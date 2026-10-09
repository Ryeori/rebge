# Тесты checkpoint4.3

Все89 Rust tests находятся в `bevy/tests/unit/` по исходной структуре:
`animation/<algorithm>.rs`, `input/<algorithm>.rs`, `assets/scene.rs`, `world/animation.rs`.
Runtime содержит только `#[cfg(test)] #[path="..."] mod tests;`.
Это unit child modules, а не Cargo integration crates: приватные API остаются приватными.

```powershell
cargo test --locked --manifest-path bevy/Cargo.toml
cargo test --offline --manifest-path bevy/Cargo.toml -- --include-ignored
```

Первый уровень использует код и небольшие `bevy/tests/fixtures/`.
Второй требует локальных `assets/` и `reports/`: независимые native recordings и derived
scene/pose/input fixtures. Они не входят в Git. Пути private fixtures относительно
`CARGO_MANIFEST_DIR/..` сохранены. Runtime asset root можно менять, но это не переносит
автоматически test fixtures. Отсутствие данных не означает успешного прохождения private tests.

Новые тесты хранить в `tests/unit/<system>/`. Native parity проверять независимой записью;
synthetic preview tests проверяют continuity/finite values/state reachability.

Каталог живых сценариев — `tools/jade/movement_cases.json`; runner — `run_movement_case.py`.
Порядок: native-code → гипотеза → dry-run → готовность сцены → запись → квалификация → сравнение.
Каждый запуск ограничен объявленным case. Оригинал/REBGE имеют единый эксклюзивный game lock.
Ввод сбрасывается при ошибке, затем фокус возвращается в Codex/ChatGPT.

Для automation отдельно нужны ViGEmBus, Python vgamepad, universal-modder и Ghidra MCP.
Сторонние бинарники не входят в репозиторий; для обычной игры они не нужны.
Основной runner и return-focus принимают `REBGE_UM_ROOT`/`REBGE_VGAMEPAD_ROOT`;
без override используются установленные Python-модули либо локальные fallback.
Остальные исторические probes проверять по help и документации до запуска.
