# Стадии реконструкции Jade на Bevy

Текущий приоритет пользователя (2026-10-09): сначала стабилизировать движение
Jade, выбор анимаций и переходы текущего среза; затем расширять набор подключённых
анимаций (включая idle) и контент. Подробности и backlog камеры — в верхней
контрольной записи о завершении4.3 ниже. Это порядок работы внутри проекта.

Актуальное правило хранения по прямому указанию пользователя: все проектные
файлы находятся в C:/Users/Dan/Desktop/rebge. Assets — assets/; captures —
reports/bevy/captures/; полный вывод анализа — reports/ghidra/raw/;
база Ghidra — ghidra/project/bge.gpr и bge.rep. Прежние указания про внешние
каталоги отменены. Оригинальная установка игры и общие toolchains остаются
на своих местах. Приватные ассеты/база/вывод исключены из Git.

Цель проекта: полная реконструкция игры на Rust/Bevy с доступным исходным кодом всех игровых систем, пригодным для последующей модификации и расширения. Итоговая реализация должна воспроизводить оригинальную Anniversary Edition по всему игровому опыту: управление и game feel, камера, физика, анимации, AI, бой, взаимодействия, задания, интерфейс, звук, визуальное представление, переходы и сохранения. Просмотрщик одной сцены и отдельные эпизоды являются промежуточными результатами, а не сокращением конечного объёма.

Реконструкция означает собственный проверяемый исходный код Bevy; исходные имена, комментарии и структура утраченного кода разработчика не могут считаться восстановленными без доказательств. Требование идентичности — критерий приёмки, а не утверждение о текущей готовности. Для каждой системы фиксируются подтверждённые алгоритмы, параметры, сценарии сравнения и оставшиеся расхождения. Неизвестные механизмы не заменяются приблизительными без явной отметки.

Все ассеты в итоговом проекте должны иметь понятные редактируемые форматы и структуру по назначению (модели, материалы, текстуры, скелеты, анимации, тексты, звук, сцены и игровые данные). Сохраняются связи, единицы, управляющие коды и происхождение; бинарные исходники служат доказательством и основой воспроизводимой конвертации, но сами по себе не считаются завершённым экспортом. Системы Bevy организуются по функциональным каталогам; формат данных и подключение модификаций документируются.

Переход к каждой стадии требует подтверждения пользователя; внутри одобренной стадии агент действует автономно. Стадия 4 одобрена; работа возобновлена по просьбе пользователя 2026-10-09. Необходимые системные разрешения запрашиваются средствами среды.

## 1. Надёжный доступ к ресурсам и локализация
Статус: завершена — 300 пар TXI/TXS экспортированы и прошли побайтовый round trip; детали в MODLOG.md.
Объём: оформить BPAK reader, восстановить 68-байтовые TXI и TXS, проверить все 150 языковых групп EN/RU, создать локальный экспортёр с явным внешним каталогом для извлечённых файлов. Сохранить схемы, неизвестные поля, хеши и воспроизводимые команды. Проверить Rust toolchain без установки на этой стадии.
Критерий: текстовые записи связываются по подтверждённым таблицам; строки и управляющие коды читаются; offsets/counts проверяются; неизвестные поля не теряются. Для сериализатора требуется round trip. Ассеты не попадают в репозиторий.

## 2. Одна сцена Jade: геометрия и зависимости
Статус: статический срез ангара выполнен и просмотрен — SCENE_FORMATS.md. Точность native rendering/visibility, физические единицы и collision behavior ещё не подтверждены; ограничения сохранены для последующих стадий.
Объём: найти scene/object/mesh/material/texture/collision records, восстановить одну сцену и её зависимости; доказать корректность геометрии, осей и масштаба. Создать минимальные конвертеры, если прямое чтение нецелесообразно.
Критерий: одна реальная сцена с оригинальными ресурсами отображается в проверяемом viewer; документированы несопоставленные поля и эффекты. Не принимать произвольную PNG за готовую карту.

