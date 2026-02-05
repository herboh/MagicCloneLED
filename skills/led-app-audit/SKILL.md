---
name: led-app-audit
description: Audit this LED controller app for reliability, API correctness, and low-complexity maintainability improvements; produce ranked findings, markdown artifacts, and an implementation plan.
---

# LED App Audit Skill

Use this skill when asked to review this repository or similar LED-controller apps.

## Workflow
1. Read goals and architecture from `README.md` and key runtime files.
2. Review backend correctness first (`backend/main.py`, manager/controller modules).
3. Review frontend state/event lifecycles (`src/components/**`).
4. Produce `docs/audit/<date>-review.md` with:
- Scope
- Verification notes
- Findings ordered by severity with file:line
- Ranked change list
5. Produce `docs/audit/<date>-implementation-plan.md` with minimal-change rollout.
6. Commit docs only on the audit branch unless implementation is explicitly requested.

## Guardrails
- Prioritize behavioral correctness over style.
- Favor fewer abstractions and lower LOC.
- Do not rewrite architecture unless a defect requires it.
- If tests/tooling cannot run, record exactly what failed and why.

## Severity Guide
- `P0`: data loss, wrong API contract, security/safety critical behavior.
- `P1`: user-visible functional defects or high-risk fragility.
- `P2`: maintainability/performance risks with lower immediate impact.

