> Текущий статус: возобновлено 2026-10-09; стадия 4.3 не завершена.
> Актуальная сводка: CONTEXT.md; продолжение: RESUME.md.
> Ниже — исторические записи: прежние NEXT/NOTverified/PASS counts относятся к моменту записи.

# Стадия 4: подтверждённые результаты

## Актуальный проход 2026-10-08: полный список Sally и action consumer

Конечная цель уточнена пользователем: полная реализация игры на Bevy,
редактируемые ассеты и проверенное совпадение всего игрового поведения.
Текущие промежуточные результаты этой цели пока не достигают.

`probe_sally_parts.py` проверил все 47 записей `.gao` ресурса7100AF2A
и 26 уникальных visual geometry. Все 26 разобраны существующим type1 reader
с сохранением неизвестных байтов при roundtrip; trailing_size каждого8.
24 geometry имеют8вершин/12треугольников;620030FB имеет464/862,
620030F7 имеет107/145. Соответствующие GAO:CE00A4B0 и62000404.
Роль этих объектов и принадлежность видимой модели ещё не доказаны;
список47 не объявлен скелетом. Метаданные и SHA:
reports/jade/stage4-sally-all-parts.json.

Ghidra MCP снова доступен после открытия перенесённого проекта.
Geometry resource dispatcher140a39860 читает type первого uint32,
ограничивает type<=12 и вызывает reader из DAT14209ba20 со stride0x50.
Это отдельная таблица от geometry-modifier DAT1419b0ac0 stride0x28;
смешивать их назначения нельзя.

Action-list thunk1409bd970 ->1535a0cc0 читает количество из размера/8
в обычной ветви (в другой ветви размер/4). Ресурс71004D9B содержит235
пар `.act`; loader ставит ключи в очередь с callback1409bdbc0.
1409bdbc0 читает count byte и второй byte заголовка, затем в обычной
ветви4-байтовый заголовок и20-байтовые записи, разворачивая их в32байта.
Первый ключ записи ставится в очередь через140b442c0, третий —1409beef0.
После записей есть дополнительные условные данные, ещё не разобранные.
Семантика полей, временные единицы и формат animation resource пока открыты.
Полный код локально: reports/ghidra/raw/rebge-stage4-geometry-wrapper-loader.json,
rebge-stage4-action-list-loader-body.json, rebge-stage4-action-reader.json.
Следующее: проследить140b442c0/1409beef0, затем написать проверяемый
reader actions и animation links с сохранением всех неизвестных полей.

## Actions: проверка всех слотов и первый animation loader

Уточнение прежней записи:71004D9B содержит235 слотов, а не235 действительных
`.act` записей. 36 слотов целиком нулевые; остальные199 содержат `.act`.
Новый probe сохраняет пустые позиции и порядок списка.

`jade_actions.py` читает обычную ветвь1409bdbc0: header `<BBH>`, record
`<III4BHBB>` размер20. Поля пока названы по позиции; первый и третий uint32
подтверждены как resource keys отдельными callback очереди. Поддержан writer
из JSON-представления с непрочитанным хвостом hex и сохранением padding.
199 реальных actions прошли decode/encode byte exact. Counts записей:
160 actions по1,36 по2,2 по3,1 по5. Все214 уникальных первых resource keys
присутствуют в Resources.pak. Непрочитанные tail bytes суммарно9612.
Три теста прошли: отклонение усечённых записей, изменение ключа без изменения
остальных байтов, сохранение хвоста пустого action. Это проверяет формат
префикса, но не завершает восстановление действий/анимации.

Loader140b442c0 читает `<HH>` count/flags, затем variable-length tracks:
8-байтовый header track, условная GAO reference, далее140b43db0.
GAO reference ставится в очередь1409ea250, что связывает tracks с объектами.
Все214 ресурсов имеют flags2; count44..50 (44:102,45:59,46:27,47:23,
48:1,49:1,50:1). Count ещё не называется количеством костей или кадров.
140b43db0 читает count ключевых записей, переменную ширину первого поля,
переиспользование flags и ветви данных по маске0x7c0; ветвь0x80 вызывает
140b49120, ветвь0x40 —140aeace0. Их семантика/сжатие ещё открыты.
Третий callback1409beef0 ->153629c80 читает byte count и тройки байтов
в две runtime-таблицы; это ещё не доказательство событий/звуков.

Evidence: reports/jade/stage4-sally-actions.json; полные Ghidra outputs
rebge-stage4-animation-resource-loader.json, animation-track-reader.json,
action-third-loader-body.json в reports/ghidra/raw/.
Следующий срез: conditional action tail и variable tracks, compressed
reader140b49120; затем проверка поз и привязок к47GAO. Стадия4.2 продолжается.

Стадия одобрена пользователем и продолжается. Оригинальная игра не запускалась.

`jade_callbacks.py` прочитал PE и нашёл 3864 кандидата именованных callbacks:
uint64 key/name pointer/function pointer. Метаданные — stage4-native-callbacks.json.
Выбранные записи и переходы сверены через Ghidra MCP.
Общий heuristic scan также захватил служебные таблицы с малыми ключами;
3864 нельзя считать числом доказанных игровых callbacks. При сопоставлении
ресурсов исключены ключи ниже01000000 и sentinelFFFFFFFF; выбранные
таблицы поведения дополнительно сверяются по тегам .ofc.

Sally_sa_exec_joynorm_blend: вход 1410643d0 переходит в 1560e4150.
Вектор смешивается с предыдущим через alpha = clamp(delta * 12, 0, 1).
Константа 12 подтверждена по 14173cc60, последовательность MULSS/MAXSS/MINSS
проверена в listing. src/motion.rs переносит эту формулу; пока она используется
только диагностической камерой. Физические единицы времени и обычная камера
персонажа ещё не доказаны. Sally и Jade_Sister нельзя считать одним контроллером.

GAO 3D0030FF содержит последовательность компонентов 4, 20, FFFFFFFF.
Компонент 4: offset 7936, end 191628, 6 наборов по 1907 вершинам,
2 вторичных набора с 6 и 2 индексами. Число 1907 совпадает с mesh 16003795.
Reader 1409d49d0 и update 1409d3670 подтверждают аддитивные взвешенные
смещения исходных позиций. Это не доказательство скелетной анимации.
Временной driver, значения runtime весов и идентичность объекта ещё неизвестны.

Компонент 20: reader 1409d03b0 -> 15382da90, виртуальная таблица
1419a1900. После wrapper type/instance идут 4 uint32, 4 float32,
условные два float3 и последний float32. Векторы записаны только если
четвёртый float равен DAT_14173c8ec = c520803f (float32 1.001).
В этом объекте размер с wrapper 68 байт, end 191696; следующий uint32 —
FFFFFFFF, collision key начинается в 191700. Семантика полей пока не названа.
Все прочитанные слова и неизвестные промежутки сохраняются побайтово.

`probe_actor_fields.py` проверяет обе GAO, компоненты и точную границу
collision tail. Результат stage4-actor-fields.json содержит только метаданные.
Полный оригинальный decompile/listing сохранён вне проекта в reports/ghidra/raw/rebge-stage4-*.
Shape-list readers 153d0dde0/1409e8540 пока не классифицированы как анимация.

## Подстадия 4.1: уточнение component20

Регистрация 1409afd30 назначает slot 1419a1918 на 1409d0d50 и
slot 1419a1920 на 1409d1430. Ghidra memory/read показывает в обоих
случаях байты c20000 — x86-64 RET imm16(0). Update slot не меняет
состояние; гипотеза, что этот callback двигает phase компонента 4,
исключена. Это не исключает обращений других функций к полям component20.
В Ghidra создана функция RE_Component20_UpdateNoop по 1409d0d50;
decompile подтверждает немедленный return. Изменена только база анализа,
не bge.exe. Полный вывод — reports/ghidra/raw/rebge-stage4-component20-update-confirmed.json.

Подстадия 4.1 завершена для этого среза: callbacks, readers, границы,
input filter и исключение неверного driver. План 4.2–4.6 находится в STAGES.md.
Следующее точное действие: decompile Sally_sa_init по 141313190;
проследить доступ к brain/action ресурсам и найти соответствующий GAO.
После идентификации персонажа искать writer phase/weight его анимации.
Критерий всей стадии 4 не достигнут.

## Подстадия 4.2: первый проход после организации папок

Прочитан Sally_sa_init141313190 (526 строк; полный вывод во внешнем TEMP).
Аргументы lookup140aeac00 проверены в Resources.pak: 140005AA,26003A64,
3500E1D5,71003F5A,71003FF9,71004BD8,71004BD9,71005CE1,7100AED2,
9E00049B присутствуют. Callback key7100AF12 также имеет ресурс.
Семантика всех ключей пока не установлена.

Lookup140aeac00 — бинарный поиск по таблице key/value из 16-байтовых пар,
возвращает FFFFFFFFFFFFFFFF при отсутствии. Это не loader сам по себе.
3500E1D5 и71003F5A — GAO с дополнительными pre-action ветками;
они пока не декодированы, моделью Jade эти объекты не объявлены.
710047BC — GAO с hierarchy710047FF; ссылка встречалась в обработчике
ввода. Mesh refFFFFFFFF, material62000CDC: модель персонажа не доказана.

DAT1420d6620 используется Sally_sa_init для action selection, но функция
140b272a0 меняет его для конкретного script/action execution context и
восстанавливает прежнее значение. Это не доказанный постоянный player pointer.

Метаданные: ../reports/jade/stage4-character-resource-probe.json.
Инструмент: ../tools/jade/probe_character_resources.py. Каждый ресурс
ограничен4MiB; неподдержанные ветки отмечаются, ссылки не угадываются.
Следующее: восстановить pre-action GAO branches bit1/bit22 в1409ea250 для
3500E1D5/71003F5A, затем пройти hierarchy/brain/action до mesh персонажа.
4.2 продолжается; критерий персонажа не достигнут.

