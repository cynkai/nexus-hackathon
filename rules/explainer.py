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
"""

import os
import json

# LLM configuration
LLM_API_KEY_ENV = "NEXUS_LLM_API_KEY"
LLM_MODEL = "gpt-4o-mini"  # lightweight, cheap

DEFAULT_LANGUAGE = "ko"


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
                    f"예상 도착 지연: 약 {delay_str}."
                )
            else:
                # MEDIUM — transfer possible but buffer < 30 min
                msg = (
                    f"항공편이 지연되었으나 예정된 KTX 환승이 가능합니다. "
                    f"환승 여유 시간이 촉박하니 도착 후 바로 이동해 주세요. "
                    f"예상 도착 지연: 약 {delay_str}."
                )
        elif reason_code == "TRANSFER_TIME_INSUFFICIENT":
            display_ko = rec.get("display_ko", "")
            if display_ko:
                msg = (
                    f"항공편이 {flight_delay}분 지연되었습니다. "
                    f"예정된 KTX 환승이 불가능하여 {display_ko}를 추천합니다. "
                    f"예상 도착 지연: 약 {delay_str}."
                )
            else:
                msg = (
                    f"항공편 지연으로 예정된 KTX 환승이 불가능합니다. "
                    f"대체 열차를 찾을 수 없어 고객센터(1544-7788) 문의가 필요합니다. "
                    f"예상 도착 지연: 약 {delay_str}."
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
                f"is still possible. Estimated arrival delay: {delay_en_str}."
            )
        return (
            f"Your flight has been delayed, but the scheduled KTX transfer "
            f"is still possible. The transfer window is tight — please proceed "
            f"to the platform immediately upon arrival. "
            f"Estimated arrival delay: {delay_en_str}."
        )

    if reason_code == "TRANSFER_TIME_INSUFFICIENT":
        en_display = rec.get("display", "")
        if rec.get("service_id") and en_display:
            return (
                f"Your flight has been delayed. The scheduled KTX transfer is "
                f"no longer possible. We recommend {en_display}. "
                f"Estimated arrival delay: {delay_en_str}."
            )
        return (
            f"Your flight has been delayed. The scheduled KTX transfer is "
            f"no longer possible. No alternative trains available. "
            f"Please contact customer service (1544-7788). "
            f"Estimated arrival delay: {delay_en_str}."
        )

    # LAST_TRAIN_MISSED
    return (
        f"Due to the flight delay, the KTX transfer is no longer possible "
        f"and no alternative trains are available today. "
        f"Please contact customer service (1544-7788) for alternative transport."
    )


def _llm_generate(result, api_key, lang=DEFAULT_LANGUAGE):
    """
    Use LLM to generate a natural Korean passenger message.
    Falls back to template on any error.
    """
    try:
        import urllib.request

        prompt = (
            "You are a Korean railway customer service agent. "
            "Generate a concise, empathetic Korean passenger message (2-3 sentences) "
            "based on the following travel situation data. "
            "Be factual and calm. Do NOT add any information not present in the data.\n\n"
            f"Data: {json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
            f"Language: {lang}\n"
            "Passenger message (Korean only):"
        )

        body = json.dumps({
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 300
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read())
        return raw["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


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

    # Try LLM path
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if api_key:
        llm_msg = _llm_generate(result, api_key, lang)
        if llm_msg:
            result = dict(result)
            result["passenger_message"] = llm_msg
            return result

    # Template fallback
    result = dict(result)
    result["passenger_message"] = _template_message(result, lang)
    return result
