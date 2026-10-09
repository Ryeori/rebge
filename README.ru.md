[English version](README.md)

# REBGE

Проверяемая реконструкция Beyond Good & Evil 20th Anniversary Edition на Rust/Bevy.
Это собственная реализация по реверсу, а не восстановленные исходники разработчика, доступа к ним у меня нет и быть не может.

## Цель проекта

Восстановить исходный код, который собирается в игру, максимально близкую к оригиналу.
Сначала точность. Перенос на другой движок - потом.

## Требования

- Windows x64 - проверенная на текущий момент платформа.
- Rust stable, Cargo и toolchain MSVC.
- Visual Studio Build Tools: **Desktop development with C++** и Windows SDK.
- Рабочий драйвер видеокарты; текущая сборка проверена с Vulkan.
- Отдельный runtime pack ассетов: в репозитории исходников его нет.
- Интернет для первой загрузки зависимостей Cargo либо готовый локальный кеш.
- Python3.10+ для экспорта и проверки. Python-пакеты указаны в `requirements.txt`;
  для запуска уже скомпилированного preview Python не нужен.

Оригинал игры, Ghidra и зависимости автоматизации нужны для соответствующих флоу
реверса, а не для запуска готового runtime pack.

## Быстрый запуск

1. Открой PowerShell в корне проекта; проверь `rustc --version` и `cargo --version`.
2. Получи отдельный runtime pack и положи его содержимое в
   `asset-packs/stage43-runtime/`. Должен существовать файл
   `asset-packs/stage43-runtime/scenes/sally-hangar/scene.json`.
   Без извлечённой библиотеки ассетов пакет нельзя создать из одних исходников.
3. Собери и запусти:

   ```powershell
   cargo build --locked --manifest-path bevy/Cargo.toml
   .\run-hangar.cmd
   ```

4. Для Python-инструментов установи зависимости и проверь пакет:

   ```powershell
   python -m pip install -r requirements.txt
   python tools/assets/export_runtime_pack.py --check-pack asset-packs/stage43-runtime
   ```

Если пакет находится в другом месте, задай абсолютный путь в `$env:REBGE_ASSETS`
перед запуском. Отсутствующий пакет нужно подключить: сборка кода его не создаёт.
Ошибка линкера MSVC обычно означает отсутствие C++ Build Tools или Windows SDK.

## Прогресс и milestones

Текущая точка: **4.3 завершена для проверенного среза** (10 октября 2026).
Jade управляется в ангаре: анимации, skinning, ходьба, бег, старт, остановка и развороты.
Все 89 тестов прошли, включая приватные fixtures. Код разложен по системам,
тесты вынесены отдельно, ассеты подключаются отдельным пакетом.
Вся игра ещё не восстановлена; полное совпадение поз и физики пока не подтверждено.

| Milestone | Статус |
|---|---|
| 1. Чтение ресурсов и локализация | Завершено |
| 2. Геометрия и ассеты ангара | Статическая сцена готова |
| 3. Первая запускаемая сборка Bevy | Завершено |
| 4.1–4.2. Данные персонажа и основа анимаций | Завершено для выбранного среза |
| 4.3. Движение и анимационные переходы | Завершено для проверенного среза |
| Подготовка репозитория и отдельного пакета ассетов | Завершено |

## Roadmap

- **4.4:** физика движения, коллизии, контакты и гравитация.
- **4.5:** поведение оригинальной камеры, ограничения и препятствия.
- **4.6:** интеграция и сравнение полного управляемого среза ангара.
- **5:** взаимодействия, диалоги, AI, бой, задания, звук и переходы сцен.
- **6:** расширение покрытия игры, проверка сохранений/загрузки и подготовка runtime.
- **Позже:** возможный перенос на другой движок после реконструкции.

Подробнее: [стадии](docs/STAGES.md).

## TODO для README

- [ ] Добавить раздел Ghidra: настройка, подключение локального MCP и флоу анализа кода.

## Структура

| Каталог | Назначение |
|---|---|
| `bevy/src/animation/` | Восстановленные численные алгоритмы |
| `bevy/src/input/` | Ввод, selector/predicates, adapters |
| `bevy/src/world/animation/` | data/controller/pose/stepping/ecs/telemetry |
| `bevy/src/{app,assets,camera,world,ui,debug}/` | Остальные системы runtime |
| `bevy/tests/unit/<system>/` | Тесты по структуре систем |
| `bevy/tests/fixtures/` | Небольшие численные fixtures |
| `tools/`, `docs/` | Реверс, экспорт, замеры, форматы и доказательства |
| `AGENTS.md`, `.agents/skills/` | Правила и навыки агентов |

Ассеты, raw recordings, база Ghidra и сторонние бинарные установки — отдельные локальные
зависимости, исключённые `.gitignore`. [Состав репозитория](docs/REPOSITORY_LAYOUT.md).

## Сборка и тесты

Проверенная среда: Windows x64, Rust stable, MSVC C++ Build Tools/Windows SDK.
Bevy0.19; версии зависимостей закреплены `bevy/Cargo.lock`. Из корня проекта:

```powershell
cargo build --locked --manifest-path bevy/Cargo.toml
cargo test --locked --manifest-path bevy/Cargo.toml
```

`--offline` подходит, когда зависимости уже доступны. Private fixtures требуют локальных
`assets/` и `reports/`; полная проверка checkpoint89tests:

```powershell
cargo test --offline --manifest-path bevy/Cargo.toml -- --include-ignored
```

[Структура и зависимости тестов](docs/TESTING.md).

## Подключение ассетов и запуск

Пакет с `manifest.json`, `scenes/`, `textures/` подключается отдельно.
По умолчанию launchers используют `asset-packs/stage43-runtime/`; иной путь задаётся так:

```powershell
$env:REBGE_ASSETS = (Resolve-Path ./asset-packs/stage43-runtime).Path
.\run-hangar.cmd
```

`run-preview.cmd` открывает из того же пакета диагностическую сцену. Прямой запуск:

```powershell
.\bevy\target\debug\rebge.exe --assets "$env:REBGE_ASSETS" --scene scenes/sally-hangar/scene.json
```

Также: `./bevy/Run-Rebge.ps1 -Assets <каталог> -Capture`.
Для запуска готового пакета оригинал и Ghidra не нужны.
WASD/левый стик — движение; Shift/R2 — ускорение; правый стик/мышь — камера;
R — сброс сцены, P — пауза. Это playable preview, не полная игра.

## Создание пакета

Python3.10+, standard library; полная локальная library уже должна существовать:

```powershell
python tools/assets/export_runtime_pack.py --source assets --output asset-packs/stage43-runtime
python tools/assets/export_runtime_pack.py --check-pack asset-packs/stage43-runtime
```

Экспорт включает только зависимости ангара/контролируемой сцены и сохраняет source/payload
SHA256. Исходные ассеты остаются на месте. [Формат пакета](docs/RUNTIME_ASSET_PACK.md).

## Реверс и агенты

[Индекс механизмов](docs/REVERSE_INDEX.md), [STAGES](docs/STAGES.md).
Порядок: native-code audit → гипотеза → тест оригинала → парное сравнение → исправление.
Игровой ввод эксклюзивно у одного агента; после ввода release и возврат фокуса в Codex/ChatGPT.
Глобальные плагины устанавливаются отдельно; проектные навыки лежат `.agents/skills/`.
Для readers/экспорта оригинала: `python -m pip install -r requirements.txt`.
Исторические probes могут требовать настройки путей конкретной установки; см. документацию/help.

Репозиторий создаёт пользователь; подготовка не выполняет git init, commit или публикацию.
