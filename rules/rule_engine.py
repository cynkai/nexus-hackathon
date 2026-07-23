"""
NEXUS Rule Engine
────────────────
Reads Scenario.json and produces explainable transfer recommendations.
Rule-based only. No ML, no LLM, no optimization.
"""

import json
from pathlib import Path


def load_scenario(path="data/Scenario.json"):
    with open(Path(__file__).parent.parent / path) as f:
        return json.load(f)


def calculate_transfer_possible(available_minutes, required_minutes):
    """Transfer is possible only if available time meets or exceeds required time."""
    return available_minutes >= required_minutes


def calculate_risk_score(transfer_possible, available_minutes, required_minutes):
    """
    Risk score ranging 0.0 (safe) to 1.0 (critical).
    
    Rule:
    - If transfer is possible → risk = 0.0
    - If transfer fails → risk = shortfall ratio, capped at 1.0
    """
    if transfer_possible:
        return 0.0
    shortfall = required_minutes - available_minutes
    return round(min(1.0, shortfall / required_minutes), 2)


def calculate_estimated_delay(delay_minutes, transfer_possible, available_minutes, required_minutes):
    """
    Estimated total delay to final destination (minutes).
    
    Assumption:
    If the scheduled transfer fails, the next available rail service
    is assumed to depart within 30 minutes of the missed departure.
    This is a reasonable heuristic for high-frequency KTX lines
    (Seoul–Busan headway is typically 30–60 minutes).
    
    Rule:
    - If transfer is possible → no additional delay
    - If transfer fails → flight delay + wait for next available service
      (next service wait estimated from required transfer interval)
    """
    if transfer_possible:
        return 0
    shortfall = required_minutes - available_minutes
    next_service_wait = min(shortfall, 30)
    return delay_minutes + next_service_wait


def calculate_risk_level(risk_score):
    """
    Map numeric risk_score to a human-readable level.
    
    0.0       → LOW
    0.01–0.50 → MEDIUM
    0.51–1.0  → HIGH
    """
    if risk_score == 0.0:
        return "LOW"
    if risk_score <= 0.50:
        return "MEDIUM"
    return "HIGH"


def generate_recommendation(transfer_possible, delay_minutes, available_minutes, required_minutes):
    """
    Generate one explainable recommendation.
    
    Rule:
    - If transfer is possible → continue as planned
    - If transfer fails → reschedule with explicit acknowledgment that
      next-train schedule data is unavailable in the current mock.
    """
    if transfer_possible:
        return {
            "recommendation": {
                "action": "CONTINUE",
                "target": "CURRENT_PLAN",
                "display": "Continue as planned",
                "service_id": None,
                "departure": None
            },
            "reason": (
                f"Transfer is feasible. "
                f"Available transfer time ({available_minutes} min) meets "
                f"required transfer time ({required_minutes} min)."
            ),
            "reason_code": "TRANSFER_FEASIBLE"
        }
    return {
        "recommendation": {
            "action": "RESCHEDULE",
            "target": "NEXT_AVAILABLE_RAIL",
            "display": "Take the next available KTX",
            "service_id": None,
            "departure": None
        },
        "reason": (
            f"Flight delay of {delay_minutes} min makes the scheduled connection impossible. "
            f"Available transfer time ({available_minutes} min) is "
            f"{required_minutes - available_minutes} min short of the required {required_minutes} min."
        ),
        "reason_code": "TRANSFER_TIME_INSUFFICIENT"
    }


def generate_passenger_message(delay_minutes, estimated_delay_minutes, risk_level):
    """
    Build a deterministic passenger-facing message from facts only.
    No invented data. No LLM. Template-based only.
    """
    if risk_level == "LOW":
        return (
            f"Your flight has been delayed by {delay_minutes} minutes. "
            f"Your scheduled rail transfer is still possible. "
            f"Estimated arrival delay: {estimated_delay_minutes} minutes."
        )
    return (
        f"Your flight has been delayed by {delay_minutes} minutes. "
        f"The scheduled rail transfer is no longer possible. "
        f"We recommend taking the next available KTX. "
        f"Estimated arrival delay: {estimated_delay_minutes} minutes."
    )


def run(scenario_path="data/Scenario.json", scenario_data=None):
    if scenario_data is not None:
        data = scenario_data
    else:
        data = load_scenario(scenario_path)

    # ── Extract facts ──────────────────────────────────────────────
    delay = data["delay_events"][0]["delay_minutes"]
    t = data["transfers"][0]
    available = t["available_minutes"]
    required = t["required_minutes"]

    # ── Rule chain ─────────────────────────────────────────────────
    transfer_possible = calculate_transfer_possible(available, required)
    risk_score = calculate_risk_score(transfer_possible, available, required)
    risk_level = calculate_risk_level(risk_score)
    estimated_delay_minutes = calculate_estimated_delay(
        delay, transfer_possible, available, required
    )
    rec = generate_recommendation(
        transfer_possible, delay, available, required
    )
    passenger_message = generate_passenger_message(
        delay, estimated_delay_minutes, risk_level
    )

    return {
        "scenario_id": data["scenario_id"],
        "transfer_possible": transfer_possible,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason_code": rec["reason_code"],
        "reason": rec["reason"],
        "estimated_delay_minutes": estimated_delay_minutes,
        "recommendation": rec["recommendation"],
        "passenger_message": passenger_message,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
