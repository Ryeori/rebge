# Актуальная контрольная точка — 2026-10-10

Текущий milestone: подготовка к репозиторию завершена; см. верх HANDOFF.md и README.md. Runtime ассеты отдельно в asset-packs/stage43-runtime (41файл), animation runtime разделён на6модулей, тесты в bevy/tests/unit.89полных/23обычных теста PASS, сборка и capture ангара из внешнего пакета PASS. Пользователь создаёт Git самостоятельно;4.4 не начата.

Эта запись и верх HANDOFF.md имеют приоритет над историческими сводками.
Подстадия4.3 завершена в принятом practical slice:89 private tests PASS/build PASS,
независимые clock/local-pose fixtures и итоговые три native-first live probes.
Source playback/skin, старт/остановка, gait transitions, standing/moving turns
подключены; пользователь принял текущий movement. Sprint start исправлен на
123→1→3→2 без лишней4; phase Bind сохраняет active incoming blend.
Запуск `run-hangar.cmd`; итоговая сборка загружена в ангар.

Stage4 остаётся открыта. Следующее4.4: native velocity/gravity/contact solver,
collider и units. Camera controls работают, ограничения/препятствия отдельны.
Sharp-stick turn physics в согласованном backlog. Selection velocity, steering,
walking dwell и outgoing root context приближённые; full native VM/pose/physics
parity и покрытие всех72cases не заявлены. Water D90057F2 — временный материал.
Evidence: reports/jade/movement-suite/stage43-final-postfix-paired-audit-20261010.json;
reports/bevy/stage43-run-mode-regression-r2-tests-20261010.txt; HANDOFF.md.
Новые узкие агенты — с пустым контекстом; native-code audit ПЕРЕД game probes;
game lock эксклюзивно root, после ввода release+focus ChatGPT.

## Исторические сводки (не текущее состояние)

LATEST2026-10-09:28/28RusttestsPASS;023957rootbasis129primary/57transitionPASSwithin1e-5,maxRust1.013279e-6;explicitobservedreferences,notatomiccallbackinputs.11rootdropsareforwardkeyboundaries;2repeatincrementsnativecontrollerpathtraced. Nextboundedrootclock/controllergates+referenceentrysideeffects+phaserepeatlimit,thenframepipeline. Nonewgameneededyet;ECSplaybackstillopen. HANDOFF.mdhascurrentdetails.

LATEST2026-10-09: runtime_pose mapping+ordinarychannelbridge complete;2720localwritesmatch,23/23RusttestsPASS. Root/rebased/proceduralbranchesstillseparate. Nextexplicitrootrotation/context thenframepipeline/ECS. Workautonomously,notifyonlywhenuser/gameattentionneeded.

LATEST2026-10-09: actor_reference.rs added;32stationaryprimaryrootpositionsEXACT;22/22RusttestsPASS. Moving/transition/rootrotationinputtiming stillopen. Nextexplicitpriorlocals/runtimeclonemap/rootcontexts->worldpose/ECS.4.3INPROGRESS.

# Состояние проекта — возобновлено 2026-10-09

Работа возобновлена по просьбе пользователя 2026-10-09.
Для текущих offline задач запуск игры и пользовательский ввод не требуются. Текущая стадия: 4.3, НЕ завершена.
Все проектные файлы находятся в C:/Users/Dan/Desktop/rebge.

## Подтверждённые результаты

- Архивы BPAK и локализация EN/RU: доступ и экспорт восстановлены; 300 пар TXI/TXS проверены round trip.
- Статическая сцена ангара: извлечена и ранее показана в Bevy. Запуск viewer подтверждён; идентичность рендера оригиналу не доказана.
- Комплект Sally: 26 meshes, 50 materials, 26 textures, 214 animation resources. Привязка 47 animation slots к 48 объектам исходного скелета проверена.
- Rust animation core: channels, transition clock, pose blend, tracking phase, hierarchy, skeleton, binding, sparse local_pose.
- Все 214 клипов проходят проверку привязки. Сборка локальных записей позы проверена на 2880 вращениях из записи ходьбы; предоставленные позиции вне корня совпадают точно. Для вращений допуск 1e-5.
- Смешивание проверено на 684 native вращениях (максимальная ошибка Rust 5.9604645e-8). Таймеры переходов сверены с записями оригинала.
- Последняя полная проверка: cargo test --offline -- --include-ignored — 20/20 PASS после добавления world_pose (2026-10-09).

## Что ещё не готово

- Автономное продвижение часов клипа и полная state machine персонажа.
- Полная поза кадра и её мировые матрицы с корректным actor/root reference и runtime clone semantics.
- ECS skeletal playback и динамический skinning: новые математические модули ещё не подключены к отображаемому персонажу.
- Tracking при движении: точные входы native callback не получены. Матрица актёра, reference и brain offsets меняются между ordinary и corrected публикациями. Совпадение промежуточных idle проверок не доказывает walking parity.
- Небольшие расхождения root reference при движении около 1.5e-5 остаются; допуск не повышать ради их скрытия.
- Procedural modifiers, scale/alternate channel/event branches и VM не перенесены полностью.
- Игровое движение, collision solver, оригинальная камера, AI, бой, взаимодействия, задания, звук, сохранения и все сцены не реализованы в полном объёме.
- Все ассеты игры ещё не приведены к конечным редактируемым форматам. Аудио преимущественно сохранено в исходных Wwise форматах; пробные декодирования не означают готовую звуковую систему.
- Pey'j: обсуждён общий подход, перенос его контроллера/state machine не выполнен.

## Проверки и evidence

Сводка: reports/bevy/stage43-animation-core-validation.json.
Приватные traces/fixtures: reports/jade/. Вывод Ghidra: reports/ghidra/raw/.
Последний движущийся fast trace: stage43-tracking-order-20261008-191518.json,
1072 observations, 4 clip runs; callback marker edges 32/29, ноль полностью
внутри callback 3; ноль стабильных input windows для принятия walking tracking.
Это ограничение измерения, а не доказательство правильности/неправильности всего writer.
Ghidra project сохранён ранее; последние MCP операции были только чтением.

## Следующие шаги

1. Продолжить offline: собрать локальные матрицы из явно переданной предыдущей позы и sparse writes.
2. Рассчитать parent-first мировую иерархию, отдельно восстановив root conversion и исходные/runtime flags. Не заменять отсутствующие каналы финальной измеренной позой.
3. Проверить на существующих данных, затем подключать ECS bones/skin. Запуск viewer с новыми анимациями до этого не заявлять.
4. До нового walking tracking теста изменить способ получения callback inputs либо восстановить VM/root-motion порядок по коду. Не просить повторять тот же цикл ходьбы без изменения измерения.

При будущих динамических тестах пользователь управляет игрой. Давать короткий
сценарий с целью и точными действиями; agent исследует и анализирует самостоятельно.
После перезапуска игры обновлять PID/base и full snapshot; не использовать старые указатели.
Следующая крупная стадия требует подтверждения пользователя; стадия 4 уже одобрена.


2026-10-09: Bevy hierarchy::compose_tracking_world/world_pose реализуют native1409b4e70 traversal bit400000,отдельно отtarget bit1;накоплениеchild-to-root сnativef32ассоциацией.360stored-world сравнений из8qualifiedsamples190347 проходят1e-5. Slots27/28 исключены заранее из-заmodifier24;флаги output не сверены. Входы: recordedfinal locals+explicitrootworld,не source-only animation. Fullsource->world/ECS playback/rootrefs всё ещё не готовы. Следующее: explicit local pose/root conversion и runtime/source clone mapping для соединения sampler сworldcomposer.
