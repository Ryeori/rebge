---
name: rebge-native-measure
description: Record and qualify original BGE movement, animation transitions and runtime inputs across controlled scenarios.
---
# Controlled native measurement
Use [rebge-game-check](../rebge-game-check/SKILL.md) for scene/input work. Read the current handoff and relevant raw evidence.
1. State the unresolved variable. Repeat a test with a changed hypothesis, pattern, duration or observer. For acceleration, hold opposite sprint through turn79, exit80 and run2; releasing during79 measures stopping.
2. Refresh Get-Process bge, its bge.exe module base and runtime pointers. Historical addresses belong only to their original trace.
3. Inspect tools/jade/drive_start_capture.py --help. --run-reverse-hold controls sprint before reversal; --run-reverse-after controls opposite sprint after it. Keep the relevant event within capture_tracking_sequence.py's bounded recording window (--max-seconds defaults to5 and accepts1..8; sample cap256).
4. Retain raw trace, external input timestamps, captures, stderr, exact scenario parameters and input SHA256 under reports/. Release keys in finally even on capture failure.
5. Run audit_reverse_capture.py <trace> for source signatures/actions/phases. Use jade_trace_consistency.rejection_reasons for source/clock qualification. Qualify selector, speed and pose with their own consistency markers.
6. Use audit_postturn_acceleration.py <traces> --output <report> for post-turn timing, diagnostic velocity and source-exit slopes. It retains per-subsystem qualification and associates new input records. Summarize sampled boundary intervals, scalar input, speed byte, blend state and source-root movement. Preserve but exclude terrain fall/ledge/grab runs from intended gait comparisons.
## Evidence limits
Sequential reads are not atomic callback inputs. Equal bytes do not prove writer order. Source signatures do not prove full poses. Actor displacement / sample wall time is diagnostic speed, subject to mixed frames and timing. Keep source units distinct from metres; retain rejected cases and missing inputs.
## Done
Every scenario has a trace/input record, qualified phase summary, contamination decision and bounded conclusion. Request human preparation only for an actual unavailable scene/input.

