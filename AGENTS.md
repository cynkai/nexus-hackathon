# AGENTS.md
## Mission
Deliver the smallest convincing MVP.
Our objective is a stable demo,
not perfect architecture.
---
## Workflow
Complete ONE task.
STOP.
Wait for user confirmation.
Never continue automatically.
---
## Scope
Never add features unless explicitly requested.
Forbidden
- Reservation
- Payment
- Multi-Agent
- Digital Twin
- Physics Engine
- National Optimization
---
## Engineering
Prefer
- direct implementation
- simple functions
- small files
- explicit logic
Avoid
- Clean Architecture
- DDD
- CQRS
- Event Bus
- Repository Pattern
- Generic abstractions
---
## Dependencies
Prefer standard libraries.
Ask before adding dependencies.
---
## Safety
Ask before
- changing architecture
- renaming files
- changing directory layout
- introducing frameworks
Never refactor working code unless it blocks progress.
---
## Validation
A task is complete only if
✓ Code builds
✓ Existing behavior still works
✓ Recommendation is generated
✓ Dashboard updates
✓ No regression introduced
---
## Output Format
Always return
1. Summary
2. Files changed
3. How to run
4. How to verify
Then STOP.
---
## Human Override
The repository is the source of truth.
Reality beats documentation.