## Подстадия 4.2: подтверждена таблица поведения Sally

В 1409ea250 разобраны pre-action ветки bit22 (word+68 bytes),
bit1 (4 words) и bit21. При bit24 массив содержит8-byte key/word records;
иначе serialized matrix68 плюс64legacy bytes, всего132байта.
Размер runtime matrix68 нельзя использовать как stride архивного массива.
GAO71003F5A содержит47записей132bytes, actionwordsFFFFFFFF/1/255/0,
behavior71003F58 и brain9E005E4D. GAO3500E1D5 содержит32записи,
behavior3500E1FA. Значения pre-action words пока не названы семантически.

Поле bit5, ранее предварительно названное hierarchy, — behavior descriptor:
native loader140b40340->155a6f210 читает два ключа и планирует загрузку
definition через140b3e8e0->155a5c520, а второго блока через140b3eb90.
Definition loader делит размер на8 и проверяет теги .ofc, отдельно .ova.
Поэтому новое имя в probe — behavior; старые отчёты сохраняют прежний label.

Проверенная цепочка: GAO71003F5A -> descriptor71003F58 ->
definition71000CDD + block71003F60. В definition632bytes имеется79tagged
records: одна .ova71000CDC и78 .ofc. Все78ключей .ofc сопоставлены с
именованными nativecallbacks, включая Sally_sa_exec_init_normale,
Sally_sa_exec_animselector и Skins_RealoadSallySkin. Это доказывает связь
GAO с обычным контроллером Sally; идентичность render mesh ещё не доказана.

GAO710047BC через710047FF->71003B21 связан с Global_glob_* callbacks,
следовательно, его не следует принимать за персонажа лишь из-за ссылки
из input handler. Brain9E005E4D содержит ссылку .smd260029E5 (64bytes).
Skin reload1411b0430 также непосредственно запрашивает71003F5A;
обращается к0700654D и9E001C0D, но их роль требует дальнейшего просмотра.

Evidence: reports/jade/stage4-character-resource-probe.json,
stage4-character-links.json, stage4-character-links-deeper.json.
Полные decompile во внешнем reports/ghidra/raw/rebge-stage4-behavior-loader.json,
ofc-table-loader.json, matrix-flags-reader.json, sally-skin-reload.json.
12Python tests прошли; реальные ресурсы прочитаны с проверками границ.
Следующее: definition .ova71000CDC, skin resources0700654D/9E001C0D,
native skin reload и GAO geometry branches до конкретного mesh. 4.2не завершена.

## Дальнейший проход4.2 и библиотека

Skin group0700654D — kind4, четыре material resources07006BC4,
07006BC6,0700654E,07006BC8; каждый дочерний ресурс — kind5.
Это материалы, не geometry.9E001C0D — отдельный GAO с behavior9E001C0F
и brain9E005E61; его роль ещё не доказана. .ova71000CDC имеет35486bytes.

Pre-action words GAO71003F5A:7100B0E7,A9001F3E,7100AF29,71004D9B.
Последний ресурс1880bytes содержит235tagged.act records; первые
71004D9C/D9D/D9E существуют и ссылаются на7100B0E7/E8/E9.
7100AF29(16bytes) ->7100AF2A(376bytes) ->47.gao records.
Первые CE00A4AC/CE00A53B/CE00A53C/CE00A53D имеют visual geometry refs
CE00A48A/CE00A499/CE00A49A/CE00A49B. Их geometry kind1, но всего8вершин;
они могут быть служебной геометрией. Полноценной моделью Sally не объявлены.
Связь235actions с47parts — следующий проверяемый срез; также нужно
проследить native consumer7100AF29 и действительную render geometry.

Evidence: stage4-sally-skin-resources.json, stage4-sally-geometry-candidates.json,
stage4-sally-mesh-action-links.json, stage4-sally-visual-parts.json,
stage4-sally-visual-resources.json в reports/jade/.
Параллельно выполнен ASSET_AND_SYSTEM_LAYOUT.md для уже подтверждённого
набора ангара/текстов; это не означает завершение reverse персонажа.

## 2026-10-08 — compressed animation tracks and local rotation poses (4.2)

Evidence from Ghidra MCP: 140b442c0 resource loader, 140b43db0 key reader,
140b49120 compression, 140b48f70 quaternion accessor, 140aed650 matrix builder,
140b486d0 mirrored rotation application, 140b482f0 interpolation consumer,
140b49ba0 indexed target/root consumer. Constants read from static program memory:
14173cf6c = 32767; 14173c214 = 1/1024; 14173c8e8 = 1;
14173cd70 = 60; 14173c670 = 0.5. Raw outputs remain in reports/ghidra/raw.

New jade_animation.py reads ordinary PC tracks, including byte-duration keys,
shared transform headers and shared frame flags. All 214 Sally resources parsed
through EOF with zero opaque tails: 97,481 keys; transform flags 0090 (68,586),
0010 (9,058), 0001 (19,533). 77,644 quaternion samples, zero relative quaternion
encodings in this corpus. Absolute compressed XYZ uses signed int16 / 32767;
W = sqrt(max(0, 1 - XYZ squared)). Unimplemented masks fail explicitly.
Segment reconstruction is byte-exact for all resources; this is boundary/source
preservation validation, not independent confirmation of numeric poses or an
editable typed-field writer. Local JSON retains source segments and SHA256.

jade_pose.py exports native local rotation matrices and Bevy basis conversion
(x,z,-y), honoring native frame flag20 Y/Z sign flips. Output lives under
assets/animations/sally/local-samples and local-rotation-poses. SHA256 manifests:
reports/jade/stage4-sally-animations.json and stage4-sally-local-poses.json.
Largest quaternion squared-norm deviation: 8.17097082217444e-08.
All non-root rotation slots fit the 47-object candidate list; FFFF is the actor
root in 140b49ba0. List identity, parent hierarchy and translation consumers
remain to prove. Full skeleton pose, skinning and Bevy playback are not complete.
Four tests passed: shared headers/extreme quaternion, every truncation boundary,
Jade-to-Bevy matrix basis, native mirror/root mapping.

Next: confirm short1 indices against 7100AF2A, follow bit22 linked GAO transforms,
recover translation application and exact interpolation/time progression.
GAO bit23 is conditional interpretation inside bit13 action data, not by itself
an extra payload; the older actor probe currently skips it conservatively.

## 2026-10-08 — parent links and translation channels (4.2)

probe_sally_transform_links.py extracts bit22 link key + 68-byte matrix from
47 GAOs. There are 46 links:45 internal, one external CE00A6D3, slot38 unlinked.
Native1409b4e70 follows runtime link+8 through ancestors and combines each local
matrix+10, then the terminal GAO matrix. Parent semantics are now confirmed.
Graph validation detects cycles and duplicate keys; observed max internal depth7.
Scale-aware140ae9c00 delegates multiplication to140ae9420; exact composition,
external root and indexed object-list identity remain pending before full poses.

Translation accessor140b4ae30 returns first float3 for transform flags&3. Consumer
140b49fb0 writes position to target matrix+30/34/38 and supports linear (one point),
quadratic (two points), cubic (three points) segments. Cubic coefficient at
14173cb3c read via MCP =3. Frameflag20 mirrors X; multi-point mirrored handling
explicitly rejected pending assembly verification. jade_pose.py implements these
curves given fraction[0,1]; native time writer/endpoint selection not emulated.

Exported214 local translation JSON resources with19533 position samples and
sourceSHA256 under assets/animations/sally/local-translation-samples. Native
parent graph saved assets/skeletons/sally/gao-parent-links.json. Hash manifest:
reports/jade/stage4-sally-translations.json. Six animation/pose tests pass,
including interpolation controls and graph cycles/external roots. Full pose,
skinning and Bevy playback still pending. Next:CE00A6D3, indexed binding,
140ae9420 multiplication and native track time progression.

## 2026-10-08 — external root and original linked pose (4.2)

Expanded ancestor traversal (bounded128objects) finds CE00A6D3:flags00000880,
no parent, original translation about(2.27e-8,4.69e-6,-0.6898523). Closed graph:
48GAOs, maximum depth8. Native140ae9420 implements column-major parent*local;
1409b4e70 accumulates linked local transforms then terminal GAO world matrix.
Current linked matrix flags are2/6, no scale bit8. jade_pose.affine_product and
assemble_rest_pose implement this branch and explicitly reject scale bit8.

Export assets/skeletons/sally/gao-rest-pose.json, SHA256 and comparison evidence
reports/jade/stage4-sally-rest-pose.json. Maximum difference from independently
stored GAO world matrices is6.07685617956712. This is not a parity validation.
Native1409b59d0 updates linked local matrix from world and inverse parent world,
confirming separate world/local representations; current game state still needed
to establish which saved configuration is displayed. No animation binding assumed.
Seven reader/pose tests pass, including noncommuting rotated/translated parent
composition and unsupported scale rejection. Next:7100AF29 loader and runtime
indexed7100AF2A binding, native track time writer, animated pose assembly.

## 2026-10-08 — indexed binding and restricted forward timing (4.2)

Static chain proves Sally's indexed list identity:1409ea250 stores pre-action
word2(7100AF29) at visual+8;1409bf060 supplies it as param3 to1409be7b0;
1409ed490→153d51380 loads descriptor firstword7100AF2A through1409ed200;
153d2d340 reads8-byte GAO pairs in source order;153602b50 clones sequentially;
1409be7b0 attaches cloned list at visual+10;140b49ba0/140b49fb0 select short1
from indexedlist+18 with16-byte stride. FFFF selects actor root71003F5A.
Native clone parent remapping is separate from original asset ancestor graph.

Export assets/skeletons/sally/animation-binding.json and SHA256 manifest/report
reports/jade/stage4-sally-animation-binding.json.214resources,9613tracks,
47valid indexed slots. 9522tracks contain simple transform keys;91contain
non-transform event/jump/control records and are explicitly unsupported.

