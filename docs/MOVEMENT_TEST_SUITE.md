# Воспроизводимые проверки movement и transitions

Набор входит в stage4.3. Источник сценариев — `tools/jade/movement_cases.json`,
генератор — `movement_suite.py`. Сигнал каждого теста задаётся точками
`t,x,y,r2`; между точками выполняется линейная интерполяция. Дискретный скачок
задан интервалом10ms; удержание — двумя одинаковыми точками. Плановая частота
ввода100Hz; фактические timestamps сохраняются и имеют приоритет.

## Порядок прохождения

| Очередь | Категория | Изменяемые условия | Что проверяем |
|---|---|---|---|
| 1 | input_threshold | strength0.10..1.00, включая0.14/0.16/0.35/0.65 | deadzone, начало движения, scalar, выбор gait |
| 2 | start | rise0/0.10/0.20/0.35/0.70s | Slow/Start/Walk, задержка старта, разгон |
| 3 | standing_turn | оба направления, те же скорости нарастания | gate116/117, сторона, final heading |
| 4 | standing_release | hold0.05/0.12/0.25/0.35/0.50/0.75s | entry/body/exit interruption, blend с idle |
| 5 | gait | walk-stop, run-stop, run↔walk, R2 до начала движения | фазовая цепочка, скорость, dwell, continuity |
| 6 | run_reverse | run0.50/1.30/2.80s, opposite held1.8s | 79→80→2, ускорение, обратный рывок |
| 7 | stop_reentry | neutral gap0.05..2.20s | очередь запросов, stop/idle/waiting, blending |
| 8 | turn_angle | ±45/90/120/150/170/180° | угловой gate, разворот или обычный steering |
| 9 | interrupt | смена направления через0.08/0.20/0.35s | pending target и ответ на ввод во время клипа |
| 10 | noise | слабый противоположный отскок0.05/0.10/0.14/0.16 | ложный разворот при отпускании |
| 11 | collision | стена прямо/под углом, отдельно подготовленная сцена | blockage, Slow, slide; пока не готовая parity-система |
| 12 | camera | заранее повернутая камера | camera-relative движение; измерить yaw отдельно |

Для каждого ID — три независимые записи оригинала и REBGE. `--repeat` — метка
повтора, не команда автоматического повторения. Сначала один проход каждой
категории; для найденных различий — остальные повторы и пробы вокруг границы.
Все cases исходно pending. Catalog не является журналом подтверждённой parity.

## Подготовка

Оригинал: загруженная ровная открытая площадка, без уступов/врагов/interaction,
место для указанного пробега. Физический геймпад отключён; виртуальный DS4
принимается оригиналом, виртуальный Xbox в предыдущей проверке игнорировался.
Оригинал не сбрасывается/телепортируется: после каждого теста проверяем сцену.
Для wall cases пользователь отдельно готовит стену. Прежняя готовность открытой
сцены не разрешает автоматически считать готовой сцену у стены.

Подготовка facing: короткий левый/правый ввод, neutral1.2s. Это намерение runner,
не гарантия native idle: первичные state/source snapshots и снимок проверяются.
Camera orientation и controller device остаются частью записи. REBGE перезапускает
preview черезR перед case; позиция/камера оригинала должны сравниваться относительно
своего начала, абсолютные координаты двух сцен не сравниваются.

Не запускать долгий batch без наблюдения. Одна команда = один case. В original
режиме runner отвергает одновременно запущенную REBGE из-за UM substring matching.
`--resume-menu` применяется только после наблюдения pause menu. При потере
foreground или ошибке виртуальный ввод сбрасывается; память игры не изменяется.

## Команды из корня проекта

Проверить каталог и расписание без ввода:

```powershell
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/movement_suite.py
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/test_movement_suite.py
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/run_movement_case.py --case standing_right_rise_0.20 --target original --dry-run
```

Оригинал после проверки сцены (desktop execution требует разрешения среды):

