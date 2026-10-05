"""
NEXUS Explainer
───────────────
Generates passenger-facing explanation text.
Uses LLM when available (and configured), otherwise falls back to templates.

CRITICAL RULE:
  - Only passenger_message may differ between LLM and template paths.
  - All decision fields (risk_score, risk_level, reason_code,
    estimated_delay_minutes, recommendation, local_suggestions)
    are read-only. The explainer NEVER modifies them.
  - If LLM fails for any reason, silently fall back to template.
  - The LLM only rephrases the template message. If its text drops or
    contradicts a fact the template states (see check_message), the
    template is used instead.
"""

import os
import json
import re

# LLM configuration
LLM_API_KEY_ENV = "NEXUS_LLM_API_KEY"
LLM_MODEL_ENV = "NEXUS_LLM_MODEL"
DEFAULT_LLM_MODEL = "gpt-5.4-mini"
CUSTOMER_SERVICE = "1544-7788"

DEFAULT_LANGUAGE = "ko"


# 숫자를 한국어로 읽었을 때 받침이 있는가 (0 영, 1 일, 3 삼, 6 육, 7 칠, 8 팔, 10 십…)
_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False,
                  "5": False, "6": True, "7": True, "8": True, "9": False}


def _object_particle(word):
    """'KTX-110' → '을', '14:00 출발 KTX-112' → '를' (받침에 맞는 목적격 조사)."""
    if not word:
        return "를"
    last = word[-1]
    if last.isdigit():
        # 0으로 끝나면 십·백·천·만으로 읽힌다 — 모두 받침이 있다
        stripped = word.rstrip("0")
        zeros = len(word) - len(stripped)
        if zeros and stripped and stripped[-1].isdigit():
            return "을"
        return "을" if _DIGIT_BATCHIM[last] else "를"
    if "가" <= last <= "힣":
        return "을" if (ord(last) - 0xAC00) % 28 else "를"
    return "를"


def _template_message(result, lang=DEFAULT_LANGUAGE):
    """
    Build a deterministic passenger message from the result dict.
    Template-based. No LLM calls.
    Branching is based on reason_code, NOT risk_level.
    risk_level is only used for intensity within the same code path.
    """
    r = result
    reason_code = r.get("reason_code", "")
    risk_level = r.get("risk_level", "MEDIUM")
    delay = r.get("estimated_delay_minutes", 0)
    delay_str = f"{delay}분" if delay is not None else "당일 도착 불가"
    delay_en_str = f"{delay} minutes" if delay is not None else "arrival impossible today"
    # 지연 0분이면 "예상 도착 지연: 약 0분" 대신 예정대로 도착한다고 말한다
    arrival_ko = "목적지에는 예정대로 도착합니다." if delay == 0 else f"예상 도착 지연: 약 {delay_str}."
    arrival_en = "You will arrive on schedule." if delay == 0 else f"Estimated arrival delay: {delay_en_str}."
    rec = r.get("recommendation", {})
    suggestions = r.get("local_suggestions", [])
    flight_delay = r.get("flight_delay_minutes", None)
    if flight_delay is None:
        flight_delay = str(delay) if delay is not None else "?"

    if lang == "ko":
        if reason_code == "TRANSFER_FEASIBLE":
            if risk_level == "LOW":
                msg = (
                    f"항공편이 지연되었으나 예정된 KTX 환승이 가능합니다. "
                    + arrival_ko
                )
            else:
                # MEDIUM — transfer possible but buffer < 30 min
                msg = (
                    f"항공편이 지연되었으나 예정된 KTX 환승이 가능합니다. "
                    f"환승 여유 시간이 촉박하니 도착 후 바로 이동해 주세요. "
                    + arrival_ko
                )
        elif reason_code == "TRANSFER_TIME_INSUFFICIENT":
            display_ko = rec.get("display_ko", "")
            if display_ko:
                msg = (
                    f"항공편이 {flight_delay}분 지연되었습니다. "
                    f"예정된 KTX 환승이 불가능하여 {display_ko}{_object_particle(display_ko)} 추천합니다. "
                    + arrival_ko
                )
            else:
                msg = (
                    f"항공편 지연으로 예정된 KTX 환승이 불가능합니다. "
                    f"대체 열차를 찾을 수 없어 고객센터(1544-7788) 문의가 필요합니다. "
                    + arrival_ko
                )
        else:  # LAST_TRAIN_MISSED
            msg = (
                f"항공편 지연으로 인해 KTX 환승이 불가능하며, "
                f"오늘 운행하는 대체 열차가 없습니다. "
                f"고객센터(1544-7788)를 통해 대체 교통편을 문의해 주세요."
            )
        if suggestions and reason_code != "LAST_TRAIN_MISSED":
            names = [s["name"] for s in suggestions[:2]]
            msg += f" 대기 시간을 활용해 주변 장소를 방문해 보세요: {', '.join(names)}."
        return msg

    # ── English path ────────────────────────────────────────────
    if reason_code == "TRANSFER_FEASIBLE":
        if risk_level == "LOW":
            return (
                f"Your flight has been delayed, but the scheduled KTX transfer "
                f"is still possible. " + arrival_en
            )
        return (
            f"Your flight has been delayed, but the scheduled KTX transfer "
            f"is still possible. The transfer window is tight — please proceed "
            f"to the platform immediately upon arrival. "
            + arrival_en
        )

    if reason_code == "TRANSFER_TIME_INSUFFICIENT":
        en_display = rec.get("display", "")
        if rec.get("service_id") and en_display:
            return (
                f"Your flight has been delayed. The scheduled KTX transfer is "
                f"no longer possible. Please {en_display[:1].lower() + en_display[1:]}. "
                + arrival_en
            )
        return (
            f"Your flight has been delayed. The scheduled KTX transfer is "
            f"no longer possible. No alternative trains available. "
            f"Please contact customer service (1544-7788). "
            + arrival_en
        )

    # LAST_TRAIN_MISSED
    return (
        f"Due to the flight delay, the KTX transfer is no longer possible "
        f"and no alternative trains are available today. "
        f"Please contact customer service (1544-7788) for alternative transport."
    )