140b272a0 native timing:duration=ticks/60, elapsed+delta capped at current key;
overshoot carried, exact equality stays outgoing key, loop/terminal branches
controlled by runtime flags and actor context. jade_animation_time.py implements
restricted positive-time transform-only segments with explicit loop/hold policy.
It does not emulate native event VM, context-specific terminal behavior or
runtime mode selection.9tests pass: exact boundary, carry, multi-cycle looping,
zero-duration rejection, unsupported command tracks, prior pose/reader checks.

140aecfd0 quaternion interpolation resembles shortest-path spherical rotation,
but decompile loses XMM fraction and sign operations. Next inspect140aed150
and assembly before implementing interpolation; then control-track semantics,
combined position/rotation snapshot and cloned parent mapping. Bevy playback
and numeric/visual parity against live game remain pending.

## 2026-10-08 — native rotation interpolation (4.2)

Read-only Ghidra MCP evidence: quaternion-interpolation-assembly, quaternion-weight-helper, quaternion-normalize, quaternion-threshold, quaternion-sign-mask under reports/ghidra/raw/rebge-stage4-*.
140aecfd0 saves incoming fraction XMM3 to XMM9, passes it as helper XMM1. Negative dot canonicalizes second quaternion using PADDD with four 0x80000000 words (verified memory14173da50), then clamps dot to1. Threshold14173c1f0 is float bytes95bfd633. Near-equal branch leaves angle0; helper140aed150 returns first quaternion unchanged, even at fraction1. Other branch uses angular sine weights and normalizes with14009bae0. jade_pose.interpolate_rotation reconstructs these mathematical operations without mutating caller inputs. Python double/libm differs from native single-precision SSE and bundled CRT; bit-exact parity is not claimed.
Validation:11 animation tests pass, including half-turn midpoint, opposite signs, near-equal hold, endpoints, invalid input. Full animated pose, cloned external-parent remapping,91 control tracks and Bevy playback remain pending. Next combine timed local rotation/translation after resolving destination matrix selection and cloned parents.

## 2026-10-08 — timed local channels and clone destinations (4.2)

Added tools/jade/jade_animation_sample.py and export_sally_timed_channels.py. Report reports/jade/stage4-sally-timed-channels.json covers214resources/9613tracks with four explicit hold-policy probes per track;9522supported,91event/jump tracks explicitly rejected. Inputs carry decoded JSON SHA256. Probes are local channel writes, not full world poses or runtime playback parity.
Ghidra153602b50 remaps an internal source parent to the matching clone entry, clears external parents (runtime pointer sentinels1/2 require separate treatment). The47-object clone map records source parent, clone parent and destination. Consumers140b49ba0/140b49fb0 write linked matrix at link+10 for GAOflag400000, otherwise GAO+10 matrix. Translation consumer can switch effective parent to actor on transformflag20 and call1409b59d0 to rebase; static clone mapping alone cannot define every animated world pose.
Sampler implements ordinary position/rotation channel interpolation, duration-zero and translation no-interpolation flag800 branches. Time remapping/alternate endpoint flags8/40, mirrored multi-control curves and event tracks fail explicitly. Rotation consumer selects next rotation directly at segment end, bypassing near-equal helper hold; regression test covers this distinction.13tests pass.
Next: inspect general rotation path140b482f0, actor/world conversion and parent switching/rebase; apply channels into seeded clone matrices before full pose export. Bevy animation/skinning remains pending.

## 2026-10-08 — channel application to clone local matrices (4.2)

Read general rotation consumer140b482f0 through MCP; evidence reports/ghidra/raw/rebge-stage4-general-rotation-interpolation.json. It holds current rotation for zero duration, missing next rotation or frameflag800; chooses next directly at endpoint; mirrors Y/Z for frameflag20; other supported branches call140aecfd0. Updated sample_local_track accordingly. Matrix-source rotation conversion and alternate endpoint remain outside support.
Added sample_clone_local_matrices: seed linked_local_matrix or gao_matrix by GAOflag400000; apply ordinary quaternion basis and position writes independently in track order; preserve unwritten matrix entries. Explicitly reject actor root and dynamic parent switching context. It does not assemble world matrices or claim clone initialization/runtime parity.
export_sally_local_matrix_snapshots.py writes reports/jade/stage4-sally-local-matrix-snapshots.json:214 midpoint snapshots,9094applied tracks,428actor-root tracks rejected,91event tracks rejected. Zero complete snapshots because every clip has actor-root channels. No observed parent-switch rejection at these midpoint samples; this does not prove all runtime states avoid it.15tests pass, including component preservation, source immutability and general rotation hold behavior.
Next resolve actor reference matrix DAT1420c3470 writers and native composition140ae9870/140b48240; then assemble complete pose and verify against original runtime. Bevy playback remains pending.

## 2026-10-08 — explicit actor-root reference conversion (4.2)

New MCP evidence: root-reference-xrefs, root-reference-check140b48240, root-rotation-compose140ae9870, root-position-transform140ae9fb0, root-reference-owner1409ad760, root-update-context1409c1c50 in reports/ghidra/raw/rebge-stage4-*. Existing140b28360 update selects reference pointer: absent without GAOflag04000000; matrixblock+44 when bit10000 clear, +88 when set. Track actor binding can preserve caller reference for null object binding; global DAT1420c3470 is transient context, not a permanent Sally asset matrix.
140b48240 scans tracks up to the current track for the same effective actor, transform kind80 and frameflag4. Position conversion depends on this scan; rotation composition independently uses reference basis.140ae9870 composes reference*local basis subject to native identity flags, without writing position.140ae9fb0 rotates position then caller adds reference translation; scale-bit8 has a separate branch.
Added jade_animation_root.py: reference_matrix_offset and convert_root_channels with explicitly supplied runtime matrix, flags and translation gate. No guessed default matrix. Scale-bit8 unsupported.17tests pass, including reference block selection, rotated/translated position and independent translation gate. Full snapshot export still rejects actor-root tracks until actual runtime context is available; previous report remains partial. Next recover reference block initialization/writes and scan semantics per resource, then integrate root writes and runtime clone hierarchy.

## 2026-10-08 — root reference refresh (4.2)

MCP evidence root-reference-refresh1409c1d60, root-reference-initialize1409c0850, root-action-update1409bcd20, root-refresh-default-reference and its xrefs saved under reports/ghidra/raw/rebge-stage4-*.
1409c0850 evaluates animation with zero delta at CURRENT track state, temporarily removing scale and using DAT14195aee0 as initial reference. It transposes evaluated rotation, transforms negative position, and composes current actor matrix with inverse evaluated root through140ae9c00. This is a refresh at current state, not a time-zero asset transform. Main animation writes selected matrixblock+44/+88; transition animation writes its own block+10.1409c1d60 gates refresh by actor flags2/04000000 and active animation, optionally also transition state.
Added rigid_inverse and refresh_root_reference in jade_animation_root.py for orthonormal no-scale branch: reference=current_actor*inverse(evaluated_root). Inputs must be explicit; scale branch rejected.18tests pass, including noncommuting actor/root reconstruction and scaled basis rejection.
Static bytes at14195aee0 contain identity matrix with flags0. Xrefs include writes1409979a2/154b1b381; therefore do not assume runtime contents immutable from initial PE bytes. Next inspect these writers and runtime track-state/first-key flag4 gate, then integrate explicit-context root writes into local snapshots. Complete pose/Bevy playback still pending.

## 2026-10-08 — root integration with explicit diagnostic context (4.2)

Read writer targets1409979a2→1409973e0 and154b1b381→154b1b340 through Ghidra MCP. Both copy identity basis/position constants into DAT14195aee0 and mask flags with2. Evidence default-reference-writer-a/b. Observed writes reset the shared reference; no claim about undiscovered indirect writes.
sample_clone_local_matrices now accepts explicit root_context: actor_matrix, reference_matrix, reference_flags, per-track translation_gates. Root channels apply independently in track order to actor destination, preserving unwritten entries. Without context actor roots remain rejected. Runtime gate computation, action blending and cloned parent/world composition remain pending.
Exporter --neutral-root-diagnostic supplies explicit identity actor/reference and false gates. New separate report stage4-sally-neutral-root-snapshots.json:214resources,9522applied tracks,129complete LOCAL channel snapshots,85partial resources due to91control tracks. This chosen diagnostic state is not captured original runtime and these are not complete world poses. Existing context-free snapshot report preserved.19tests pass including root integration and input matrix immutability.
Next implement runtime140b48240 gate from effective actors/current frame flags, track-state first-key flag4 initialization, then linked clone world assembly and visualization.

## 2026-10-08 — runtime gate and post-clone actor attachment (4.2)

Read153219c00 through MCP: reports/ghidra/raw/rebge-stage4-clone-actor-parent-attach.json. This is called at end1409be7b0 AFTER clone remapping. All objects acquire linked flag400000 if absent. Null effective parents become actor; local matrix is replaced with GAO matrixblock+44. First list entry with null parent and bit10000 clear initializes its extra matrix from default reference and runtime position globals1420b0bc8/bcc/bd0. Existing bit10000 branch copies its existing extra matrix instead. Therefore old local snapshots describe incomplete attachment initialization, not full runtime skeleton.
Added translation_reference_gate explicit runtime entries:140b48240 inclusive scan through current index, resolve null actor to default actor, require same effective actor + current transformkind80 + frameflag4. No mutation of decoded source flags; first-track initial runtime flag4 seen in1409be7b0 is caller-specific and cannot be applied indiscriminately to199actions.
Added jade_clone_pose.assemble_attached_clone_base_world: requires explicit attachment matrices for null-parent entries and evaluated actor matrix, applies actor attachment and parent*local hierarchy, rejects missing/cyclic links. BASE pose only: animated channels must be applied after attach initialization; do not feed old snapshots and claim animation parity.21tests pass including same-actor gate boundaries and noncommuting actor/child composition.
Next extract GAO extra matrixblock+44 data and initialize clone local matrices BEFORE animation application. Then world pose export and visual check. Diagnostic129complete-local snapshots remain limited and are not complete native attached/world poses.

