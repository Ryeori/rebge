---
name: rebge-native-code
description: Inspect BGE native functions and constants through local Ghidra and derive bounded algorithms for REBGE.
---
# Native function → bounded algorithm
Use universal-modder:reverse-engineering. Current entrypoints/limitations are in docs/HANDOFF.md; keep private artifacts inside the project.
1. Search reports/ghidra/raw, tools/jade and bevy/src before requesting new decompilation.
2. Use tools/ghidra/Read-Ghidra.ps1 with tool inspect, action decompile, file_name bge.exe, verified address and max_lines 0. Save raw response in reports/ghidra/raw/. Refresh localhost Ghidra availability.
3. Identify readers/writers, gates, time source and state lifetime. Separate descriptor speed binding, VM speed writer, input filter, transition clock and root/reference publication. Verify decompiler types/arguments against listing where arithmetic depends on them.
4. Read constant bytes and preserve f32 bits, operation order, conversions and units. Runtime/source flags and actor/reference/procedural writers are different contexts.
5. Compare independent native records with explicit inputs. A plausible formula or late-snapshot match does not establish callback chronology. Leave unsupported gates and prior-state inputs visible.
## Done
Result gives provenance, inputs, writers, arithmetic and unresolved branches. Mark preview heuristics as approximations. Update documentation at milestones or on request.
