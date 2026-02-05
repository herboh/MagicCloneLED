# Implementation Plan - High Impact, Low Complexity

## Objective
Address correctness issues first, then simplify code paths without increasing architecture complexity.

## Phase 1 (Immediate)
1. Backend status-code preservation.
- Update `backend/main.py` handlers to:
  - `except HTTPException: raise`
  - `except Exception as e: raise HTTPException(500, ...)`
- Apply to individual bulb command, group command, and sync routes.

2. Group action validation.
- Add explicit `else` branch in `/groups/command` for unknown/invalid payload combinations.

3. Frontend state mutation fix.
- Replace in-place `.sort()` comparisons in group buttons with immutable comparison helper.

## Phase 2 (Small hardening)
1. WebSocket reconnect lifecycle cleanup.
- Track reconnect timeout id in a `useRef`.
- Clear pending timeout in cleanup.

2. Conversion utility consolidation.
- Move HSV/RGB/HEX conversion helpers into `src/lib/color.ts`.
- Replace duplicate inline converters in `BulbControls` and `ColorWheel`.

## Validation Checklist
- Manual API checks for expected `400/404/503/500` behavior.
- Frontend group-selection behavior stable across repeated toggles.
- No reconnect after component unmount.
- Build/lint pass once dependencies are available in the worktree.

## Success Criteria
- No false `500` responses for validation/user errors.
- Invalid group commands are rejected with `400`.
- Fewer moving parts in frontend color logic.
- Net reduction in LOC in control components.

