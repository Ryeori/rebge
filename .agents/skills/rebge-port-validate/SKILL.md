---
name: rebge-port-validate
description: Port qualified BGE movement or animation mechanisms into Rust/Bevy and validate native fixtures and preview continuity.
---
# Qualified mechanism → playable verification
Use [rebge-native-code](../rebge-native-code/SKILL.md) for arithmetic and [rebge-native-measure](../rebge-native-measure/SKILL.md) for missing evidence.
1. Separate native algorithms from preview adapters. Preserve f32 order and explicit inputs. Label provisional scheduling, steering, interruptions and subjective tuning.
2. Native parity tests use independent native fixtures. Preview scenarios check continuity/finite poses/state reachability, not original behavior. Root agreement does not validate a whole pose.
3. Run relevant checks, then cargo test --offline --manifest-path bevy/Cargo.toml -- --include-ignored. Preserve failures; distinguish actor motion from limb vertex displacement.
4. Build cargo build --offline --manifest-path bevy/Cargo.toml. Close only the freshly identified preview PID if its binary is locked. Use [rebge-game-check](../rebge-game-check/SKILL.md) for visual/user comparison.
5. Retain validation report with source hashes, scenarios, errors, approximations and exclusions. Update docs/handoff at a completed task/milestone or request; preserve the historical pause checkpoint. Movement/transitions precede expansion of connected assets/idle animations.
## Clip bank regeneration
Ordinary builds need no export. When full regeneration is necessary, the base exporter overwrites the bank. Verify inputs and preserve order: export_sally_playback_preview.py, export_turn_preview_bank.py, export_run_preview_bank.py, export_restart_second_phase.py, export_standing_turn_bank.py (tools/jade).
## Done
Checks pass, current binary contains the change, and parity claims are bounded by independent evidence. Subjective feel remains a user comparison when measurements cannot establish it.
