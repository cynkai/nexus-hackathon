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
    """
    r = result
    risk_level = r.get("risk_level", "MEDIUM")
    delay = r.get("estimated_delay_minutes", 0)
    rec = r.get("recommendation", {})
    suggestions = r.get("local_suggestions", [])
    # Flight delay minutes from reason string or fallback
    reason_parts = r.get("reason", "").split("delay of ")
    flight_delay = reason_parts[1].split(" min")[0] if len(reason_parts) > 1 else str(delay)

    if lang == "ko":
        if risk_level == "LOW":
            msg = (
                f"항공편이 지연되었으나 예정된 KTX 환승이 가능합니다. "
                f"예상 도착 지연: 약 {delay}분."
            )
        elif risk_level == "CRITICAL":
            msg = (
                f"항공편 지연으로 인해 KTX 환승이 불가능하며, "
                f"오늘 운행하는 대체 열차가 없습니다. "
                f"고객센터(1544-7788)를 통해 대체 교통편을 문의해 주세요."
            )
        else:
            sid = rec.get("service_id")
            dep = rec.get("departure")
            display = rec.get("display", "")
            if sid and dep:
                msg = (
                    f"항공편이 {flight_delay}분 지연되었습니다. "
                    f"예정된 KTX 환승이 불가능하여 {display}을(를) 추천합니다. "
                    f"예상 도착 지연: 약 {delay}분."
                )
            else:
                msg = (
                    f"항공편 지연으로 예정된 KTX 환승이 불가능합니다. "
                    f"대체 열차를 찾을 수 없어 고객센터(1544-7788) 문의가 필요합니다. "
                    f"예상 도착 지연: 약 {delay}분."
                )
        if suggestions:
            names = [s["name"] for s in suggestions[:2]]
            msg += f" 대기 시간을 활용해 주변 장소를 방문해 보세요: {', '.join(names)}."
        return msg
    else:
        # English fallback (existing logic)
        if risk_level == "LOW":
            return (
                f"Your flight has been delayed, but the scheduled KTX transfer "
                f"is still possible. Estimated arrival delay: {delay} minutes."
            )
        if risk_level == "CRITICAL":
            return (
                f"Due to the flight delay, the KTX transfer is no longer possible "
                f"and no替代 trains are available today. "
                f"Please contact customer service (1544-7788) for alternative transport."
            )
        if rec.get("service_id"):
            return (
                f"Your flight has been delayed. The scheduled KTX transfer is no longer possible. "
                f"We recommend {display}. Estimated arrival delay: {delay} minutes."
            )
        return (
            f"Your flight has been delayed. The scheduled KTX transfer is no longer possible. "
            f"No alternative trains available. Please contact customer service (1544-7788). "
            f"Estimated arrival delay: {delay} minutes."
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
