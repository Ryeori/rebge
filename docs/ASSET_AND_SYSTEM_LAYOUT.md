# Ассеты и игровые системы

Все извлечённые ресурсы хранятся в локальной библиотеке пользователя:
`./assets/`. Исходники и инструменты находятся в проекте.
Путь библиотеки передаётся runtime через `--assets`; сцену выбирает `--scene`.
Локальная папка проекта содержит оригинальные ассеты; они исключены из Git
и не включаются в публикацию runtime.

## Каталог ассетов

- `models/meshes/<key>.json` — геометрия в исходных осях и масштабе.
- `textures/<key>.png` — полноразмерный первый цветовой поток.
- `materials/<key>.json` — подтверждённые ссылки на текстуры и ограничения.
- `scenes/<scene-key>/scene.json` — сцена и связи объектов.
- `texts/<locale>/<group-key>.json` — lossless локализация и управляющие коды.
- `animations/`, `skeletons/`, `collisions/` — после подтверждения форматов.
- `animations/sally/local-samples/<key>.json` — декодированные ключи дорожек,
  исходные байтовые сегменты, SHA256 ресурса и неподтверждённые поля.
- `animations/sally/local-rotation-poses/<key>.json` — локальные вращения
  и матрицы Jade/Bevy; привязка к 47 GAO кандидатная, полной позы ещё нет.
  Эти экспорты учитываются в stage4-sally-animations/local-poses reports;
  основной catalog.json пока описывает прежний набор из 470 ассетов.
- `animations/sally/local-translation-samples/<key>.json` — позиции ключей
  и control points, SHA256 исходного ресурса; без полного playback.
- `skeletons/sally/gao-parent-links.json` — 47 объектов и native parent links;
  дополнительно внешний корень CE00A6D3 (всего 48 объектов), skinning
  и привязка списка дорожек ещё не восстановлены.
- `skeletons/sally/gao-rest-pose.json` — исходная поза, собранная из
  native linked matrices; пока без применения анимаций и skinning.
- `skeletons/sally/animation-binding.json` — подтверждённый порядок
  47 объектов, соответствие индексам дорожек и цепочка native consumers.
  Отчёт stage4-sally-animation-binding.json сохраняет границы сегментов
  и список дорожек, которым нужен обработчик событий/переходов.
- `audio/wwise-source/<archive>/banks/` и `streamed/` — извлечённые BNK/WEM; исходное кодирование, SHA256 и индексы встроенных медиа в stage4-wwise-audio-source-export.json. Пока без PCM-конвертации и регистрации в catalog.json.
- `audio/wwise-source/<archive>/embedded/<bank>/<media-id>.wem` — 1197 полных встроенных медиа, отделённых от 7755 потоковых префиксов; SHA256 проверены.
- `audio/decoded-probes/<archive>/<media-id>.wav` — 16 проверенных PCM-примеров; назначение не классифицировано, массовая конвертация и HIRC-связи ожидают разбора.
- `sounds/sfx/`, `sounds/music/`, `sounds/voice/` — после определения роли и кодека.
- `ui/`, `vfx/` — после определения зависимости и назначения ресурса.
- `catalog.json` — archive/key/type/path, source SHA256, exported SHA256,
  версия конвертера, зависимости и ограничения каждого экспорта.

В каталог не помещать ресурс по предположению о типе. Неизвестные форматы
оставлять в списке нерешённых ресурсов каталога. Пустая папка не означает,
что соответствующая система игры восстановлена. Подтверждённые форматы
экспортировать по зависимостям сцен и персонажей, затем расширять покрытие.
Первый набор: ангар, его meshes/materials/textures и EN/RU texts. Нормали,
сжатые вспомогательные texture streams и mesh tails не терять в reader;
ограничения конвертированной версии перечислять в catalog.

## Код Bevy

- `src/main.rs` — только точка входа и объявление модулей.
- `src/app/` — CLI, конфигурация, запуск и регистрация систем.
- `src/assets/` — схемы ресурсов, загрузка, валидация, координаты, локализация.
- `src/world/` — создание сцены и объектов.
- `src/camera/` — камера и ограничения; diagnostic orbit отдельно от native follow.
- `src/input/` — обработка и подтверждённый фильтр ввода.
- `src/ui/` — интерфейс и диагностическая панель.
- `src/debug/` — screenshots и проверки запуска.

По мере восстановления добавить `animation/`, `physics/`, `character/`,
`audio/`, `ai/`, `interaction/`, `dialogue/`, `combat/`, `progression/`,
`save/`. Создавать реальные модули с реализацией; не имитировать готовность
пустыми системами. Каждая новая система обязана иметь своё имя/путь,
привязку к evidence реверса и перечисленные расхождения с оригиналом.

## Порядок разработки

1. Структурировать уже написанный runtime и доступные ассеты.
2. Достроить комплект Sally: geometry, skins, behavior, skeleton/animation.
3. Подтвердить один переход анимации и его отображение.
4. Восстановить движение/контакты и камеру.
5. Связать персонажа и сцену в Bevy и сравнить с оригинальным поведением.
6. Исследовать звук и остальные системы отдельными проверяемыми срезами.

Ассетная библиотека расширяется в каждой подстадии. Общая стадия4 остаётся
незавершённой до управляемого персонажа и проверки поведения.

## Реализованный первый набор

Экспортёр `tools/jade/export_asset_library.py` создал470зарегистрированных
записей:61mesh,46полноразмерных color textures,53materials,9material groups,
1scene,300EN/RUtext groups. SHA256 всех выходных файлов проверены;
300побайтовых round trips локализации прошли. Оригинальные контейнеры
известных ресурсов сохранены отдельно для повторной конвертации.
Texture27000502 остаётся неизвестной. Этот первый catalog.json ещё не включает последующие экспорты анимаций, скелетов и исходного Wwise-аудио; их состояние описано выше и в отчётах stage4. UI/VFX остаются pending.

Runtime уже разделён на указанные модули и читает постоянную библиотеку.
Сборка и3Rust tests прошли; ангар запущен и кадр проверен визуально.
Snapshots сохраняются отдельно в `./reports/bevy/captures/`.

Character kit Sally: `assets/models/characters/sally/manifest.json`, `native-pose.obj/.mtl`; source meshes/materials/textures stay in their typed directories. `assets/scenes/sally-runtime-skin/scene.json` is a static runtime-palette snapshot; dynamic animation belongs in a separate Bevy animation system during4.3.