## 2026-10-08 — source clone initialization and sampled world matrices (4.2)

MCP clone1409a7170 saved gao-clone-matrices.json; loader1409ea250 evidence confirms bit10000 copies the first source GAO matrix into runtime block+44. It is not another serialized matrix. Sally detached clone roots:slot0CE00A4AC(parent externalCE00A6D3 cleared) andslot38A9003C48(no source link); both have bit10000. Attach153219c00 copies this extra matrix into local linked matrix and assigns actor parent.
initialize_source_clones reconstructs this source-state initialization for observed roots, rejects absent bit10000 runtime-position cases. assemble_sampled_clone_world composes AFTER channel writes, preserving animated root-object writes. New report stage4-sally-attached-world-snapshots.json:214resources,47object world matrices per midpoint,129complete supported-channel snapshots,85partial/91controltracks. Explicit identity actor/reference and disabled translation gates remain a chosen diagnostic context; prior runtime matrix updates, clone position overrides, action blending/VM and skinning are not reproduced. Source bit8 scale branch not supported.
22tests pass including attachment-before-animation order and source immutability. Previous neutral-root report retained as historical pre-attachment diagnostic. Next visualize complete diagnostic world poses and implement effective runtime frame/gate state before native playback parity.

## 2026-10-08 — interactive diagnostic pose viewer (4.2)

Added tools/viewer/pose_viewer.html: offline canvas projection of47 GAO world positions and parent links, resource selector, complete-channel filter, optional object basis axes, orbit/zoom/reset. No external libraries. serve_scene.py accepts --viewer pose without changing default hangar viewer behavior.
Server session24543: python tools/viewer/serve_scene.py --assets reports/jade --port8182 --viewer pose. Opened http://127.0.0.1:8182/ in app browser, verified resource7100B0E7 shows47objects/44applied tracks/0unsupported; screenshot visually confirms central humanoid hierarchy plus widely separated auxiliary objects. These auxiliary roles remain unclassified; do not claim every GAO is a bone or the result matches original runtime. Viewer accurately labels neutral context and missing model/skinning/parity. Screenshot save to reports/bevy/captures denied EPERM; image inspected in browser tool output only.
Next classify far-away auxiliary GAO and control91tracks; add true timed sequence only after runtime flags/gates are resolved. Existing22 Python tests unchanged.

## 2026-10-08 — control-track inventory and native record fields (4.2)

probe_sally_control_tracks.py outputs stage4-sally-control-tracks.json. Actual91unsupported tracks contain304non-transform keys:154kind0000 with no payload,150kind0040 events,2290event source records. No kind200/400 jump keys occur in this Sally set. Previously generic event/jump wording should not imply observed jumps.
MCP140aeace0 evidence event-record-loader.json confirms ordinary serialized8-byte record <iHBB>: signed32 value,16bit selector, metadata byte, dispatch byte. Expanded runtime record is16bytes; script dispatch uses last byte through PTR_FUN141958b78. Added typed native_records while preserving original bytes/opaque pairs. Semantic opcode/selector mapping is unresolved.
140b272a0 event branch can conditionally wait using frameflags8/10 and VM stack result; cannot treat all events as cosmetic or simply remove them. Event execution updates script context and stack globals. Added signed/truncation record test:23animation tests pass. Next map observed dispatch categories and selectors to native handlers, then implement event timeline/VM required for faithful animation/gameplay.

## 2026-10-08 — two-level VM dispatch (4.2)

Observed record dispatch counts:1=1623,2=147,3=373,31=147. Read dispatch table141958b78 (stride16). Category1→1414cc610,2→1414cc9c0,3→1414cc730. Initially functions missing; created these three functions through MCP and saved project. They jump via signed runtime selector at record+8:category1base141943ef8,category2base14193f728,category3base141958c78,eachstride16. Category31 is terminal recognized by caller before dispatch; its selector bytes are not opcode indices.
Read observed source selectors:category1 selector33→1414c3360,34→1414c4780,40→1414c30a0. Naive category3 source6000/8061/12103 lookup returns null;category2source2054 yields1417140e8 whose code/data role is unresolved. Therefore source selector cannot yet be assumed identical to post-load runtime selector for every category. Need inspect loader relocation/postprocessing before decoding source semantic handlers. Do not execute null table targets or mark VM recovered.
Evidence script-dispatch-table/category1-3/selector-* and script-dispatch-save under reports/ghidra/raw. No VM emulator or gameplay parity yet. Next category1 concrete handlers and relocation of category2/3 records. Existing23tests unchanged.

## 2026-10-08 — arithmetic handlers and selector remapping tables (4.2)

Decompiled category1 handlers:selector33→1414c3360 subtraction,34→1414c4780 addition,40→1414c30a0 bitwise OR. Stack tags1/2 distinguish integer/float paths; decompiler casts lose bit reinterpretation, so no arithmetic emulator parity claimed. Evidence vm-address JSONs.
140b43db0 only expands serialized event records; no relocation in that reader. Found140b28fa0 initialization maps source IDs to indices via DAT1420ca0e0, enumerating category table74entries, category2table1149entries, category3table27entries. Read category3 IDs512..564 and full category2 table in4096-byte MCP chunks (memory limit4096).
Source records dispatch3 with selectors6000/8061/12103 match IDs in category2 table:runtime indices16/212/679, pointers1414ceaa0/140b47770/1414a73a0. Thus source dispatch byte is ALSO not yet equivalent to runtime category; loader/postprocessing must map both fields. Source dispatch2selector2054 absent in this table; unresolved. Mapping saved stage4-sally-vm-selector-mapping.json. Do not execute source records directly against runtime dispatch tables.
Next inspect relocation references to DAT1420ca0e0 and handlers1414ceaa0/140b47770/1414a73a0; preserve unresolved literal/terminator records. Existing23tests unchanged, no VM gameplay effects reproduced.

## 2026-10-08 — CORRECTION: source categories and event ID linking (4.2)

140b44150 confirms remapping selector AND dispatch fields through140b28fa0 global map. Previous direct source category1 selectors33/34/40 interpreted as subtract/add/OR was WRONG: those runtime-index handlers exist, but sourcecategory1 is literal category→runtime0;selectors33/34 are type IDs→runtime1/2. Sourcecategory2→runtime1 operators;source2054→runtimeindex6. Sourcecategory3→runtime2 functioncalls;6000→16,8061→212,12103→679. Source31 terminal is recognized before linking; ignore arbitrary selector bytes. This correction supersedes earlier semantic assignments and direct table address claims.
Added jade_vm_link.py and export_sally_linked_events.py reproducing verified table order (category16/type28/operator74/function1149/native27). New report stage4-sally-linked-events.json2290records:1879ID-linked,147terminal,264literal references unresolved140b40280 for selectors27/28/2A/2B. No VM execution or pointer fabrication.24tests pass including source/runtime category mismatch regression. Ghidra project saved after3additionalhandler functions created.
Handlers read:6000→1414ceaa0 pops3numeric stack items and pushes tag3float3 (one protected constant still unresolved);8061→140b47770 queues up to5entries of64bytes containing actor and stack vectors, subsystem role unproven;12103→1414a73a0 takes4arguments/calls1566a0f90 and pushes integer result. Do not assign gameplay/audio/FX meaning before following callees. Next literal reference resolver140b40280, true operator2054handler1414c3a80, literal handler1414cc790 and protected constants/call targets.

## 2026-10-08 — null references and context operator (4.2)

All264previous unresolved reference literals are sourcecategory1/selector40/value0. Native140b40280 returns0 immediately; selector28(hex) also preserves sentinels1/2. jade_vm_link now resolves only these verified cases, leaves arbitrary nonzero keys dependent on native remap/resource tables. Re-export stage4-sally-linked-events.json:2143linked +147terminal, no unresolved fields in observed set. This is complete ID/reference preprocessing coverage, NOT VM execution.
Read140aeac00 sorted key/value lookup;140b40280 performs first ID mapping then bucket lookup(index lowbyte(key+key>>8))*24; dynamic tables/context still needed for general nonzero refs. Source2054 operator→1414c3a80 pops one stack value, sets DAT1420d6618 script object context and DAT1420c3488 related component; special DAT1419a1428 sentinel branch sets context0. It is not arithmetic. Literal1414cc790→1400bf1f0 pushes converted value/type onto32-byte value stack +16-byte descriptor stack. Type6 conversion1411dbaa0 copies null unchanged;sentinel1/2 fetch context pointers through PTR_DAT14193f710. Created missing operator6/type6 functions and saved Ghidra.
25tests pass incl null/sentinel resolution and unknown-key rejection. Next implement explicit typed stack/literal and context state, follow effect queue8061 and call12103; event waiting/side effects still unimplemented.

## 2026-10-08 — bounded typed VM prefixes (4.2)

Read scalar literal converter1411dbb20:32-bit copy, no numeric conversion. Added jade_vm_state.py explicit typed stack for runtime literal types1integer/2float-bit-pattern/6reference; sentinel1/2 require supplied runtime references. Operator1:6 sets object/component context using supplied object snapshot/sentinel; unsupported calls fail before mutation. Native untyped reinterpretation outside supported reference context intentionally rejected.
probe_sally_vm_prefixes.py report stage4-sally-vm-prefixes.json evaluates fresh event stacks under explicitly chosen sentinel0/no objects:147nonempty event payloads,979prefix records executed,0events reach terminal. Stops113at2:16(vector construction),5at2:248,5at2:614,24at2:679. Of150kind40keys,3have no record payload and are not executed here. No whole-event execution, wait/timing or side effects claimed.
26tests pass including float bit preservation, null context update, terminal, and unsupported-call stack preservation. Next vector constructor2:16 protected type constant and handlers2:248/614/679, then complete event prefix execution; game effects still pending.