## 3. Первый запускаемый срез Bevy
Статус: завершена — Bevy 0.19.1 собран и запущен, кадр ангара проверен визуально; bevy-validation.json и bevy-run.log.
Объём: проверить актуальные официальные Bevy API, установить недостающий Rust toolchain при разрешении среды, создать приложение с доступом к установке игры, сценой, камерой и выбранной локализацией. Запустить и проверить кадр.
Критерий: воспроизводимая сборка и запуск, оригинальная сцена, понятные ошибки отсутствующих данных, записанный screenshot/log. Никаких вымышленных игровых механик под видом восстановленных.

## 4. Управление, коллизии и анимация
Статус: подтверждена пользователем, не завершена. Подстадия4.3 завершена для принятого среза 2026-10-10; 89 private-inclusive tests PASS. Управляемая Jade в ангаре, source playback/skin, старт/остановка, gait transitions и standing/moving turns работают. Точное steering/physics, collision/gravity и native camera constraints остаются отдельными задачами. Текущая контрольная точка — верх HANDOFF.md и CONTEXT.md.
Объём: исследовать игровую логику и skeleton/animation; переносить измеренные правила движения, камеры и столкновений. План динамического oracle согласовать здесь; использовать собственные offline файлы/записи и только допустимые способы наблюдения.
Критерий: один персонаж управляется в одной сцене; поведение сравнивается с исходными данными/трассами, а не с субъективным сходством.

### Подстадии 4 — работа при ограниченном лимите

Каждый проход ограничен одной конкретной задачей; сохранять код, evidence и
точное следующее действие. Одобрение стадии 4 уже получено; новых вопросов
для обычных действий внутри неё не требуется. Число оставшихся токенов
не принимать за измеренный бюджет: 25% — оценка пользователя.

- **4.1. Карта callbacks и компонентов — завершена для выбранного среза.**
  3864 heuristic callback candidates (выбранные таблицы сверены), фильтр ввода, GAO tail, компоненты 4/20, точная граница
  collision tail. Подтверждено: update компонента 20 — no-op; связь с
  анимацией не установлена. Evidence: STAGE4_REVERSE.md и тесты readers.
- **4.2. Персонаж и его ресурсы — завершено по критерию комплекта.**
  Актёр Sally71003F5A и47slots подтверждены native consumers и read-only runtime.
  Комплект323файла:26meshes/50materials/26textures/214animations/skeleton bindings,
  manifest с SHA256, OBJ текущей позы и Bevy scene6parts19406triangles.
  Skinning bone*bind исправлен и проверен7тестами;3Bevy tests проходят.
  Все6 native meshes имеют те же уникальные координаты, что source (reorder/duplicates).
  Palette=inverse(actor)*world проверено47slots,maxerror3.9e-6.
  Это подтверждение происхождения ресурсов и статической позы; автономный playback,
  native modifiers/control VM, topology/UV/shader и frame parity ещё не готовы.
  Дальнейший этап не должен подменять captured palette работающим анимационным runtime.
- **4.3. Воспроизводимые анимационные переходы — завершена для принятого среза, 2026-10-10.**
  Numerical core, pose assembly и ECS playback/skin подключены; 89 private tests PASS.
  Независимые fixtures:31 transition clock cases и684 local pose blends; root/reference
  stages проверяются отдельно. Итоговые native-first live probes: held-R2 start,
  run→walk, reentry gap0.15; основные цепочки совпали после исправления mode2 bins.
  Дополнительная Starting4 удалена только для sprint; same-action phase Bind сохраняет
  активный incoming blend. Startup run timing residual≈3–6ms в двух записях.
  Критерий контрольных source поз/расчёта промежуточной позы и playable переходов выполнен.
  Это не whole-pose/native VM/physics parity и не проверка всех72catalogcases.
  Approximate velocity/steering, procedural coverage и chronology limits сохранены
  в документации реверса; резкая смена угла стика — согласованный backlog. Evidence:
  reports/jade/movement-suite/stage43-final-postfix-paired-audit-20261010.json.
