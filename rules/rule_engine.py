"""
NEXUS Rule Engine
────────────────
Reads Scenario.json + transfer_profile.json, calculates transfer feasibility
from timestamps and component times. Rule-based only. No ML, no LLM.
"""

import json
import os
import sys
from pathlib import Path

# Ensure project root is in path for sibling imports
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from rules.local_recommender import recommend as recommend_local


def load_scenario(path="data/Scenario.json"):
    with open(Path(__file__).parent.parent / path) as f:
        return json.load(f)


def load_transfer_profile(path="data/transfer_profile.json"):
    with open(Path(__file__).parent.parent / path) as f:
        return json.load(f)


def _iso_to_minutes(iso_str):
    """Convert ISO8601 time to minutes since midnight."""
    time_part = iso_str.split("T")[1]
    h, m, _ = time_part.split(":")
    return int(h) * 60 + int(m)


def calculate_available_minutes(scenario_data):
    """
    available = KTX departure - flight actual arrival (in minutes).
    Reads from the transfer's from_arrival and to_departure.
    """
    t = scenario_data["transfers"][0]
    arr_min = _iso_to_minutes(t["from_arrival"])
    dep_min = _iso_to_minutes(t["to_departure"])
    return max(0, dep_min - arr_min)


def calculate_required_minutes(profile_data):
    """
    Sum all component times from the transfer profile.
    Excludes _source (comment field).
    """
    profile = profile_data["icn_t1_to_seoul_station"]
    return sum(v for k, v in profile.items() if k != "_source" and isinstance(v, int))


def calculate_transfer_possible(available_minutes, required_minutes):
    return available_minutes >= required_minutes


def calculate_risk_score(transfer_possible, available_minutes, required_minutes, estimated_delay_minutes, last_train_missed=False, seat_contention=False):
    """
    Multi-factor risk score 0.0–0.99 (or 1.0 for last_train_missed).
    
    | Condition | Risk | Level |
    |---|---|---|
    | Transfer feasible, buffer ≥ 30 min | 0.0 | LOW |
    | Transfer feasible, buffer < 15 min | 0.3 | MEDIUM |
    | Transfer failed, alternative train exists | delay/180min | MEDIUM/HIGH |
    | Seat contention (skipped no-seat train) | +0.2 weight | HIGH |
    | Last train missed | 1.0 | CRITICAL |
    """
    NORMALIZE_THRESHOLD = 180  # minutes
    
    if transfer_possible:
        buffer_min = available_minutes - required_minutes
        if buffer_min >= 30:
            return 0.0
        else:
            return 0.3  # tight buffer (< 15 min or < 30 min)
    
    if last_train_missed:
        return 1.0
    
    # Alternative exists — cap at HIGH range (0.99 max)
    base = min(0.99, estimated_delay_minutes / NORMALIZE_THRESHOLD)
    if seat_contention:
        base = min(0.99, base + 0.2)
    return round(base, 2)


def _time_str_to_minutes(t_str):
    """Convert HH:MM time string to minutes since midnight."""
    h, m = t_str.split(":")
    return int(h) * 60 + int(m)


def calculate_estimated_delay(transfer_possible, next_train, original_arrival_iso):
    """
    Estimated total delay to final destination (minutes).
    = selected train arrival - originally scheduled arrival.
    Returns None if no train is available today (arrival impossible).
    """
    if transfer_possible:
        return 0
    if not next_train:
        return None  # arrival impossible today
    _, _, next_arrival = next_train["train"]
    orig_arr_min = _time_str_to_minutes(original_arrival_iso.split("T")[1][:5])
    next_arr_min = _time_str_to_minutes(next_arrival)
    return next_arr_min - orig_arr_min


def select_next_train(ready_minutes_from_midnight, rail_timetable):
    """
    Find the first train departing after ready_time with available seats.
    Returns dict with 'train' tuple and 'seat_contention' bool,
    or None if no train found.
    """
    best = None
    seat_contention = False
    for entry in sorted(rail_timetable, key=lambda e: _time_str_to_minutes(e["departure"])):
        dep_min = _time_str_to_minutes(entry["departure"])
        if dep_min < ready_minutes_from_midnight:
            continue
        if not entry["seats_available"]:
            seat_contention = True
            continue
        if best is None:
            best = (entry["service_id"], entry["departure"], entry["arrival"])
            break
    if best is None:
        return None
    return {"train": best, "seat_contention": seat_contention}


def calculate_risk_level(risk_score, last_train_missed=False):
    """Map numeric risk_score to a human-readable level.
    Only last_train_missed=True can produce CRITICAL."""
    if last_train_missed:
        return "CRITICAL"
    if risk_score == 0.0:
        return "LOW"
    if risk_score < 0.50:
        return "MEDIUM"
    return "HIGH"