## 2026-10-08 — scalar vector constructor and remaining calls (4.2)

Implemented runtime2:16/source6000 float3 constructor1414ceaa0 for scalar tags1/2 only, preserves X/Y/Z stack order and rounds integer conversion to float32. Protected third type-check constant:PEbytes4883ec08 at151c405d6 xor08ec834a=2; confirmed instead of guessing. Underflow/unsupported converters fail before mutation.
Prefix report updated147events/1996executed records/0terminals. Stops109at2:212,4at2:207,5at2:248,5at2:614,24at2:679.27tests pass after updating earlier unsupported-handler regression to an actually unsupported ID; vector order/mixed types/underflow tested.
New decoded handlers:source8133/runtime248→140b39180 pops clear-mask then set-mask and updates actor component ushort+50 as(old&~clear)|set; context side effects need explicit runtime object. source12022/runtime614→1414a46d0 calls15666c230 with object,id,float and pushes integer. source12103/runtime679→1414a73a0 calls1566a0f90, whose body calls15666c230, checks resulting resource index/flag400, uses float argument and count to call154f89f00. Subsystem meaning not established. Created missing248/614functions and saved Ghidra. Next inspect15666c230/154f89f00 and remaining207/212queue consumers before faithful side-effect emulation.

## 2026-10-08 — object mask side effect and resource instance call chain (4.2)

Implemented runtime2:248/source8133 component ushort+50 update using explicit object snapshot:consume setmask then clearmask, oldflags&~clear|set, restore default actor/component context. Integer mask branch only; float conversion14078b830 unresolved.28tests pass including exact masks/old context/default restoration. Prefix coverage remains1996records/0terminal events because5mask events lack actual component snapshot; stop reason now accurately identifies missing runtime flags.
Read15666c230:subsystem enable14195af34 gate, calls156670320(actor,id,18000080), conditional scalar154f63710, activates154fa0fd0.156670320 creates/finds instance through140afa260 and140afab90, attaches actor matrix/position pointers to instance+58/+60.154f63710 clamps parameter to0..1 and stores+18 then update140aff0e0.154fa0fd0 queries interface+70, sets activation flags then invokes140af8a30.679wrapper1566a0f90 additionally computes integer parameter fromfloat andinstance+14 then154f89f00 calls interface+60. Resource strideC0 andflag400 observed; audio/FX/gameplay subsystem identity still unproven. No fake instance indices or activation success used.
Next inspect140afa260/140afab90/140af8a30 and queue207/212 to establish resource class; actual runtime snapshots required for faithful side effects. Evidence vm-subsystem-* JSON. No full event/Bevy playback parity.

## 2026-10-08 — actor resource indirection and bounded component queue (4.2)

140afa260 ordinary actor path requires actorflag08000000, component+48 resource map, valid local index, then resolves global resource index; template strideB0 and instance strideC0 are different pools. Added jade_resource_instance.select_actor_resource with explicit snapshot and enabled gate;clamp_instance_parameter mirrors154f63710 native epsilon0branch/min1.29tests pass. This does not create/backend-play resource instances.
Created/decompiled missing handler207/source8056→140b47500 and saved Ghidra.207usespreviousscriptcontextobject,212/source8061usesDAT14210c108object. Both find component+28/+28 queue, record64bytes, limit5entries,count+140.207consumes4stackitems;212consumes3pluscurrentactor. Scalar/vector args and extra helper-derived fields preserved in decompile; protected offsets need assembly/static constant validation before queue emulator. Purpose unresolved; no sound/FX naming assumed.
Resource allocation routes through load branches1550c3bd0/1550cd6f0,140b050f0/140b04ff0,154d5fbd0 or1552fc720 based on template flags. Activation140af8a30 interfaces and defaulttable1420c2860 need tracing to backend before subsystem identity. Prefix execution still1996records and0full events; no fake side effects. Next queue consumer and resource loader/backend metadata.

## 2026-10-08 — audio subsystem identified as Wwise (4.2)

Read140af9430 initializes Windows backend table1420c2180 (tag77696e20), assigning init140b08700 and query140b08db0, plus stream-derived backend tables.140b08700 calls imported AK::MemoryMgr,AK::StreamMgr,AK::SoundEngine andAK::MusicEngine APIs; loads CommonBank.bnk and registers game objects200 Listener/199 Static Wwise Game Object.140b08db0 queries GetPlayingIDsFromGameObject. These direct imports/string references CONFIRM audio/Wwise identity of resource subsystem previously unnamed. Exact Wwise version not established.
Windows loadcallback1420c2210→140b09930 is RET/no-op, confirmed after creating function; do not interpret legacyload path as actual media decoding. Interface1420c2860 static PEbytes allzero, runtime140af9430 assignment required; no null-table execution. Saved Ghidra. Existing resource logic and VM tests unchanged29passfrompriorpass.
Read-only rg of installation for loose .bnk/.wem/.pck returned none; audio data likely container-backed but location NOT established. No audio files extracted/converted yet. Queue207/212 subsystem still unclassified; audio identification does not automatically identify that separate component queue.
Next trace Wwise file-location resolver/bank IO to package assets, resource614/679 audio ID mapping and queue207/212 consumer. Need meaningful audio behavior before VM playback parity.

## 2026-10-08 — container-backed Wwise banks found (4.2)

Added probe_wwise_banks.py read-only named BPAK resource inventory, bounded bank chunk parsing (tag4+size32, exact EOF, BKHD version/bankID). Ran with approved access to game archives and project LZ4 dependency after sandbox import failure. Report stage4-wwise-bank-inventory.json:7763named .bnk/.wem/.pck resources,8banks Init/CommonBank and DE/US/ES/FR/IT/NL language banks. Banks located through archive entries, no loose-file assumption. All bank chunks valid; no media exported/decoded yet. BKHD version is bank format, not automatically precise Wwise software release.
MCP IO vtable141738540 includes140b0a9c0open candidate,140b0a9f0read→140ae4d20; decompileopen currently single instruction/no function boundary, needs function creation before interpreting path resolver. Evidence wwise-io-vtable and wwise-io-address JSONs. Next bank HIRC event/media linkage, RIFF/WEM codecs and extraction into typed audio assets; queue207/212 role still unknown. Existing29tests unchanged.


### 4.2 — извлечение исходного аудио Wwise

`tools/jade/export_wwise_audio_sources.py` извлёк 7763 файла (8 банков BNK и 7755 потоков WEM), 2972657023 байта, в `assets/audio/wwise-source/<archive>/banks|streamed/`. Манифест `reports/jade/stage4-wwise-audio-source-export.json` содержит исходный архив, имя, размер, SHA256 и формат каждого потока. Для 8952 встроенных записей банков проверены границы DIDX/DATA и записаны смещения, размеры и SHA256; сами записи пока остаются внутри банков.

Проверка: все 7763 выходных пути уникальны, файлы существуют и размеры совпадают с манифестом. Все потоковые WEM имеют RIFF fmt codec tag 0xFFFF; конкретный кодек ещё не подтверждён. 7071 моно и 684 стерео. Экспорт сохраняет исходное кодирование, не является WAV/FLAC и пока не подключён к Bevy или основному catalog.json. Следующий шаг: определить расширение fmt и декодер, проверить преобразование небольшого набора в редактируемый формат, затем восстановить HIRC event/media связи. Очереди VM 207/212 по-прежнему не классифицированы.


### 4.2 — проверка декодирования Wwise Custom Vorbis

Официальный vgmstream r2117 win64 установлен локально в tools/audio/vgmstream; источник и SHA256 архива сохранены в PROVENANCE.json, лицензия сохранена. Первый WEM и 16 представителей всех сочетаний частоты/каналов успешно декодированы. tools/jade/decode_wwise_probes.py выбирает самый маленький поток каждого сочетания и конвертирует с -i (без циклических повторов). Выход: assets/audio/decoded-probes/<archive>/<media-id>.wav, 9020110 байт. reports/jade/stage4-wwise-decoded-probes.json хранит метаданные декодера, исходный и выходной SHA256. Проверены частота, каналы, длина PCM и совпадение числа сэмплов WAV с декодером во всех 16 случаях. Кодек подтверждён как Custom Vorbis на этих примерах; массовая конвертация 7755 потоков ещё не выполнена, встроенные медиа не декодированы. Прослушивание, HIRC event mapping, loop semantics и Bevy playback остаются неподтверждёнными. Далее: встроенные записи/prefetch и связи HIRC, затем масштабирование экспорта.


### 4.2 — полные встроенные медиа и потоковые префиксы

probe_wwise_bank_structure.py проверил framing HIRC всех 8 банков: 45606 объектов, точное достижение конца каждой секции. Проверки reader на усечённые заголовки/недопустимые размеры/хвосты прошли. Типовые payload сохранены без интерпретации в stage4-wwise-bank-structure.json. Из 8952 DIDX-записей 1197 имеют полную RIFF-длину, а 7755 — префиксы; каждый префикс побайтово совпадает с началом внешнего WEM того же media ID (кандидаты из всех архивов проверены, совпавшие пути сохранены). Префиксы не следует декодировать вместо полного потока.

export_wwise_embedded.py сохранил 1197 полных WEM, 14429367 байт, в assets/audio/wwise-source/<archive>/embedded/<bank>/<media-id>.wem с проверкой SHA256 по исходным банковым сегментам. Полные записи найдены в CommonBank; один минимальный пример успешно преобразован vgmstream в PCM WAV с проверкой длины и числа сэмплов. Отчёт stage4-wwise-embedded-export.json. Всего теперь 8952 полных медиа-файла (7755 внешних+1197 встроенных), без учёта банков; массовая PCM-конвертация ещё не выполнена. HIRC type-specific поля и связи event/action/sound, роли музыки/голоса/SFX, playback/loop parity остаются задачей следующего прохода.


