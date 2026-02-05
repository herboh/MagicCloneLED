# Release 2: Color Sync + Command Latency Tuning (2026-02-05)

## Problem
1. UI color preview (swatch/brightness gradient) could desync during rapid color interactions.
2. Color command responsiveness could degrade under quick repeated input due to conservative throttling and queue buildup risk.

## Changes
1. Frontend color-state stability:
- Added a short local-interaction guard window (500ms) so stale websocket updates do not immediately overwrite rapid local color changes.
- Reduced redundant state churn by applying incoming websocket-derived state only when values materially differ.

2. Frontend command dispatch behavior:
- Switched debounced sender to per-endpoint coalescing with duplicate-command suppression.
- Reduced debounce from 200ms to 120ms for faster visual-to-device response while still limiting request rate.
- Fixed RGB brightness adjustment path to avoid stale hue/saturation reuse during chained updates.

3. Backend transport pacing:
- Reduced API debounce window from 200ms to 120ms.
- Added group-route per-target debounce filtering so repeated group actions do not enqueue unnecessary work for bulbs.
- Tuned bulb transport pacing constants:
  - `MIN_COMMAND_INTERVAL_SECONDS`: 0.25 -> 0.12
  - `GROUP_COMMAND_SPACING_SECONDS`: 0.05 -> 0.02

## Expected Outcome
1. Color UI should no longer get stuck on stale preview values during rapid drag/click interaction.
2. Perceived color-change latency should improve significantly while retaining safeguards against bulb overload.

## Follow-up Validation
1. Rapid drag on color wheel for 10-15 seconds with one bulb selected.
2. Rapid quick-color taps across distinct colors.
3. Group color sweep with 3-4 bulbs and watch for missed/queued lag.
4. Verify no increased bulb resets or command failures in logs.
