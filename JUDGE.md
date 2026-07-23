# NEXUS — Judging One-Pager

> Read time: under 2 minutes

## What problem is solved?

A passenger arrives at **Incheon International Airport** from abroad, then plans to take **AREX → KTX to Busan**. Their flight is delayed by 45 minutes. Can they still catch the train? If not, what should they do?

**Railway and aviation systems are disconnected today.** No single system answers this question. NEXUS proves that integrating both data sources enables better transfer decisions.

## What the demo shows

| Step | What happens |
|------|-------------|
| 1 | A flight delay event is received (KE-123, +45 min) |
| 2 | NEXUS calculates: available transfer time (95 min) < required transfer time (118 min) → **transfer impossible** |
| 3 | Risk score: **0.17 (MEDIUM)**, ETA: **30 min** |
| 4 | Recommendation: **"Take KTX-110 at 14:00"** |
| 5 | Operator Dashboard displays all data (Korean labels) |
| 6 | Passenger View shows Korean message with local suggestions |

## Demo steps (60 seconds)

1. **Start:** `python3 frontend/server.py`
2. **Open:** `http://localhost:8080`
3. **Dashboard loads** — Operator sees: SC001, ❌ 불가능, MEDIUM, 0.17, 30분 delay, Korean passenger message
4. **Passenger sees:** *"항공편이 45분 지연되었습니다. 예정된 KTX 환승이 불가능하여 14:00 출발 KTX-110를 추천합니다..."*
5. **Fault injection:** Visit `/api/result?fault=1` then reload — cached fallback works (server failure demo)

## Why this matters

- **Integrated data** — Combining rail + aviation produces insights neither system can generate alone
- **Explainable** — Every recommendation includes a reason, risk score, and estimated delay (no black box)
- **Deterministic** — All scores, risk levels, and recommendations are rule-based. Passenger-facing text uses LLM when available (template fallback otherwise). Smoke test proves decision fields are byte-identical between LLM and template paths. Fully auditable.
- **Resilient** — Graceful fallback if data sources are unavailable
- **Extensible** — Normalization layer for public API data is implemented; API endpoint is ready to connect

## Architecture highlights

```
Scenario.json (facts) → Rule Engine (judgment) → Dashboard (presentation)
```

- **Facts and judgment are separated** — clean pipeline, each stage has one responsibility
- **Rule Engine is frozen** — Dashboard never needs changes when data sources change
- **Zero external dependencies** — Python standard library only

## Known limitations

- **Mock data** — three pre-defined scenarios (flight normalization layer implemented; rail timetable integration **not yet implemented** — live API connection would produce empty timetable → fallback behavior)
- **Not production software** — accuracy is secondary to demonstrating the concept
- **Feature-freeze** — no reservation, ticketing, payment, or multi-agent (by design)

## Key takeaway

> NEXUS proves that combining railway and aviation data enables better transfer decisions than treating each system independently — with explainable, deterministic rules and a resilient demo that works even offline.
