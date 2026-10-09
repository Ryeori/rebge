---
name: rebge-game-check
description: Launch and exercise REBGE or original BGE on Windows, capture the result, and validate a movement or rendering scenario.
---
# Launch → exercise → validate
Use universal-modder:game-automation for live input. Read the current handoff.
1. Identify the target and refresh PID/path: rebge.exe is the preview; bge.exe on E: is the original. A request to try the current iteration normally means REBGE. Build only if changed/stale.
2. Launch REBGE with --assets <project>/assets --scene scenes/sally-hangar/scene.json; confirm scene/gamepad in the log. run-hangar.cmd is the user entrypoint.
3. Define a distinguishing input pattern and acceptance criterion. Ask for terrain preparation only when needed and wait for readiness. Existing user authorization persists; this skill grants none.
4. Observe a GPU-safe screenshot before input. Original opens pause on focus loss. Resume an observed menu; --loaded means a loaded scene was observed already.
5. Use UM foreground guards and finally-release of held keys. Desktop isolation can report a false missing window; request execution escalation when required.
6. Retain input commands, before/after captures and relevant logs in reports/. Validate the observed result, including terrain interference. A successful process exit alone proves no game feel.
## Target ambiguity
UM Drive('bge') and shot --exe bge.exe can match rebge.exe. Close only the freshly identified REBGE PID before original observations, or use a verified exact target. Preserve the original process/save. Background helpers use hidden windows.
## Done
Requested target is loaded, or the scenario has observed results and explicit pass/fail/blocked reasons. For launch alone, stop after confirming load.
