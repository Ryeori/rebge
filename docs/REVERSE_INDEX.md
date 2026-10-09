# Индекс механизмов

| Механизм | Native entry | Код |
|---|---|---|
| Input filter/scalar |1560E4150|input/blend.rs, animation_selector.rs|
| Ordinary mode1/2 table |141013870|input/animation_selector.rs|
| Animation selector |140C25CC0|input/animation_selector.rs|
| Turn predicate |1411DAF10|input/turn_predicate.rs|
| Heading |14110D470|input/native_steering.rs, diagnostic_steering.rs|
| Descriptor/phase binding |1409AD760,1409BD3B0|animation/action_transition.rs, primary_phase.rs|
| Transition clock |1409BCD20|animation/transition.rs|
| Root/reference |140B49FB0,140B27EB0|animation/root_*, reference_*, actor_reference.rs|
| Runtime velocity writer |1409ECFC0|Evidence only; input caller не полностью увязан|

Кодовые пути относительно bevy/src/. Численное ядро и интеграция различны:
world/animation/ содержит scheduling и явно ограниченные adapters (selection velocity,
eligibility/dwell/outgoing root context). Совпадение ветки не доказывает whole pose/physics.
Procedural/modifier paths покрыты частично. Декомпиляция не считается исходниками разработчика.

Подробности: MODLOG.md, STAGE4_REVERSE.md, SCENE_FORMATS.md.
Private raw evidence — reports/; Ghidra wrappers — tools/ghidra/.