### 4.2 — числовые связи событий Wwise v140

probe_wwise_event_links.py реализует ограниченный reader: event count как big-group base128 varint и action IDs; action prefix ushort type/uint target/byte bus; sound prefix plugin/stream/source/in-memory-size/sourcebits. Формат сверён с первичными исходниками wwiser wparser.py/wmodel.py/wdefs.py (ссылки в отчёте). Хвосты действий и звуков сохранены без интерпретации.

stage4-wwise-event-links.json: 17840 event objects,17997 actions,8828 sounds по всем банковым вариантам (не уникальные игровые события, локализованные варианты повторяются). Все 17997 event→action ссылок разрешаются внутри своего банка в объекты типа3. Все 8963 Play-действия имеют target в банке,8826 ведут непосредственно к Sound; остальные137 требуют container/music parsing. Все8828 sound source IDs найдены в DIDX своего банка. Тесты count0/1/128,усечённого varint/списка/хвоста прошли. Пока не восстановлены action properties/delay/fades,музыкальные playlist/container маршруты,языковой выбор,имена событий и привязка вызовов Jade VM к Wwise IDs. Далее: полный путь событий через контейнеры и сопоставление с native вызовами; PCM mass export ещё pending.


### 4.2 — маршруты контейнеров Wwise

Официальный wwiser snapshot v20260808 сохранён в tools/audio/wwiser с SHA256 архива и provenance (master snapshot, не pinned commit). probe_wwise_container_routes.py разбирает все8банков в XML stage4-wwise-full-<bank>.xml. Далее извлекает строго именованные Children/ulChildID и sourceID; не ищет случайные совпадения DWORD.

Все137 непрямых Play целей:105type13 Music Playlist Container,30type10 Music Segment,2type9 Layer Container по вариантам банков. Получены157 путей к source-ID наборам, без missing/cycle/empty leaf. Отчёт stage4-wwise-container-routes.json хранит граф, пути, sourceIDs, parser logs/XMLhash. Это кандидаты медиа, не фактический выбранный playback: switch/state/RTPC, playlist ordering/weights, track clips/timing, fades/transitions не исполняются. Поля остаются в XML для дальнейшего переноса. Далее: выбрать конкретную музыкальную цепочку и восстановить clips/playlist/transition условия, сопоставить Jade event IDs. Массовый PCM export и Bevy audio pending.


### 4.2 — visual variants, influences и НЕпройденная проверка skinning

По1409ea250 флаг23 использует action_words[0] как descriptor для1409ed490/153d51380, не добавляет новый блок. Убрана ошибочная блокировка в probe_character_resources. Семь variant descriptors ведут к29GAO-вариантам; экспортированы26type1mesh в models/meshes/sally-*.json,50materials и26PNGtextures без неподдержанных зависимостей. Extended header теперь сохраняет index16,matrix68,words32; legacy normal fields сохранены.27GAO skin-entry tables экспортированы в skeletons/sally/visual-skin-bindings.json. Native1409c1480 копирует таблицу варианта и перебиндивает actor/index.

Подтверждено140a2fce0→140a43a00→140a41940→140a41f90: low16 DWORD=vertex index, весь DWORD=float32 weight одновременно. jade_skin.py реализует8flags modes иfloat32 accumulation без нормализации;4skin tests+29animation tests pass. Порядок source records сохранён: loader1542eec90 разворачивает pointer array, consumer разворачивает снова. Native140ae9420 подтверждает composition=param3*param2. Runtime skin matrix branch включает owner-relative conversion и type18modifiers1409ddef0; их применение ещё не восстановлено.

Сцена sally-skin-diagnostic:7частей,12batches,19910triangles, явный variant1/pose7100B0E7. Bevy3tests/build/captureexit0. Первыйкадр132548 пустой из-за hardcoded hangar camera. Добавлено optionalpreview_camera в scene schema, title/UI используют scene.name; Home сбрасывает scene camera distance. Исправленныйкадр132736 показывает НЕкорректную деформацию тела. Animated GAOworld→actor skin-array mapping остаётся неподтверждённым; НЕ готовая модель/не parity. Сериализованная actor47matrixarray заполнена нулями flags0 (native identity fastpaths имеют значение); forced-general diagnostic на ней также неверен, кадр133019. Не считать эти эксперименты finished character asset. Source skin experiment и animated reports разделены.

Evidence: stage4-sally-visual-variants-probe,variant-geometry,variant-dependencies,source-skin-matrices,skinned-preview reports; Ghidra visual-selection/mesh-constructor/geometry-dispatch-init/mesh-deformation/skin-vertex-apply/skin-compose-order/skin-modifier-binding/skin-matrix-modifier/skin-modifier-writer. Последний по имени animation-to-skin-matrices содержит140b29720 AI callbacks, а не writer skin matrices. Следующее: native actor matrix-array writer/owner-relative pipeline иmodifier association; получить корректный meshpose и проверить его визуально.4.2ОСТАЁТСЯОТКРЫТОЙ, не закрывать по числу экспортов.


## 2026-10-08 — 4.2: доказанный комплект Sally и живая палитра

Критерий 4.2 «один доказанный комплект персонажа» выполнен. Это не завершение стадии 4 или полной игры.
`assets/models/characters/sally/manifest.json`: 323 файла с путями/SHA256, 26 meshes, 50 materials,
26 textures, 214 animation channel resources, skeleton bindings и статический OBJ/MTL.
Актёр 71003F5A, indexed list7100AF2A, 47 slots подтверждены native цепочкой и живым процессом.

Исправлена ошибка экспортера: affine_product(local,parent) ранее вызывался в обратном порядке.
Native140a43a00 требует bone*bind; compose_skin_matrix теперь соблюдает порядок и flags0/2/4/6,
scale8 явно запрещён. Регрессия проверяется noncommuting rotation/translation тестом.
Всего 7 skin tests и 3 Bevy tests проходят. После исправления растяжения модели исчезли.

Native1409ce4e0 вызывает1409ce210 по indexed order и записывает actor-relative palette.
1409ce210: direct actor child копирует local; внутренний parent берёт уже вычисленный slot,
compose/140aed9a0 orthonormalize/restore scale; detached fallback inverse(actor)*world.
140aed9a0 нормализует X, Y=Z cross X, Z=X cross Y. Эта полная рекурсивная реализация пока не перенесена.

Read-only runtime snapshot reports/jade/stage4-sally-runtime-20261008-142531.json:
47 palette matrices flags6. Соотношение palette=inverse(actor)*objectWorld проверено на47slots:
maxabs3.901337095157942e-6; снимок несинхронизирован с одним остановленным кадром.
Фактические варианты slots0/9/14/18/20/37 =1/1/2/2/1/1;slot21=FD hidden.
Native/source vertices:1852/1588,4492/4492,519/422,519/422,2047/2047,1583/1306.
Во всех6 мешах наборы уникальных float3 координат совпали ТОЧНО; native делает reorder/duplicates.
Prefix comparison здесь ошибочно выглядит как несовпадение — использовать coordinate-set evidence.
Topology, UV duplication и финальный native deformed vertex buffer пока не сверены.

assets/scenes/sally-runtime-skin/scene.json:6parts10batches19406triangles, живая палитра + offline geometry.
Проверенный Bevy capture reports/bevy/captures/sally/bevy-20261008-142417.png показывает целую Sally
с правой рукой на бедре. OBJ — зафиксированная поза, НЕ автономное проигрывание анимации.
Original GPU capture original-sally-safe_small.png чёрный сFPS, визуальное frame/pixel parity НЕ доказано.
Снимки старого ошибочного skinning сохранены как история, больше не являются текущим состоянием.

UM game-automation FFmpeg установлен внутри tools/game-automation/universal-modder,
SHA2563601e9ce9f1f7aad2333427a6645271a09e4e52d231e75afcd4ad42fdfe7e425.
Для UM использовать process-local LOCALAPPDATA=<project>/tools/game-automation.
Original bge.exe PID36912/ASLR base получать заново. Пользователь взял управление кнопками на себя;
не отправлять клавиши/клики без нового согласования. Read-only snapshots согласованы.

Следующий подэтап4.3: native phase/weight/time и один воспроизводимый переход анимации.
Control VM, modifiers, topology/render buffers и shader parity остаются явными открытыми задачами.


### 2026-10-08 — reference refresh and tracking input qualification
Refreshed Ghidra MCP1409c0850 (stage43-reference-refresh-evaluator.json) confirms final reference = saved actor * inverse temporary evaluated root. Implemented restricted no-scale refresh_reference in jade_actor_reference;4tests pass including rotated actor multiplication order and scaled-input rejection.
New probe_reference_refresh.py on165629:197qualified identity-root cases,197/197basis EXACT,197/197position within1e-5,max1.9073486328125e-6;4cases skipped. This is conditional on current captured actor world, not proof of refresh-time saved input. Does not solve residual slot0/body conversion or prove complete pose.
Tracking audit previously counted only field presence. It now checks reference/globals/role consistency on BOTH adjacent samples.3audit tests pass. Of145adjacent candidates,141have stable captured inputs;4reject changed actor reference. All retain callback_input_proven=False. Report overwritten165629-tracking-input-audit.json and new165629-reference-refresh.json saved. Next establish callback prior-world provenance before conditional tracking replay; no new game recording required for current static work.