```powershell
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/run_movement_case.py --case standing_right_rise_0.20 --target original --scene-ready --repeat 1
```

Preview запускается с opt-in telemetry; без переменной обычный запуск не пишет
файлы и не считает centroid. Каталог назначения уже должен существовать:

```powershell
$env:REBGE_MOVEMENT_TRACE='C:/Users/Dan/Desktop/rebge/reports/bevy/movement-frames.jsonl'
$env:RUST_LOG='info'
& C:/Users/Dan/Desktop/rebge/bevy/target/debug/rebge.exe --assets C:/Users/Dan/Desktop/rebge/assets --scene scenes/sally-hangar/scene.json
```

В другом shell, после загрузки:

```powershell
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/run_movement_case.py --case standing_right_rise_0.20 --target preview --scene-ready --repeat 1 --preview-trace reports/bevy/movement-frames.jsonl
```

Каждый запуск создаёт уникальный `reports/jade/movement-suite/<case>-<target>-rN-<timestamp>/`:
`run.json`, before/after PNG, и `preview.json` для REBGE. Original/controller
collector paths содержатся в run.json; сырые файлы остаются в reports/jade.

```powershell
& C:/Users/Dan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe tools/jade/compare_movement_cases.py <native-run.json> <preview-run.json> --output reports/jade/movement-suite/comparison.json
```

## Разбор и критерии

Runner проверяет свежий нейтральный waiting123 без активного blend в течение
0.15s перед началом записи. Иначе завершает case с ошибкой; нельзя сравнивать
начало ввода в готовом idle с вводом во время предыдущего перехода. Старые
run.json без readiness comparator маркирует setup_unqualified.

Для held threshold проб используйте `tools/jade/audit_stick_threshold.py`:
сохраняются SHA256, rejected samples, стабильная native norm и фактически
доставленные WinMM X/Y. Номинальная команда отличается от доставленного
значения из-за квантования. Ghidra140d01010/listing140d01870 подтверждает
component gate0.35 и saturation выше0.925; перенесено в input/stick.rs.
Exact native device normalization, camera-change latch и gameplay diagonal
validation остаются открытыми. Standing predicate1411daf10 найден, но для
его переноса нужны новые standing_turn_inputs с полным actor/global контекстом.

Автоматический результат всегда needs_review, а не PASS. Сначала проверяем, что
оба target приняли заданный сигнал, timestamps/coverage достаточны и сцена не
загрязнена. Затем — action+phase sequence, времена входа/выхода, native blend
table, speed byte, heading, displacement и профиль ускорения. Исходные clock
bytes и native input markers анализируются отдельно от qualification целой позы.

Ориентир для timing disagreement — больше двух игровых кадров и sampling
uncertainty; устойчивое отсутствие/лишний action — отдельный дефект независимо
от похожей картинки. Не назначать всеобщий допуск скорости до проверки units,
terrain и native sampling. Actor jump и mesh/root jump разделять. Telemetry
сохраняет source actor matrix и Bevy mesh centroid в разных координатных базисах.

Проверенная parity: совпали квалифицированные входы и механизм в заданном
сценарии. Approximate: preview adapter дал подходящее поведение, native writer
ещё не перенесён. Blocked: неготовая сцена, controller ignored, unknown mapping,
недостаточное окно/coverage. Rejected сырые записи не удаляются.

Comparator пока не декодирует TurnStop: такая фаза делает сравнение неполным,
а не успешным. Native read-time velocity диагностическая; пики из последовательного
чтения нельзя считать истинной скоростью. Совпадение gait/root не доказывает
полную позу. Jerk/pose continuity проверяется дополнительно по preview root locals,
centroid, кадрам и независимым native pose channels с проверенной индексацией.

Следующие расширения после первых расхождений: доставка timeline в simulation
frame time вместо desktop wall time; независимая pose metric; camera yaw capture;
верификация TurnStop mapping; статистика трёх повторов и интервалы переходов.