def generate_recommendation(transfer_possible, delay_minutes, available_minutes, required_minutes, profile_data, next_train=None):
    """
    Generate one explainable recommendation with component breakdown.
    If transfer fails and next_train is available, fills service_id and departure.
    """
    if transfer_possible:
        return {
            "recommendation": {
                "action": "CONTINUE",
                "target": "CURRENT_PLAN",
                "display": "Continue as planned",
            "display_ko": "예정대로 진행",
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

    profile = profile_data["icn_t1_to_seoul_station"]
    components = [
        ("immigration", profile["immigration_minutes"]),
        ("baggage claim", profile["baggage_claim_minutes"]),
        ("airport to AREX platform", profile["airport_to_arex_platform_minutes"]),
        ("AREX express", profile["arex_express_minutes"]),
        ("Seoul Station to KTX platform", profile["seoul_station_to_ktx_platform_minutes"]),
    ]
    breakdown = " + ".join(f"{v}" for _, v in components)
    shortfall = required_minutes - available_minutes

    if next_train:
        sid, dep, arr = next_train["train"]
        display = f"Take {sid} at {dep}"
        display_ko = f"{dep} 출발 {sid}"
        target = "NEXT_AVAILABLE_RAIL"
        reason_extra = f"Recommended: {sid} departing at {dep}, arriving {arr}."
        reason_code = "TRANSFER_TIME_INSUFFICIENT"
    else:
        sid, dep, arr = None, None, None
        display = "No alternative rail service available"
        display_ko = "대체 열차 없음"
        target = "LAST_TRAIN_MISSED"
        reason_extra = "No alternative rail service with available seats found for today."
        reason_code = "LAST_TRAIN_MISSED"

    return {
        "recommendation": {
            "action": "RESCHEDULE",
            "target": target,
        "display": display,
        "display_ko": display_ko,
        "service_id": sid,
            "departure": dep
        },
        "reason": (
            f"Flight delay of {delay_minutes} min makes the scheduled connection impossible. "
            f"Required transfer time ({required_minutes} min) = {breakdown}. "
            f"Available transfer time ({available_minutes} min) → {shortfall} min short. "
            f"{reason_extra}"
        ),
        "reason_code": reason_code
    }


def generate_passenger_message(delay_minutes, estimated_delay_minutes, risk_level):
    """Deterministic passenger-facing message. Template-based only."""
    delay_str = f"{estimated_delay_minutes}분" if estimated_delay_minutes is not None else "당일 도착 불가"
    if risk_level == "LOW":
        return (
            f"Your flight has been delayed by {delay_minutes} minutes. "
            f"Your scheduled rail transfer is still possible. "
            f"Estimated arrival delay: {estimated_delay_minutes} minutes."
        )
    if risk_level == "CRITICAL" and estimated_delay_minutes is None:
        return (
            f"Your flight has been delayed by {delay_minutes} minutes. "
            f"The scheduled rail transfer is no longer possible. "
            f"No alternative KTX service available today."
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

    profile_data = load_transfer_profile()

    # ── Calculate from timestamps (not from pre-computed fields) ──
    delay = data["delay_events"][0]["delay_minutes"]
    available = calculate_available_minutes(data)
    required = calculate_required_minutes(profile_data)

    # ── Rule chain ─────────────────────────────────────────────────
    transfer_possible = calculate_transfer_possible(available, required)

    # Find next train: passenger ready = flight actual arrival + required processing
    flight_arrival_min = _iso_to_minutes(data["transfers"][0]["from_arrival"])
    ready_min = flight_arrival_min + required
    timetable = data.get("rail_timetable", [])
    next_train = select_next_train(ready_min, timetable) if not transfer_possible else None

    original_arrival_iso = data["itinerary"][2]["scheduled_arrival"]
    estimated_delay_minutes = calculate_estimated_delay(
        transfer_possible, next_train, original_arrival_iso
    )
    last_train_missed = next_train is None and not transfer_possible
    seat_contention = next_train is not None and next_train.get("seat_contention", False)
    risk_score = calculate_risk_score(
        transfer_possible, available, required,
        estimated_delay_minutes, last_train_missed, seat_contention
    )
    risk_level = calculate_risk_level(risk_score, last_train_missed)
    rec = generate_recommendation(
        transfer_possible, delay, available, required, profile_data, next_train
    )
    passenger_message = generate_passenger_message(
        delay, estimated_delay_minutes, risk_level
    )

    arrival_possible_today = (
        transfer_possible or next_train is not None
    )

    local_suggestions = recommend_local(
        estimated_delay_minutes, original_arrival_iso,
        arrival_possible=arrival_possible_today
    )

    return {
        "scenario_id": data["scenario_id"],
        "transfer_possible": transfer_possible,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason_code": rec["reason_code"],
        "reason": rec["reason"],
        "estimated_delay_minutes": estimated_delay_minutes,
        "flight_delay_minutes": delay,
        "arrival_possible_today": arrival_possible_today,
        "recommendation": rec["recommendation"],
        "passenger_message": passenger_message,
        "local_suggestions": local_suggestions,
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