### 2026-10-08 — linked-world scheduling and stored-world diagnostic
Refreshed MCP1409ac510 saved stage43-linked-world-pass-evaluator.json. Implemented restricted jade_linked_world_pass with explicit visitation byte+33/list order/pass parity, parent-first traversal, native entry retry, marker lower-bit preservation, counter wrap and cycle rejection.4tests pass; existing tracking-local4tests pass. It models a specific world pass, not intervening callbacks or the entire manager update.
Sequence collector prepared object update_flags+8 and visitation_byte+33 plus before/after object-prefix checks. Syntax checked, NOT live-run. Actual manager traversal list/parity still unavailable; do not substitute indexed skeleton list as native manager list.
Saved probe_stored_world_consistency on165629:9447comparisons,9246basis matches,9243positions within1e-5. All201basis failures are slot28 (max1.8022);position failures slot28(201) and27(3),max.116258. Slots9/10/20 do not fail this SAME-final-local hierarchy comparison. Thus these readings do NOT prove stale tracking worlds; slot28 discrepancy may involve unmodeled update/list behavior, callback writes or publication. No prior callback input/full hierarchy parity claim. Report stored-world-consistency.json lists failure slots. Next investigate slot28 special update/publication and callback ordering using static evidence before requesting further live capture.


### 2026-10-08 — slot28 modifier0x18, live state now required
Bounded source GAOs620007A8(slot27)/620007AA(slot28),SHA256 retained, contain one modifier type0x18(decimal24) with outer flags01000000, payloadversion3, damping.9, modeflags0180/040A. Original names b_sal_PLUG_meche1.gao and b_sal_PLUG_meche2.gao suggest hair accessories; this name-based attribution is an inference.
MCP factory153464450 selects table1419a14a0+type*38; initializer1409b05fe assigns type24 callbacks: constructor1409de5b0->153cada40, pre-palette prepare1409ddef0, apply1409de5a0, reader1409de3b0->153ca5d50. Created functions at the observed jump destinations to recover reader/constructor; Ghidra project saved. State allocation100bytes; native1409dcba0 uses persistent basis+58/position+88 and damping, linked constraints and orientation correction. This is a stateful modifier, not ordinary skeletal composition. Exact cause of observed slot28 mismatch still requires its live state; no causal parity claim.
Added jade_modifier24 source record decoder/encoder, bounded state capture, end-window consistency checks, repeated-f32 damping coefficient with native timestep14173c234=0e745a3b.4tests pass. Two source records byte-exact roundtrip and exported assets/modifiers/sally/slot27-620007A8.json andslot28-620007AA.json. probe_character_resources now preserves bounded unparsed tail+offset, rather than pretending it is parsed.
Full and temporal collectors now capture slot27/28 type24 state256bytes and headers with checks. Syntax passed, NOT live-run. New probe_modifier24_state compares observed persistent state to published world only; dynamics/previous state/callback count remain unproven. Existing165629 lacks these fields so cannot validate this branch. Next REQUIRED user: exit automatic menu into loaded Sally scene, stationary5seconds, reply ready; perform approved readonly full capture, run modifier state/palette/clip probes, then determine whether movement trace is necessary. No keys/menus automated.


### 2026-10-08 — modifier lifecycle explains slot28 hierarchy disagreement
Readonly full172956:component/bothclip state/header/updatepass checks stable; modifier state checks stable; actor*palette47/47 EXACT. Source clip2600313F idle. Slot28 state position versus world within7.6294e-6. Initial direct state+58 basis comparison FAILED1.0681 because linked8 suppresses ordinary rotation2 in1409dcba0; corrected probe retains this as abandoned invalid assumption, no hidden tolerance increase.
Recovered no-scale modifier24_step: f32 repeated damping, linked position bounds, preserved parent distance, quaternion from nominal/lagged direction, optional ordinary orientation smoothing.9tests passed,10after lifecycle added. lag_pose_from_position alone loses precision from rounded final position:173533 only58/193basiswithin1e-5,max4.3303e-5; it is diagnostic, not exact replay.
Readonly sequence173533:256samples3.4508s,219poses,actor position stationary,193motionqualified,passdelta207. Ordinary3474rotations/3474positions match(max6.91e-8/3.73e-9);3281non-slot0 positions EXACT;193slot0reference positions EXACT. Slot28state positions193/193within1e-5;source roles27/28 capturedstable.
Conditional adjacent-pass modifier replay:140pairs,139statepositions EXACT and139publishedbasis within2.3842e-7. One failure62->63 has native processed marker10000000 set; positionmax.00016975,basis.00246674 preserved in report. Marker-clear subset139/139. Adjacent reads are STILL not proven callback inputs.
MCP142137198xref->1409ddda0 proves finalizer clears processed bit, restores original linked LOCAL from saved state+0c and original params, but retains lag-state/world/palette. Thus published slot28 world intentionally differs from hierarchy built from final RESTORED locals. Implemented prepare/finalize one-node lifecycle, not inferred global-list membership;10tests pass. Saved-local check385/386matches;the1exception is in processed-marker state. This settles the structural local/world discrepancy for this recorded branch, not complete dynamics/parity.
Next static+conditional tracking replay on173533 using source ordinary locals and explicit prior-world candidates. Continuity node fromwriter indexed firstentry=slot0. Overrides apply onlyparameter9 (false on84010000), do not apply capturedzero globals unconditionally. Actorstationarycurrentidle capture reusable; no new game needed now.


### 2026-10-08 — tracking replay and whole-pose read checks
Conditional tracking replay173533:140 adjacent candidate pairs,420 role rotation comparisons,0 within1e-5;maximum0.34353924.420 positions EXACT. This disproves the current conditional scheduling reconstruction, not the recovered source channels. Full failed rows remain in stage43-tracking-sequence-20261008-173533-tracking-replay.json. No tracking/Bevy parity claim.
MCP listing confirms strength computes strength*(delta*multiplier), despite misleading left-associated decompiler text; existing implementation was correct. Secondary pitch listing1409b4468..4480 and48ac..48be confirms rebuilt-current. Parameter8 branch1409b4452..44c2 retains CURRENT role1 yaw, not rebuilt yaw; fixed explicit argument, missing prior input rejected.60 tracking tests pass. Parameter8 is disabled in173533 and this correction does not resolve that record's residual.
Collector now repeats all consumed68-byte actor/world/local matrix reads, reports changed addresses and count. Tracking replay requires both samples to pass this check; older records lack it and must not silently qualify. Equal reads remain non-atomic and do not prove callback-entry inputs.
Readonly175350:256 samples,all256 matrix checks stable,203 observed pass-counter values,only ONE local pose and ONE primary state array.160 candidate pairs all skipped because native phase gate skips tracking writes. This recording provides no active animation/tracking evidence, even though the global manager pass counter advances. User intervention required: exit automatic menu to loaded Sally gameplay, remain stationary, reply ready. Next capture same bounded readonly sequence, inspect phase/pose activity, then conditional replay. Stage4.3 IN PROGRESS.


### 2026-10-08 — active matrix checks and publication order
175535 readonly256samples:207 distinct role20 local poses;206 samples whole-pose matrix checks stable. Conditional primary-only replay56 accepted pairs:168 rotations all fail(max0.47009224),168 positions EXACT.97 candidate-pair skips:77 phase skips,13 active transitions unsupported,7 whole-pose recheck changed/unavailable. The previous scheduling candidate remains disproven even with matrix rechecks.
Added capture_tracking_order.py bounded3seconds/30000 iterations/2048 changed observations, OpenProcess0x1010 only. Tracks slots0/9/10/20 world+local raw68-byte matrices and componentAA..B5. No game input, debug attachment, pause or writes. Uses existing snapshot PID/actor and validates actor/component; matrix/object pointer lifetimes still not atomic.
180020 first publication recording:208 observations,133 matrix-change events over0.814s, mixed separate local/world update patterns.180147 upgraded recording includes current primary header/fullstates before/after/link/component checks:198 observations,186 clip-stable,9 state arrays,37 matrix events(world-only17/local-only19/mixed1);17 events have same checked clip state/header and same pass counter. Confirms multiple observable publication states per pass; DOES NOT identify exact callback-entry world matrices. audit_tracking_order.py preserves event classification in JSON.
Latest180147 all observed componentAF=6,currentphase0: tracking phase is no longer an active eligible branch; next eligible recording needs user exit automatic menu to loaded Sally scene and reply ready. Then fresh full sequence plus bounded publication observer while eligible. Current stage4.3 remains IN PROGRESS; no native tracking or Bevy parity claim.


### 2026-10-08 — observed intermediate source pose and tracking writer replay
180425 active readonly sequence:256 samples;conditional adjacent-final-pose replay453rotations FAIL(max0.44365082),453positions EXACT. This remains invalid as a callback-input reconstruction; no tolerance changed.
Fast180447:396 observations,297 matrix events(146world-only/77local-only/74mixed),135 same checked clip+pass events,70 primary state arrays. New probe_tracking_order_pose.py matches source2600313F against observed locals9/10/20:351/1050 source-local rotations match (125/350slot9,115/350slot10,111/350slot20). Intermediate ordinary animation writes are observable separately from tracking output.
Upgraded capture_tracking_order.py adds slot19 parent and actorworld,actual delta/brain/target-storage reference checks.180728:659 observations. New probe_tracking_order_replay.py uses explicit worlds from the observation preceding all-three-ordinary locals, source channels/current states, then FIRST role0 local write followed by a second observation with IDENTICAL secondary+role0 locals. Selection uses publication bytes only, never best-fitting error. Original first-write-only comparison48:32matches;role0 all16 within6.55e-6,secondary8/16each. Repeated-local qualification48/48within6.55e-6, no skips. This older record still uses conditional phase proxy/global/reference inputs; not causal/bit-exact parity.
Collector now directly observes componentflags/current phaseindex+flags/control,actorflags/reference68bytes/B4height,signaxis/multiplier with end checks. Source clip headers are included so idle clip switching does not require old resource identity.181303current clip was absent from full sequence; probe correctly refused. Its raw recording retained.181411includes current header metadata:839 observations,389events,127samecheckedclip/pass events,96statearrays. Current-phase/reference conditional replay30comparisons:26rotations within1e-5;remaining4role0 max1.475214958e-5;30positions EXACT,phase directly observed for30. Secondary roles1/12 all10each within1e-5. Remaining reference/input-age/native arithmetic errors not settled; do not raise tolerance or claim full pose parity.
MCP1409b4ba0/4baa calls1400369e0 for horizontal projected normalization. Corrected pitch_difference from double hypot/division to rounded-f32 norm/reciprocal/multiply. Regression rounded diagonal [.707106769,.707106769,0] must give zero horizontal pitch; old method created .000345267.61tracking tests pass. Prior181411report preserved as-before-pitch-normalization.json; correction does not resolve the4residual cases.
Current limitations: primary-only self/null target; blocked-target table/resolution and unanimated locals still supplied from full template; pointer lifetimes and native callback-entry state are not fully atomic; host trig; scaled/near-horizontal/transition branches unvalidated. No Bevy tracking integration or game-feel parity achieved.
NEXT requires manual movement: loaded scene, reply ready, then walk and turn for about10seconds after reply. Capture fresh256sequence(startdelay3s) to exercise active transitions/actor reference; no automated game input. Subsequent fast observer if needed. Stage4.3 remains IN PROGRESS.