def _llm_generate(base_message, lang=DEFAULT_LANGUAGE, api_key=None, model=None):
    """
    Ask the LLM to rephrase the template message for the passenger.
    The template is the only source of facts. Returns None on any error.
    """
    try:
        import urllib.request

        language = "Korean" if lang == "ko" else "English"
        prompt = (
            "You are a railway customer service agent. Rewrite the message below "
            f"for the passenger in calm, empathetic {language}, in 2-3 sentences.\n"
            "Rules:\n"
            "- Keep every fact: whether the transfer is possible or not, every time, "
            "train number, number of minutes, phone number and place name.\n"
            "- If the message says to move right away, keep that.\n"
            "- Do not add any fact, number or advice that is not in the message.\n"
            "- Output only the rewritten message.\n\n"
            f"Message:\n{base_message}"
        )

        body = json.dumps({
            "model": model or os.environ.get(LLM_MODEL_ENV) or DEFAULT_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 400
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
        return raw["choices"][0]["message"]["content"].strip() or None
    except Exception:
        return None


_NUMBER = re.compile(r"\d+(?:[:\-]\d+)*")


def check_message(message, result, base_message, lang=DEFAULT_LANGUAGE):
    """
    Return a list of problems with an LLM message (empty = OK).
    The template message (base_message) is the reference: the LLM may
    reword it but must keep its conclusion and must not invent numbers.
    """
    problems = []
    if not message:
        return ["empty"]
    reason_code = result.get("reason_code", "")
    possible = bool(result.get("transfer_possible"))
    rec = result.get("recommendation", {}) or {}

    # Every number (times, minutes, train ids, phone) must come from the template.
    base_numbers = set(_NUMBER.findall(base_message))
    invented = [n for n in _NUMBER.findall(message) if n not in base_numbers]
    if invented:
        problems.append(f"numbers not in template: {invented}")

    if lang == "ko":
        impossible_words = ("불가능", "어렵", "못 타", "탈 수 없")
        says_impossible = any(w in message for w in impossible_words)
        if possible and says_impossible:
            problems.append("says the transfer is impossible")
        if possible and "가능" not in message.replace("불가능", ""):
            problems.append("does not say the transfer is possible")
        if not possible and not says_impossible:
            problems.append("does not say the transfer is impossible")
        if reason_code == "TRANSFER_FEASIBLE" and "바로" in base_message \
                and not any(w in message for w in ("바로", "즉시", "서둘", "곧장")):
            problems.append("drops the urgency")
        if reason_code == "LAST_TRAIN_MISSED" and "대체 열차" not in message:
            problems.append("does not say there is no alternative train")
    else:
        lower = message.lower()
        if possible and ("no longer possible" in lower or "not possible" in lower):
            problems.append("says the transfer is impossible")
        if not possible and not any(w in lower for w in ("no longer possible", "not possible", "cannot", "can't", "unable")):
            problems.append("does not say the transfer is impossible")
        if reason_code == "TRANSFER_FEASIBLE" and "immediately" in base_message \
                and not any(w in lower for w in ("immediately", "right away", "promptly", "hurry")):
            problems.append("drops the urgency")

    if CUSTOMER_SERVICE in base_message and CUSTOMER_SERVICE not in message:
        problems.append("drops the customer service number")
    if possible and CUSTOMER_SERVICE in message:
        problems.append("sends a passenger with a feasible transfer to customer service")
    service_id = rec.get("service_id")
    if service_id and service_id in base_message and service_id not in message:
        problems.append(f"drops the recommended train {service_id}")
    return problems


def explain(result, override_language=None):
    """
    Enhance result dict with LLM-generated passenger message if possible.
    
    Args:
        result: dict from rule_engine.run()
        override_language: "ko" or "en" (None = auto from passenger data)
    
    Returns:
        dict with same decision fields + possibly improved passenger_message
    
    CRITICAL: Only passenger_message may differ from input.
    All other fields are byte-identical.
    """
    # Determine language
    if override_language:
        lang = override_language
    else:
        passenger = result.get("_passenger", {})
        lang = passenger.get("language", DEFAULT_LANGUAGE)

    base_message = _template_message(result, lang)
    result = dict(result)

    # Try LLM path — kept only if it says the same thing as the template
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if api_key:
        llm_msg = _llm_generate(base_message, lang, api_key=api_key)
        if llm_msg and not check_message(llm_msg, result, base_message, lang):
            result["passenger_message"] = llm_msg
            return result

    # Template fallback
    result["passenger_message"] = base_message
    return result
