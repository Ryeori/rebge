---
name: rebge-movement-loop
description: Run the REBGE movement case suite against original BGE, qualify differences, investigate native mechanisms in Ghidra, and iterate Rust/Bevy fixes with paired regression measurements.
---
# Movement case -> native mechanism -> verified reconstruction

Read current docs/HANDOFF.md, then docs/STAGES.md and
[test suite plan](../../../docs/MOVEMENT_TEST_SUITE.md). Use the existing executable
catalog and ledger; do not replace them with an informal test list.

## Human preparation and game navigation
Before every original experiment block, describe the case IDs, input pattern,
duration and required space. Ask the user to put Jade in the centre of the field,
stop movement and disconnect the physical controller. Wait for readiness.
One readiness may cover the announced bounded block while screenshots and state
records show the same safe scene; changed terrain, a ledge or an unknown menu
requires new preparation. Do not infer readiness from a timeout or an old run.

Use [rebge-game-check](../rebge-game-check/SKILL.md) for target identity, launch,
screenshots, focus and navigation. This includes returning from an observed pause
menu; it is not a general menu search algorithm. Inspect unfamiliar menus before
acting. No automatic original restart/save/load or teleport is part of this loop.

## Iteration
1. Select one category and explicit hypothesis from
   reports/jade/movement-suite/ledger.json. Start with an existing difference,
   then thresholds/start/standing/gait. Terrain-dependent cases remain separate.
   Dry-run the case; preserve catalog/hash, build and setup context.
2. Use [rebge-native-measure](../rebge-native-measure/SKILL.md). Run
   tools/jade/run_movement_case.py for original after preparation, and preview
   with REBGE_MOVEMENT_TRACE enabled. Virtual DS4 is the qualified device.
   Refresh exact PID/base; close only preview if UM target ambiguity requires it.
   Input is neutralized on foreground loss/error. No memory writes.
3. Compare with tools/jade/compare_movement_cases.py. Review actual delivered
   controller input, initial action/phase, active blend and camera/facing before
   attributing a missing action to code. Preserve rejected reads. A logical idle
   action can still contain an incoming active blend; setup wait alone proves none.
   Repeat twice for an explicit reproducibility hypothesis; change the probe or
   observer when repetition cannot resolve the uncertainty.
4. Separate transport/mapping, filtered scalar/direction, selector gate, action
   binding, blend clock and root/pose publication. Use
   [rebge-native-code](../rebge-native-code/SKILL.md): search saved decompilation,
   follow relevant writers/readers using local Ghidra MCP wrapper, retain native
   constants and f32 order. Do not tune timing around a transport/setup defect.
5. Implement the smallest qualified mechanism using
   [rebge-port-validate](../rebge-port-validate/SKILL.md). Unknown native inputs
   remain explicit; temporary preview adaptations have named bounds and limits.
   Regression fixtures come from independent original records. Run relevant
   checks, full private-inclusive offline suite and build.
6. Repeat the distinguishing original/preview case and adjacent affected cases,
   using announced preparation. Compare timing intervals, action/phase chain,
   speed and heading. Actor/source motion and Bevy mesh/root motion use distinct
   bases. Action agreement is not full-pose parity.
7. Update ledger/history with evidence paths, hashes, rejected inputs, mechanism,
   residual error and next case. Summarize docs/handoff at the completed fix or
   category, not each command. Continue until a real scene/tool/user dependency.

## Decisions
- recorded_unqualified / needs_review: raw measurements, not successful parity.
- difference_candidate: delivery/setup appear comparable; repeats/mechanism pending.
- confirmed_difference: repeatable qualified disagreement with uncertainty stated.
- approximate: acceptable preview adapter, native mechanism still incomplete.
- verified: independent native fixtures and paired affected cases support the
  stated mechanism and bounds; never broaden to full pose/game parity.
- blocked: unavailable scene/device, unknown mapping or insufficient observation;
  retain evidence and request the specific missing assistance.

Do not auto-run the whole catalog from one readiness. Choose small relevant blocks,
inspect the scene between runs, and stop input immediately on contamination.