### 2026-10-08 — resumed: walking and turning sequence182519
User resumed and manually walked/turned without running/jumping. Readonly256samples captured refreshed PID/base.234 role20 poses,225 actor positions,167 whole-pose-matrix stable readings;componentflags0101 throughout. Qualified motion comparison initially161samples, then160 after propagating existing pose_matrices_unchanged guard into shared trace qualification. Earlier report retained as182519-before-matrix-qualification.json.
Source7100B1C3 walking:2880/2880 ordinary rotations within4.5049e-7;2720/2720 non-slot0 positions EXACT. Root actor-reference conversion152/160within1e-5,max1.526623964e-5;8small residuals remain. Restricted root-cancellation diagnostic159/160,max1.14506e-5,not substituted as final implementation. No active dual-slot blend/clip-switch was recorded, so this is not transition evidence.
Added shared optional whole-pose guard: records carrying changed matrices are rejected even when clip/pass markers match; older records still explicitly lack whole-pose checks.5trace qualification tests pass,including unchanged-pass/clip with changed matrix regression. Native reference-point transform140ae9fb0 read through MCP: no-scale basis multiplication, caller separately adds relative translation/B4height; existing implemented sum route confirmed, no speculative root fix.
Adjacent-final-pose tracking381rotationsFAIL(max.45046),381positionsEXACT remains a disproven scheduling candidate and is not accepted as callback oracle. Previously observed intermediate-pose replay and residuals documented above. No tolerance increase.
NEXT required manual input: exit menu; send ready and alternate walking/stopping about once per second for10seconds, with gentle turns, no run/jump. Record same readonly sequence with3second delay to catch start/stop transitions. Without this input, current saved walking trace cannot validate primary+transition blend. Stage4.3 IN PROGRESS; no Bevy integration/fullgame parity claimed.


### 2026-10-08 — start/stop transitions183132 and Rust animation core
User manually alternated walking/stopping about2seconds each, gentle turns, no run/jump.256readonlysamples,193matrix-stable,105actorpositions.207component0101/49component0301.193qualified poses:155primary-only/38dual-slot. Source combinations include7100B5A4+7100B1C3,7100B2E4+7100B0E7,7100B5E3+7100B2E4,7100B1C3+7100B5E3; four transition pairs.
Ordinary2790/2790rotations match(max4.36e-7);mixed684/684rotations match(max4.90e-7).3281/3281non-slot0positions EXACT. Primary root reference153/155within1e-5,max1.5261e-5. Transition-instance reference37/38within1e-5,max1.14809e-5. Shared actor reference duringtransition still11/38only,max1.4542 and remains wrong; do not use it. Eight preaction/source clips observed overall; nofullcharacterparity.
probe_transition_clock.py checks31same-resource/instance qualified adjacent transition pairs:31active flags/31counters EXACT;28active ratios EXACT;3completion events preserve old counter. Uses observed global delta as conditional call-delta input; callback-entry atomicity unproven.
Rust mathematical core added bevy/src/animation/transition.rs andpose_blend.rs, registered module inmain.rs. Transition clock/f32counter semantics, saved-primary position weight direction/clamp; matrix->quaternion fourbranches, native near-identical copy-first, raw rotation weight, native quaternion->matrix operation order. No-scale branch only, host double trig numerical substitute, Jade axes retained. ECS skeletal playback/root reference/tracking wiring NOT implemented yet.
Rust clock fixture31cases actual native counters/weights from183132 with source hash/pair provenance inbevy/tests/fixtures/animation. Private pose fixture684 reconstructed operand pairs versus OBSERVED native locals stored reports/jade/stage43-bevy-local-blend-native.json plusprovenance; generated tools/jade/export_bevy_blend_fixture.py. Rust integration test opt-in ignored by default because private original-game measurements required. Run cargo test --offline -- --include-ignored --nocapture locally:9/9tests pass.684rotation matrices compared:maximum5.9604645e-8;nonroot positions EXACT. Root translation excluded intentionally;tracking9/10/20excluded. Validation summary reports/bevy/stage43-animation-core-validation.json. Viewer behavior remains static; nolaunch claim.
Prepared transition_phase runtime lookup(component98 action table, instance54action/56phase) directly fromnative1409b3b20, bounded counts/missingdescriptor handling.2tests pass. Fullsequence collector now records transitionphaseflags/control and repeat check. NEW fields NOT yet live verified. Needed next loaded start/stop capture to verify tracking eligibility on the SECOND phase before attempting transition tracking replay. Ordinary local blend proof is independent of this missing tracking metadata.
4.3 IN PROGRESS. Next manual samegentle walk/stop -> verify new secondphase fields -> transitiontracking/rootreference residuals -> ECS skeleton integration. No source/game-feel parity and no automatic game input.


### 2026-10-08 — second-phase evidence, Rust channels, corrected tracking target
184552:192 qualified poses (157primary/35blend),45/45 secondary-phase consistency checks. Flags12/44 all allow bit4. Ordinary2826 rotations and blend630 rotations match (max3.99e-7/5.01e-7);3264nonroot positions EXACT. Primary root156/157,transition reference34/35 within1e-5;small residuals remain. Transition clock27/27active+counters EXACT,26ratios EXACT. Tracking phase148/148counter comparisons agree,including28transition pairs;counter evidence does not prove native writer execution or strength.
Rust animation/tracking_phase.rs andchannels.rs now implement phase gating and decoded local rotation/translation sampling. Full cargo test --offline -- --include-ignored:14/14PASS. Private walking fixture2880 rotations matches tolerance1e-5 and nonroot positions EXACT;local blend684 max5.9604645e-8. These modules remain numerical core,not ECS skeletal playback;primary clip advancement/root/tracking/skin integration incomplete.
MCP140e02760 invokes140b33020 for role0 target position. Re-read140b33020 confirms current linked local hierarchy composition,not stale child world position. Corrected both replay probes to use linked_target_position on reconstructed current ordinary nodes. Preserved old reports as180728/181411-before-target-hierarchy.json. Conditional intermediate replay now48/48 and30/30rotations match,max1.6987324e-6/1.5497208e-6;all78positions EXACT. Existing hierarchy tests5PASS. Sequential observations and template inputs still conditional;not callback-entry/full tracking parity. This resolves prior four idle role0 residuals,not independent walking root-reference residuals.
190347fresh sequence:256samples,one actor position,phaseflags8/control32784;203qualified260006DEposes.3654ordinary rotations match,max9.76e-8;3451nonroot positions and203root reference positions EXACT. Fast190431:1189observations but0qualifying ordinary-to-tracking events. Frozen actor/ineligiblephase is not walking tracking validation. Next intervention: active scene and gentle manual walk/stop~2s each for15seconds to obtain qualified active tracking publication boundary. No automatic input. Stage4.3 IN PROGRESS.


### 2026-10-09 — resumed, explicit runtime world hierarchy
Addedhierarchy::compose_tracking_world andworld_pose.rs:bit400000 followslinkedparents independently oftarget-positionbit1;child-to-root accumulationpreservesnativef32association,explicitrootworld,cycles/missing/scaleproductbranchesfail. Outputworldmap doesnotmutate nativegame.
export_bevy_world_fixture.py produced8qualified190347samples/360observedlocal->storedworld comparisons;slots27/28 excludedbyknownmodifier24scope beforecomparison,nofilterbyerror. Rust360comparisons pass1e-5,20/20fullRusttestsPASS. Flagsnotcompared;explicitfinalrecordedlocalsnotordinarysource-onlychannels;nocallbackentry/source->world/renderparityclaim. Knownslot28fullrawhierarchyprobe deviation.06544 independentlyretained,separatemodifierpipeline.
Next explicitpriorlocals+source/runtimeclonemap+rootconversionbeforeconnectingsparseanimatorandworldcomposer/ECSskin. Game notneedednow.4.3INPROGRESS. Pausecheckpoint20261008preservedhistorical.


### 2026-10-09 — explicit actor/root translation core
Addedanimation/actor_reference.rs: no-scale transposeinverse,reference*inverse(actor) relative matrix,nativeXYZsumordering andoptionalB4height;refresh_reference savedactor*inverse(evaluatedroot). Inputs explicit,cannotinferwhich reference/actorpose belongedtonativecallback. Scaleproductbranchesfail.
export_bevy_actor_reference_fixture.py selectedfirst32qualifiedprimaryslot0cases from190347,sourcepositionsfromuniqueclipchannels,observedactor/reference/native localposition;selectionnotbyerror. Rust32/32positions EXACT,rotatedactorrefresh/height/scalerejectiontestPASS. Full22/22RusttestsPASS.
Stationaryprimaryonlyproof;movingrootresiduals~1.5e-5,transitionreferenceselection,inputlifetime androotrotation/referencecompositionremainopen. ModuleisnotyetcoupledtoECSplayback orfull source->worldpipeline. Next explicitpriorlocalstate/runtimeclonemap androotcontexts,preservingmissingchannels beforeworldcomposition. No game needed thisstep.4.3INPROGRESS.
