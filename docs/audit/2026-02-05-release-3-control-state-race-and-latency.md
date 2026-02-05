# Release 3: Selected-Bulb State Race Fix + Faster HSV Path (2026-02-05)

## Root Cause Found
Control-panel color state was synchronized in an effect that depended on the full `bulbs` array. This caused selected-color controls to be overwritten when *unrelated* bulb updates arrived over WebSocket, producing stale/stuck color indicators.

## Fixes
1. Frontend selected-bulb sync logic:
- Added explicit `selectedBulb` derivation and synchronized controls only when the selected bulb changes.
- Kept the short local-interaction guard window to avoid stale overwrite during active drag/click.
- Split auto-selection of first bulb into its own effect.

2. Frontend latency tuning:
- Debounce is now action-aware:
  - HSV: 80ms
  - Other actions: 120ms

3. Backend latency tuning:
- Action-aware API debounce:
  - HSV/hex color: 90ms
  - Other actions: 120ms
- Transport pacing tuned further:
  - `MIN_COMMAND_INTERVAL_SECONDS`: 0.12 -> 0.10
  - `GROUP_COMMAND_SPACING_SECONDS`: 0.02 -> 0.015

## Expected Result
1. Color swatch, brightness gradient, and wheel selection should remain synchronized under rapid interactions.
2. Faster perceived color-change response while preserving anti-flood protections.
