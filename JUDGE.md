# NEXUS — Judging One-Pager

> Read time: under 2 minutes

## What problem is solved?

A passenger flies from **Jeju to Gimpo**, then plans to take **KTX from Seoul to Busan**. Their flight is delayed by 45 minutes. Can they still catch the train? If not, what should they do?

**Railway and aviation systems are disconnected today.** No single system answers this question. NEXUS proves that integrating both data sources enables better transfer decisions.

## What the demo shows

| Step | What happens |
|------|-------------|
| 1 | A flight delay event is received (KE-A, +45 min) |
| 2 | NEXUS calculates: available transfer time (5 min) < required transfer time (30 min) → **transfer impossible** |
| 3 | Risk score: **0.83 (HIGH)** |
| 4 | Recommendation: **"Take the next available KTX"** |
| 5 | Operator Dashboard displays all data |
| 6 | Passenger View shows the message in plain language |

## Demo steps (60 seconds)

1. **Start:** `python3 frontend/server.py`
2. **Open:** `http://localhost:8080`
3. **Dashboard loads** — Operator sees: SC001, ❌ Failed, HIGH, 0.83, 70 min delay
4. **Passenger sees:** *"Your flight has been delayed by 45 minutes... We recommend taking the next available KTX. Estimated arrival delay: 70 minutes."*
5. **Kill the server → reload** — cached fallback works (internet failure demo)

## Why this matters

- **Integrated data** — Combining rail + aviation produces insights neither system can generate alone
- **Explainable** — Every recommendation includes a reason, risk score, and estimated delay (no black box)
- **Deterministic** — Rule-based, no ML/LLM, fully auditable
- **Resilient** — Graceful fallback if data sources are unavailable
- **Extensible** — Public API integration ready; activate with an API key

## Architecture highlights

```
Scenario.json (facts) → Rule Engine (judgment) → Dashboard (presentation)
```

- **Facts and judgment are separated** — clean pipeline, each stage has one responsibility
- **Rule Engine is frozen** — Dashboard never needs changes when data sources change
- **Zero external dependencies** — Python standard library only

## Known limitations

- **Mock data** — single scenario, not live API data (API integration ready but requires a key)
- **Not production software** — accuracy is secondary to demonstrating the concept
- **Feature-freeze** — no reservation, ticketing, payment, or multi-agent (by design)

## Key takeaway

> NEXUS proves that combining railway and aviation data enables better transfer decisions than treating each system independently — with explainable, deterministic rules and a resilient demo that works even offline.
