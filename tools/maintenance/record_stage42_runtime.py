"""Record latest verified milestone, preserving older investigation history."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
note='''
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
'''
for name in ['MODLOG.md','STAGE4_REVERSE.md']:
 path=root/'docs'/name;path.write_text(path.read_text(encoding='utf-8')+'\n'+note,encoding='utf-8')
path=root/'docs/STAGES.md';text=path.read_text(encoding='utf-8');start=text.index('- **4.2.');end=text.index('- **4.3.',start)
text=text[:start]+'''- **4.2. Персонаж и его ресурсы — завершено по критерию комплекта.**
  Актёр Sally71003F5A и47slots подтверждены native consumers и read-only runtime.
  Комплект323файла:26meshes/50materials/26textures/214animations/skeleton bindings,
  manifest с SHA256, OBJ текущей позы и Bevy scene6parts19406triangles.
  Skinning bone*bind исправлен и проверен7тестами;3Bevy tests проходят.
  Все6 native meshes имеют те же уникальные координаты, что source (reorder/duplicates).
  Palette=inverse(actor)*world проверено47slots,maxerror3.9e-6.
  Это подтверждение происхождения ресурсов и статической позы; автономный playback,
  native modifiers/control VM, topology/UV/shader и frame parity ещё не готовы.
  Дальнейший этап не должен подменять captured palette работающим анимационным runtime.
'''+text[end:];text+='\n'+note;path.write_text(text,encoding='utf-8')
path=root/'docs/CONTEXT.md';text=path.read_text(encoding='utf-8');text=text.replace('Latest4.2 OPEN skincheckFAILED:', 'Historical4.2 previous FAILED check (superseded below):',1)
text=text.replace('## Цель и рабочий порядок','## Цель и рабочий порядок\nLatest4.2 KITCOMPLETE20261008: native47palette captured142531, max inverse(actor)*world error3.9e-6. All6 native/source coordinate sets byte-exact floats (dup/reorder);selected1/1/2/2/1/1,slot21FD. Exporter wrong multiplication FIXED bone*bind,7skin+3Bevy tests passed. Characterkit manifest323files26mesh50materials26textures214animations+bindings, OBJ native-pose;scene sally-runtime-skin6parts19406triangles/capture142417 whole Sally handonhip. OriginalGPUshotBLACK so no pixel/frameparity. Native1409ce4e0→1409ce210 actorrelative palettewriter found,140aed9a0 normalizeX/Y=ZcrossX/Z=XcrossY. Fullwriter NOTyetimplemented. Next4.3 phase/weight/time transition. Usercontrols originalbuttons, doNOTdrive without renewed consent. Readonlycaptureallowed. UM LOCALAPPDATA process-local project/tools/game-automation. Original PID36912/base MUSTrefresh.\n',1);path.write_text(text,encoding='utf-8')
path=root/'docs/ASSET_AND_SYSTEM_LAYOUT.md';path.write_text(path.read_text(encoding='utf-8')+'\nCharacter kit Sally: `assets/models/characters/sally/manifest.json`, `native-pose.obj/.mtl`; source meshes/materials/textures stay in their typed directories. `assets/scenes/sally-runtime-skin/scene.json` is a static runtime-palette snapshot; dynamic animation belongs in a separate Bevy animation system during4.3.\n',encoding='utf-8')
print('Recorded 4.2 kit milestone and outstanding 4.3 work.')
