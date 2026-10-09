# Репозиторий checkpoint4.3

Добавить: `.gitignore`, `README.md`, `AGENTS.md`, `.agents/skills/`, `bevy/Cargo.toml`,
`bevy/Cargo.lock`, `bevy/src/`, `bevy/tests/`, launchers, `tools/`, `requirements.txt`, `docs/`.
Модули runtime: app/assets/animation/input/world/camera/ui/debug. World animation разделён
на data/controller/pose/stepping/ecs/telemetry без изменения native f32 порядка.

Информация реверса — REVERSE_INDEX, форматы, MODLOG/STAGES.
Проектные навыки входят в `.agents/skills/`; глобальные plugins устанавливаются отдельно.

Локальные зависимости исключены `.gitignore` и сохранены на месте:

- `asset-packs/`: подключаемый runtime content с SHA manifest.
- `docs/HANDOFF.md`: локальная передача сессии, не входит в репозиторий.
- `assets/`: полная библиотека для exporters/private tests.
- `reports/`: memory recordings/derived fixtures/raw validation.
- `ghidra/`, `references/`, `OLD_TEST/`: база/внешние исходники/старые бинарники.
- `bevy/target/`, caches, downloaded/vendor automation/audio packages.

Runtime pack не содержит все214animationassets/audio/texts/native fixtures.
Документы с private evidence refs остаются в Git; полный validation требует local bundles.
После создания repo проверить git status и staged diff. `.gitignore` не снимает уже tracked
файлы с index. Подготовка не включает remote, commit, публикацию или назначение лицензии.
