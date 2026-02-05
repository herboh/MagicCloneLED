# LED App Regression Checklist

Run this after backend/frontend changes to avoid reintroducing control bugs.

## Setup
1. Start backend and frontend.
2. Select one online bulb.
3. Open browser devtools network tab (optional, for request pacing checks).

## Single Bulb Color Sync
1. Click 8-10 distinct spots on the color wheel quickly.
2. Drag around the wheel continuously for 10-15 seconds.
3. Confirm the wheel marker, hex swatch, and brightness gradient stay in sync.
4. Confirm bulb color tracks UI changes without long stalls.

## Brightness And Warm White
1. In RGB mode, drag brightness from 100 to 0 and back.
2. Confirm command succeeds at 0 and bulb reaches minimum output.
3. Toggle warm white on and set brightness to 0, then 100.
4. Confirm no API validation errors and UI remains responsive.

## Group Safety
1. Select a group with multiple bulbs.
2. Drag color wheel for 5-10 seconds.
3. Confirm bulbs update without resets/re-initialization behavior.
4. Confirm no flood of duplicate requests for unchanged payloads.

## Connection Resilience
1. Refresh page and verify WebSocket reconnects.
2. Navigate away/unmount UI and back.
3. Confirm no runaway reconnect loops and status returns to Connected.

## Pass Criteria
1. No stuck color preview state.
2. No HTTP 500 responses for invalid client input paths.
3. No observable bulb overload behavior under rapid interaction.
