"""
NEXUS Local Recommender
───────────────────────
Deterministic, rule-based local attraction suggestions.
Finds places near the destination station that fit within the
dead time created by the schedule disruption.

No ML, no LLM. Pure rule-based filtering.
"""

import json
from pathlib import Path


def load_local_places(path="data/local_places.json"):
    with open(Path(__file__).parent.parent / path) as f:
        return json.load(f)


def _minutes_since_midnight(t_str):
    """Convert HH:MM to minutes since midnight."""
    h, m = t_str.split(":")
    return int(h) * 60 + int(m)


def _is_open_at(open_hours_str, check_minutes):
    """Check if a place is open at a given minute-of-day."""
    start_str, end_str = open_hours_str.split("-")
    start_min = _minutes_since_midnight(start_str)
    end_min = _minutes_since_midnight(end_str)
    if end_min < start_min:
        end_min += 1440
    if check_minutes < start_min:
        check_minutes += 1440
    return start_min <= check_minutes <= end_min


def recommend(estimated_delay_minutes, original_arrival_iso=None, local_places_data=None):
    """
    Recommend local places based on dead time (delay) at destination.
    
    Filtering:
    1. Calculate time slot that was displaced by the delay
    2. Keep only places open during that time slot
    3. Keep only places where walk_minutes + typical_duration fits in the slot
    4. Sort by walk_minutes (shortest first), max 3
    
    Args:
        estimated_delay_minutes: how many minutes late the passenger arrives
        original_arrival_iso: ISO string of original scheduled arrival at destination
        local_places_data: dict from load_local_places() (loads file if None)
    
    Returns:
        list of up to 3 suggestion dicts with place info and selection reason
    """
    if local_places_data is None:
        local_places_data = load_local_places()

    if estimated_delay_minutes <= 0:
        return []

    places = local_places_data.get("places", [])
    if not places:
        return []

    # Calculate the time slot displaced by the delay
    # Original arrival was at T, now arrives at T + delay
    # The "dead time" window is [T, T + delay] at the destination
    if original_arrival_iso:
        time_part = original_arrival_iso.split("T")[1][:5]
        slot_start = _minutes_since_midnight(time_part)
    else:
        # Fallback: assume arrival in late afternoon
        slot_start = 16 * 60  # 16:00

    slot_end = slot_start + estimated_delay_minutes
    slot_duration = slot_end - slot_start

    # Filter and score
    candidates = []
    for p in places:
        walk = p.get("walk_minutes_from_station", 0)
        duration = p.get("typical_duration_minutes", 30)
        total_needed = walk + duration

        if total_needed > slot_duration:
            continue

        # Check if place is open during the window
        open_hours = p.get("open_hours", "00:00-24:00")
        # Check midpoint of visit: slot_start + walk + duration/2
        visit_mid = slot_start + walk + duration // 2
        if visit_mid > 1440:
            visit_mid -= 1440
        if not _is_open_at(open_hours, visit_mid):
            continue

        time_available = slot_duration - total_needed
        reason = (
            f"부산 도착 지연({estimated_delay_minutes}분)으로 생긴 시간 — "
            f"{p['name']}(도보 {walk}분 + 체류 {duration}분) 방문 가능"
        )
        candidates.append({
            "name": p["name"],
            "category": p.get("category", ""),
            "walk_minutes_from_station": walk,
            "typical_duration_minutes": duration,
            "description": p.get("description", ""),
            "time_available_minutes": time_available,
            "reason": reason
        })

    # Sort by walk distance (shortest first), take top 3
    candidates.sort(key=lambda c: c["walk_minutes_from_station"])
    return candidates[:3]
