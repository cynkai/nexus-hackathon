"""
NEXUS Public API Integration
────────────────────────────
Optional public data source with automatic fallback to Scenario.json.

Architecture:

    Public API (optional)
    ↓
    normalizer
    ↓
    Scenario-compatible JSON
    ↓
    Rule Engine (unchanged)
    ↓
    Dashboard (unchanged)

If Public API is unavailable → silent fallback to data/Scenario.json.
No Rule Engine or Dashboard changes needed.
"""

import json
import os
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────
# Set to True to attempt public API data on every request.
# When False, always uses data/Scenario.json (default demo mode).
USE_PUBLIC_API = False

# ── Data source identifiers (for logging / API selection) ─────────-
DATA_SOURCE_FILE = "Scenario.json"
DATA_SOURCE_API = "data.go.kr"

# ── Internal helpers ───────────────────────────────────────────────


def _load_scenario_json(path=None):
    """Load the local Scenario.json as fallback."""
    if path is None:
        path = Path(__file__).parent.parent / "data" / "Scenario.json"
    else:
        path = Path(path)
    print(f"[INFO] Using {DATA_SOURCE_FILE}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_iso_minutes(iso_str):
    """Extract total minutes since midnight from ISO8601 time string."""
    # input: "2026-07-23T11:10:00"
    # output: 11*60 + 10 = 670
    time_part = iso_str.split("T")[1]  # "11:10:00"
    h, m, _ = time_part.split(":")
    return int(h) * 60 + int(m)


def _iso_to_time_str(iso_str):
    """Extract HH:MM from ISO8601."""
    return iso_str.split("T")[1][:5]


# ── Public API fetch ───────────────────────────────────────────────


def fetch_public_data():
    """
    Attempt to fetch schedule data from a public API.
    
    Target: 공공데이터포털 (data.go.kr) 항공/철도 정보 API.
    
    In production, replace the mock implementation with:
    
        import urllib.request
        url = (
            "https://apis.data.go.kr/B551177/..."
            "?serviceKey=YOUR_KEY"
            "&pageNo=1"
            "&numOfRows=10"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    
    Returns:
        dict with 'flights' and 'rail' keys, or None on failure.
    """
    # ── Attempt real HTTP request ──────────────────────────────────
    api_key = os.environ.get("NEXUS_API_KEY") or os.environ.get(
        "DATA_GO_KR_API_KEY"
    )

    if not api_key:
        print("[DEBUG] No NEXUS_API_KEY or DATA_GO_KR_API_KEY set.")
        return None

    # The following is a TEMPLATE for production use.
    # Uncomment and configure when a valid API key is available.
    #
    # import urllib.request
    # try:
    #     # Example: airport operation info (공항운항정보)
    #     url = (
    #         "https://apis.data.go.kr/B551177/StatusOfPassengerFlights"
    #         "/getPassengerFlightsStatus"
    #         f"?serviceKey={api_key}"
    #         "&pageNo=1"
    #         "&numOfRows=10"
    #         "&itinerary=GMP"
    #     )
    #     with urllib.request.urlopen(url, timeout=5) as resp:
    #         raw = json.loads(resp.read())
    #     return raw
    # except Exception as e:
    #     print(f"[WARN] Public API request failed: {e}")
    #     return None

    print("[DEBUG] Public API not yet connected (no endpoint configured).")
    return None


# ── Normalizer ─────────────────────────────────────────────────────


def normalize_to_scenario(raw_data):
    """
    Convert a public API response into Scenario.json format.
    
    This function is the ONLY place that knows about external API schemas.
    Rule Engine and Dashboard remain completely isolated from API changes.
    
    Args:
        raw_data: dict from fetch_public_data()
    
    Returns:
        dict in Scenario.json format
    
    Raises:
        ValueError if required fields are missing
    """
    # ── Extract flight info ────────────────────────────────────────
    flights = raw_data.get("flights", [])
    if not flights:
        raise ValueError("No flight data in API response")

    flight = flights[0]
    service_id = flight.get("airline") or flight.get("flightId", "UNKNOWN")
    
    scheduled_arrival_iso = flight.get("scheduledArrival", "")
    actual_arrival_iso = flight.get("actualArrival", "")
    scheduled_departure_iso = flight.get("scheduledDeparture", "")

    delay_min = 0
    if scheduled_arrival_iso and actual_arrival_iso:
        sched_min = _parse_iso_minutes(scheduled_arrival_iso)
        actual_min = _parse_iso_minutes(actual_arrival_iso)
        delay_min = max(0, actual_min - sched_min)

    # ── Extract rail info ──────────────────────────────────────────
    rail_list = raw_data.get("rail", [])
    if not rail_list:
        raise ValueError("No rail data in API response")

    rail = rail_list[0]
    rail_id = rail.get("trainId", "RAIL-UNKNOWN")
    rail_departure_iso = rail.get("scheduledDeparture", "")
    rail_arrival_iso = rail.get("scheduledArrival", "")

    # ── Build transfer info ────────────────────────────────────────
    airport_code = flight.get("destination", "ICN")
    station_name = rail.get("origin", "Seoul Station")

    # ── Assemble Scenario-compatible document ──────────────────────
    scenario = {
        "scenario_id": "API-" + service_id,
        "title": f"{flight.get('origin', '?')} → {rail.get('destination', '?')}",
        "passenger": {
            "id": "P-API",
            "name": "API Passenger",
            "nationality": "KR",
            "language": "ko"
        },
        "route": {
            "origin": flight.get("origin", "?"),
            "waypoints": [airport_code, station_name],
            "destination": rail.get("destination", "?")
        },
        "itinerary": [
            {
                "leg": 1,
                "mode": "flight",
                "service_id": service_id,
                "origin": flight.get("origin", "?"),
                "destination": flight.get("destination", "?"),
                "scheduled_departure": scheduled_departure_iso,
                "scheduled_arrival": scheduled_arrival_iso,
                "actual_arrival": actual_arrival_iso,
                "delay_minutes": delay_min
            },
            {
                "leg": 2,
                "mode": "transit",
                "service_id": None,
                "service_name": "Transit",
                "origin": airport_code,
                "destination": station_name,
                "scheduled_departure": scheduled_arrival_iso or "",
                "scheduled_arrival": rail_departure_iso or ""
            },
            {
                "leg": 3,
                "mode": "rail",
                "service_id": rail_id,
                "origin": rail.get("origin", "?"),
                "destination": rail.get("destination", "?"),
                "scheduled_departure": rail_departure_iso,
                "scheduled_arrival": rail_arrival_iso
            }
        ],
        "delay_events": [
            {
                "subject_service_id": service_id,
                "subject_leg": 1,
                "type": "delay",
                "delay_minutes": delay_min,
                "scheduled_arrival": scheduled_arrival_iso,
                "actual_arrival": actual_arrival_iso
            }
        ],
        "transfers": [
            {
                "from_leg": 1,
                "to_leg": 3,
                "via_legs": [2],
                "from_location": airport_code,
                "to_location": station_name,
                "from_arrival": actual_arrival_iso,
                "to_departure": rail_departure_iso
            }
        ]
    }

    return scenario


# ── Main entry point ───────────────────────────────────────────────


def get_scenario_data():
    """
    Return Scenario-compatible data.
    
    If USE_PUBLIC_API is True:
        Try public API → normalize → return
        On any failure: log warning → fall back to data/Scenario.json
    Else:
        Return data/Scenario.json immediately.
    
    Returns:
        dict in Scenario.json format (always)
    """
    if not USE_PUBLIC_API:
        return _load_scenario_json()

    print(f"[INFO] Using {DATA_SOURCE_API}")
    raw = fetch_public_data()

    if raw is None:
        print(f"[WARN] {DATA_SOURCE_API} unavailable. Falling back to {DATA_SOURCE_FILE}.")
        return _load_scenario_json()

    try:
        scenario = normalize_to_scenario(raw)
        print(f"[INFO] Normalized API data → scenario_id={scenario.get('scenario_id')}")
        return scenario
    except (ValueError, KeyError, TypeError) as e:
        print(
            f"[WARN] {DATA_SOURCE_API} data invalid ({e}). "
            f"Falling back to {DATA_SOURCE_FILE}."
        )
        return _load_scenario_json()


# ── CLI test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with default config (USE_PUBLIC_API = False)
    data = get_scenario_data()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:200] + "\n...")

    # Test with API mode (will fall back gracefully without a key)
    USE_PUBLIC_API = True  # noqa -- local override for CLI test
    print("\n--- Testing API mode (expect fallback) ---")
    data = get_scenario_data()
    print(f"Result scenario_id: {data.get('scenario_id')}")