- **4.4. Движение и контакты.**
  Native velocity/gravity/contact solver, форма collider, единицы.
  Критерий: движение, остановка и контакт в одной сцене с указанными
  расхождениями. Не заменять неизвестный solver произвольной физикой.
- **4.5. Игровая камера.**
  Follow target, ограничения, препятствия и сглаживание обычной камеры.
  Критерий: подтверждённые параметры и один воспроизводимый сценарий.
- **4.6. Интеграция и сравнение.**
  Один управляемый персонаж в ангаре, проверки запуска, поз и поведения.
  Для наблюдения оригинала определить конкретный offline сценарий.
  Завершить стадию только после её общего критерия.

## 5. Игровые системы и связанный эпизод
Объём: ввод, interactions, dialogue, AI, combat, objectives, audio и transitions — отдельными проверяемыми срезами. Выбрать конкретный эпизод для интеграции; затем расширять покрытие.
Критерий: согласованный эпизод проходим, зависимости сохраняются, известны расхождения. На этой стадии объём расширения определяется доказанной совместимостью.

## 6. Совместимость и поставка runtime
Объём: карта покрытия ресурсов/сцен/механик, regression сценарии, сохранения и загрузка, производительность, документация запуска на собственной установке, um publish check.
Критерий завершения проекта: покрытие всей игры и её контента, читаемый экспорт всех необходимых типов ассетов и воспроизводимые сравнения поведения и представления с оригиналом без известных существенных расхождений. Пока покрытие неполное, выпуск обозначается промежуточным и сопровождается списком ограничений. Поставка runtime/конвертеров и публикация отдельно по прямому запросу пользователя.

## Правило завершения стадии
Сохранить результат и evidence в MODLOG.md, обновить CONTEXT.md и статус стадии, сообщить достигнутые критерии и остаточные неизвестные, запросить разрешение следующей стадии. Не повторять вопрос для уже одобренных действий.


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


4.3 remains IN PROGRESS: ordinary channels and reference paths checked; procedural tracking and modifier0x18 state must be validated before dynamic Bevy parity. Source modifier parameters are stored under assets/modifiers/sally; next live check requires loaded original scene.

4.3 next: loaded active gameplay readonly matrix-checked sequence -> phase eligibility and callback input provenance -> tracking replay -> dynamic Bevy comparison.175350 frozen-pose recording cannot validate gameplay; needs user exit menu. No full source/game-feel parity yet.

4.3 publication-order observer prepared and verified. Next user loaded eligible scene -> paired full clip/matrix sequence plus fast publication recording -> identify source-write/tracking-write boundaries -> conditional writer replay.180147 phaseAF6 prevents current tracking validation.

4.3 stationary primary tracking: observed intermediate source pose and repeated corrected locals verified conditionally;18141126/30rotations,30/30positions,4role0smallresiduals retained. Next manual walk/turn capture -> transition/reference branch verification -> finish numerical port -> integrate animation/tracking in bevy/src/animation/ with documented limits -> dynamic comparison. Stage not complete.

4.3 resumed walking182519:7100B1C3ordinary2880rot/2720nonrootposmatch;8rootreference residuals. No dual-slot transition in this recording. Next manual repeated walk/stop10s -> transition timing/reference verification -> numerical port/integration.

4.3 start/stop blend numerically verified183132:684mixed matrices;transition clock31cases exact. Mathematical core ported bevy/src/animation/{transition,pose_blend}.rs;9Rust tests pass including private native pose fixture. Next second-phase tracking metadata live check, transition tracking/root references, then ECS skeletal wiring. Not complete or full game parity.

2026-10-08 update:4.3 remains IN PROGRESS. Local channel sampling/transition phase numerical core ported,14Rust tests pass. Next: active tracking publication capture -> transition tracking/root reference residuals -> ECS skeleton/skin wiring. No full-game/game-feel parity.
