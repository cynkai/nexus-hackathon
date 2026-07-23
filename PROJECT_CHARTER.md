# NEXUS Project Charter
> We are not building the biggest system.
> We are building the most convincing 5-minute demo.
>
> When in doubt, ship.
---
## Mission
### Working Title
NEXUS (temporary)
The project name may change.
The MVP does not.
### One-line Definition
Integrate railway and aviation data to predict transfer failures,
estimate travel risk,
and provide explainable recommendations.
---
## Vision
We are NOT building a production transportation platform.
We are proving that combining railway and aviation data enables better transfer decisions than treating each system independently.
---
## Problem Freeze
Never change the core problem.
Railway and aviation systems optimize independently.
Transfer decisions across both systems remain disconnected.
Our MVP solves ONLY this problem.
---
## Feature Freeze
Do NOT build:
- Reservation
- Ticketing
- Payment
- Multi-Agent
- Digital Twin
- Physics Engine
- Chaos Engine
- National-scale optimization
- Real traffic-control integration
---
## Built (in scope for MVP)
- Local tourism suggestions (지역 관광 추천 계층) — implemented as optional add-on when transfer delay allows idle time
---
## Non-goals
This MVP is not production software.
Accuracy is secondary.
Demonstrating the value of integrated mobility data is primary.
---
## MVP Pipeline
Scenario
→ Unified Timeline
→ Prediction
→ Risk Score
→ Rule Engine
→ Recommendation
→ Local Tourism Connection (규칙 기반 추천)
→ Dashboard
→ Passenger View
Prediction
- Rule-based by default
- Optional statistical / ML enhancement if time permits
- LLM is used ONLY for explanation, never for decision making
---
## Explainability
Every recommendation MUST include
- reason
- risk score
- estimated delay
---
## Definition of Done
The MVP is complete when
✓ Delay event received
✓ Risk score calculated
✓ Recommendation generated
✓ Dashboard updated
✓ Passenger View updated
✓ Demo completes without manual intervention
---
## Success Criteria
Within five minutes, judges understand
- why rail + aviation integration matters
- what problem is solved
- how this MVP solves it
---
## Fallbacks
API unavailable
→ Mock Data
Prediction unavailable
→ Rule Engine only
Internet unavailable
→ Recorded demo
---
## North Star
If forced to choose between
- one more feature
or
- one more reliable demo
always choose the more reliable demo.
Reality beats documentation.
