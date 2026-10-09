# MODLOG — Beyond Good and Evil 20th Anniversary Edition

## 2026-10-10: stage4.3 practical acceptance
- Native-first final probes run_held_start/run_to_walk/reentry_gap_0.15 qualified against existing Ghidra selector/bin/transition mechanisms. Original and postfix preview material action chains agree; run onset residual≈−6/−3ms after mode2 table correction removed extraStarting4.
- New phase bind preserved independent active incoming blend; repeated gait regression jump0.168→0.034 centroid, original thresholds unchanged. Failed88/89 run retained; final89/89PASS and buildPASS in reports/bevy/stage43-run-mode-*.
- Numerical acceptance also supported by31 independent transition clock cases and684 local blend cases; root/reference tests separate. Full native pose/VM/physics parity and all72cases not claimed. Stage4.3 completed for accepted slice; stage4.4 next.
- Evidence reports/jade/movement-suite/stage43-final-postfix-paired-audit-20261010.json and reports/ghidra/raw/agent-stage43-final-three-probe-audit-20261010.md. Failed pre-input foreground-loss capture excluded. Tool Walking phase mapping now uses actual action_phase; old missing phase1 warning was an observer defect. Historical records/checkpoints preserved.

## 2026-10-08: Initial Ghidra MCP read
- Connected to ghidra-mcp 0.9.0 at http://127.0.0.1:8080/mcp using MCP initialize, resources/read and tools/call.
- Project: bge. Open program: bge.exe.
- Executable: E:/SteamLibrary/steamapps/common/Beyond Good and Evil - 20th Anniversary Edition/bge.exe.
- Confirmed: PE, x86-64, little endian, Windows compiler specification; image base 0x140000000.
- Snapshot: 81,877 functions and 100,857 symbols. These counts do not prove analysis completeness or correctness.
- Large executable/read-write .tls$ block: 348,032,000 bytes. Its purpose is not established; do not infer engine or protection from its name alone.
- Initial symbol search for CreateFile, ReadFile, fopen, archive, resource, save and load returned ReadFile in KERNEL32.DLL (symbol ID 64818, EXTERNAL:000000f6).
- Ghidra reports an undefined ReadFile(void) prototype; this is incomplete type information, not the real API signature.
- Saved metadata and MCP schema in ghidra-program-info.json and ghidra-mcp-tools.json; search and function metadata in ghidra-symbol-search.json and ghidra-readfile.json.
- No analysis cancellation, program edits or save operation was requested through MCP. These files are a read snapshot, not a backup of the Ghidra database.

## Next
- Read strings and cross-references around resource paths and file operations.
- Identify one resource loading function, inspect its code, and record evidence before assigning names or types.
- Keep any decompiled source or extracted game assets outside the mod repository. Current files contain metadata only.

## 2026-10-08: Resource loader and BPAK index

### Evidence and functions
- MCP reads use Read-Ghidra.ps1, which initializes the actual server and reads its documented schemas. JSON responses preserve the evidence. This session did not read an auto-analysis progress log; completeness cannot be inferred from function counts.
- 0x141702868: Data/Paks/, referenced at 0x140ae7c15 in FUN_140ae7bd0. That function constructs the directory path and calls FUN_140ae56b0 with callback LAB_140ae53f0.
- FUN_140ae56b0 appends a wildcard, enumerates directory entries, skips dot entries and invokes a callback. API identities are still tentative because the import slots are not correctly resolved by the current listing.
- LAB_140ae53f0 moves callback arguments and jumps to FUN_140ae5410. The latter skips directory entries, creates a 0x88-byte object, constructs a path via FUN_140098d00 and calls FUN_140ae6ad0. On success it inserts the object into a collection at DAT_1421355b8, ordered by the object's first uint32.
- FUN_140ae6ad0 opens the path, reads 24 header bytes, compares the first four bytes with BPAK, reads the end-of-file index and populates an in-memory 0x50-byte entry array and name/key lookup maps. This is the confirmed archive-open/index-reader target.
- 0x1416d62c0: Data/BigDir.jdproj, referenced at 0x14098cacb in startup-related FUN_14098c990.
- FUN_140ad0d50 reads InitialBigFileVersion, UniverseKey and BigDirIgnore through MiniINI-related functions. Version is stored at DAT_14195a9b0; UniverseKey is converted as base-16 and stored at DAT_14195a9b4. UniverseKey is not established to be a cryptographic key.
- Stock BigDir.jdproj states InitialBigFileVersion=37 and UniverseKey=71003ff9. Do not confuse this BigFile version with the BPAK header word at offset 4.
- Embedded source paths identify SDK/Sources/BIGfiles/BIGopen.cpp and BIGread.cpp. This establishes subsystem names, not a definitive engine identification.
- BIG_Read diagnostic string at 0x141702e30 has references in FUN_140ae8440 and at 0x140af7ceb (the latter has not yet been inspected).
- FUN_140ae8440 has a file-seek/read path and an alternate thunk path; dynamic behaviour has not been confirmed.

### BPAK structure verified by read-only parsing
Header: little endian, 24 bytes.
- +0x00: ASCII BPAK.
- +0x04: uint32, semantics unknown (Engine.pak has 0x201, other sampled archives 1).
- +0x08: uint32 copied to object +0x00; used for collection ordering (priority interpretation tentative).
- +0x0c: uint32 converted to a boolean in object +0x08; exact meaning unknown.
- +0x10: uint32 entry count.
- +0x14: uint32 index byte length. Index starts at file_size - index_byte_length.
Index record:
- uint8 kind.
- kind == 0: uint32 byte length followed by that many name bytes.
- kind != 0: uint32 resource key/ID.
- 24 more bytes of metadata, whose field meanings remain unresolved.
In-memory entry stride is 0x50, not the serialized record size. Code adds 24 to a uint64 field at entry +0x40; likely payload addressing, but must trace data consumers before naming it.

Validation: inspect_pak_index.py read all 23 stock .pak files. Every table parsed for the declared count and consumed exactly its declared index length, with no exceptions. Resources.pak has 235378 entries; Engine.pak 5; Shaders.pak 12829. Full results: pak-index-validation.json. No payload was extracted or rewritten.

### Remaining work
- Trace the 24-byte metadata consumers to determine offsets, packed/unpacked sizes and compression.
- Inspect FUN_140af7ceb and the alternate BIG_Read branch; distinguish BPAK access from legacy BigFile logic.
- Cross-check community format documentation before building a full decoder/writer.
- Confirm file API identities and runtime behaviour. All current semantic conclusions are static.
- No proxy DLL, hooks, debugger attachment or game-directory modifications were performed.
- Decompiled code responses are retained in the system temporary directory (rebge-*.json), outside this workspace. Workspace JSON contains metadata, strings and short assembly references only.

## 2026-10-08: Jade context and OLD_TEST tools
- User identified the engine as Jade and supplied OLD_TEST as community reference material for the original game. This updates the earlier unresolved engine classification; the exact Anniversary revision remains unknown.
- Applied universal-modder reverse-engineering, game-research-websearch and share-field-notes instructions. `um kb search Jade` and `um kb search Beyond Good` found no matching notes after syncing the knowledge base.
- OLD_TEST/bgaetool/bgaetool.c is CTPAX-X Team BIN tool v1.2 (2023-07-28). It expects a uint32 container length followed by blocks with uint32 unpacked/packed lengths, uses LZO1X, and writes numbered files. It contains no BPAK reader. Source includes minilzo.h/minilzo.c, which are absent from the supplied directory, so it is not self-contained for recompilation.
- OLD_TEST/jade_studio/JadeStudio.Core.dll was examined as bytes without loading or executing it. Strings identify .NET Framework 4.5, Bigfile/Map/Text/Texture classes and MiniLZO. Exact local binary equivalence to upstream has not been verified.
- Upstream JadeStudio README explicitly reports testing on the original GOG version, extracting/rebuilding sally_clean.bf and partial legacy texture/text support. Do not assume the installed DLL parses Anniversary assets.
  Source: https://github.com/4g3v/JadeStudio
- Anniversary-specific BGEModTools exists. Its README reports extraction; editing/reinjection remains TODO. Its Program.cs reads BPAK records as unpacked uint32, packed uint32, unknown uint64, relative offset uint64; it adds 24 to the offset, uses raw bytes when packed size is zero, otherwise LZ4Codec.Decode. This matches the index topology recovered from FUN_140ae6ad0; LZ4 runtime identity still needs direct game-code or payload confirmation.
  Sources: https://github.com/nillvy/BGEModTools
  https://github.com/nillvy/BGEModTools/blob/main/Program.cs
  https://github.com/nillvy/BGEModTools/blob/main/PakFile.cs
- Updated inspect_pak_index.py to interpret metadata by the community layout and check all payload ranges before the EOF index. All 23 archives have zero out-of-range entries and exact table consumption. This supports field semantics; it does not prove successful LZ4 decoding.
- Main difference: original outer BIG/.bf container and BIN block compression are not the Anniversary BPAK container. Legacy internal structures may remain useful, but each resource class must be compared after BPAK decoding. LZO support in old tools is not evidence that BPAK uses LZO.
- No OLD_TEST executable was launched; no external tool installed or game file modified.
- Research queries: bgaetool BPAK Beyond Good Evil anniversary github; JadeStudio BIG github Jade engine; exact JadeStudio github. A forum result linked a QuickBMS BPAK script, but fetching its primary source failed, so its contents were not used. JadeStudio issues fetch also failed. BGEModTools repo showed zero issues; compatibility with this exact installed build remains unconfirmed.
- Next: verify a small BPAK payload using LZ4; compare resource keys and decoded text/texture structures against legacy schemas. Use OLD_TEST as evidence for inner formats only until compatibility is demonstrated.

## 2026-10-08: Verified payload decoding and legacy text framing
- bpak_reader.py reads BPAK indices and decodes packed entries using lz4.block (4.4.5), without extracting or writing payloads. Library installed under .dependencies. Sandbox cannot read its installed directory; validation commands ran with approved access.
- Verified 861 payloads in total, including 454 LZ4-compressed entries, with zero decoding/length errors. Engine.pak: all 5; Text-en_US.pak: all 300; Text-ru.pak: all 300; Resources.pak: first 128 eligible entries under 2 MiB; Shaders.pak: first 128 eligible entries under 2 MiB. This is not whole-archive validation for Resources/Shaders.
- Resources sample contains one PNG and seven GAO-signature resources; shader sample contains 128 DXBC resources. PNG passed Pillow verify() and full load(). No image asset was saved or visually inspected; visual validation remains pending.
- Engine.pak decodes to configuration resources, including BGE_Build.ini. Its visible version field is 1.0.2; this is embedded metadata, not an independently confirmed live executable build.
- pak-payload-validation.json records IDs, lengths, signatures, hashes and errors; no full payload is exported.
- Primary legacy references fetched from the author's repository: TextFile.cs and TextGroup.cs. Their aggregate text container comprises group tables with .txg/.txi/.txs markers and offset/string buffers. Small upstream community source files are saved as jade-reference-TextFile.cs and jade-reference-TextGroup.cs for provenance, not game code.
  https://github.com/4g3v/JadeStudio/blob/master/JadeStudio.Core/FileFormats/Text/TextFile.cs
  https://github.com/4g3v/JadeStudio/blob/master/JadeStudio.Core/FileFormats/Text/TextGroup.cs
- compare_jade_text.py tested the aggregate framing against all 600 English/Russian payloads. None matches, and no payload contains the .txg/.txi/.txs marker strings. This rejects passing an individual Anniversary entry directly to that aggregate parser; it does not prove the inner resource structures were all rewritten.
- Each language has 300 entries, 34 empty and 140 starting with a zero uint32. Decimal Unicode escape patterns occur in 8 English and 123 Russian resources. The two archives share zero resource keys, so language mapping must not be inferred by matching IDs or index order.
- Additional MCP read: FUN_140af7b20 checks the little-endian magic 0x2078746d (mtx followed by space) and version 0x1001; it is a different data consumer, not evidence for text-resource decoding. This corrects the initial direction based only on the BIG_Read diagnostic xref.
- Saved decompilation outside the workspace in TEMP/rebge-bigread-next.json. No Ghidra program edits or game changes performed.

Next verified step: identify text-resource types and language selection/remapping in the executable. Follow actual consumers of resource IDs and Unicode escape handling; do not force the old aggregate container onto split Anniversary entries. Asset writer and in-game modifications remain out of scope until decoding and a round trip are proven.

## 2026-10-08: Text language mapping resolved
- MCP found locale lookup FUN_140ae2030 and default selector FUN_140ae1bf0. Selector reads the language value under HKCU/SOFTWARE/Ubisoft/Beyond Good & Evil - 20th Anniversary Edition on the Steam branch, otherwise consults PTR_s_en_US_14193ef40, and has a Windows preferred-language fallback. API names remain inferred from arguments because import typing is incomplete. No registry values were read or changed.
- Locale table at 0x141701720 has 13 entries: 0 fr-FR, 1 en-US, 2 de-DE, 3 es-ES, 4 it-IT, 5 nl-NL, 6 pt-BR, 7 ko-KR, 8 ja-JP, 9 zh-TW, 10 zh-CN, 11 ru-RU, 12 pl-PL. Strings were read directly through MCP. Availability flags start at DAT_14193f290.
- Current text-language global: DAT_14195aaa8. FUN_140ae2150 lazily initializes it. FUN_140ae1ad0 initializes DAT_14195aaac with a six-language availability table; audio-language interpretation remains provisional.
- FUN_140995700 reads LANGUAGE/LanguageID in config; further down it resets the local result to -1, so the observed read alone is not evidence that setting the config key overrides the active text language.
- Confirmed text-group consumer FUN_1409bfc80: reads a resource via FUN_140ae8760, walks 16-byte records, selects uint32 IDs at +0 and +8 according to DAT_14195aaa8/availability, keeps a fallback, and queues the two chosen resources via callbacks LAB_1409c0070 and LAB_1409bffd0. It derives record count from the first resource's unpacked byte length / 0x44 (68 bytes). Detailed inner record semantics remain unknown.
- Callback thunks jump to 0x1536a2970 and 0x15368a490 respectively; only these jumps were read, not their target logic.
- find_language_mapping.py decoded 162196 small Resources.pak entries (16..4096 bytes), with zero errors. It found 150 tables, each 208 bytes = 13 * 16.
- Every table has uint32 TXI key, .txi marker, uint32 TXS key, .txs marker. English references always occur at offsets 16/24 and Russian at 176/184. All marker checks pass. Tables account for 300 unique English and 300 unique Russian IDs, matching the entire respective language key sets. Evidence: jade-language-key-mapping.json.
- Example shared table resource 3500A08E: EN TXI=3500A090, TXS=3500A08F; RU TXI=30018CCC, TXS=30018CCD. This is a verified resource-table association, not a pairing guessed from archive order.
- Correction to earlier legacy comparison: absence of .txg/.txi/.txs strings in Text-*.pak does not mean they disappeared. The .txi/.txs reference records reside in shared Resources.pak; the referenced data reside in language archives. Jade's relationship structure persists across the changed outer container.
- No game payload files exported, game files modified, hooks installed or Ghidra program mutated. Decompilation responses remain outside workspace in TEMP/rebge-language-*.json and rebge-text-*.json.

Next: recover the 68-byte TXI entry schema and the TXS string buffer/Unicode escape semantics; build a read-only text exporter using the confirmed shared table mappings. Full runtime UI and language-switch validation remains outstanding.

## 2026-10-08: Stage 1 complete — localization exporter
- Stage 1 was explicitly approved by the user. Implemented jade_localization.py, strengthened BPAK index bounds in bpak_reader.py, added 4 corruption/roundtrip/control-preservation tests and README commands.
- Ghidra TXI callback FUN_1536a2970 loads data and extracts the first uint32 per 0x11 dwords (68 bytes) on the relevant native path. Other branches use different layouts; this exporter only targets the installed BPAK data, not all historical Jade variants.
- Ghidra TXS callback FUN_15368a490 copies the loaded buffer and enforces a final zero; empty data gets a one-byte zero buffer at runtime.
- All EN/RU TXI data is divisible by 68. A record is uint32 byte offset plus a 64-byte name field; observed unused name bytes often contain 0xCC. Preserve all bytes rather than regenerating padding.
- FUN_1409a6150 converts wide code units >=256 into decimal digits prefixed by backslash U plus and suffixed by backslash. This confirms the escape spelling. The exporter's CP1252 base interpretation is still provisional, and surrogate handling/other control semantics are not established.
- Exported 150 groups in each language: 7134 EN and 7133 RU records; all offsets in bounds, all strings terminated. Unicode escape occurrences: EN 140, RU 194574.
- 300 TXI serializers reproduce original TXI bytes. 300 JSON exports read back to byte-identical TXI and TXS, including all untouched buffer bytes. This proves lossless export, not modified-archive repacking.
- Shared group 3D0051F4 contains 172 EN versus 171 RU records; creditsVTS exists only in EN. All remaining group name multisets match. Named occurrence matching count is 7133 (includes two unnamed entries, so the label in the JSON is occurrence-based, not strictly nonempty names).
- Four meaningful tests passed: padding/offset roundtrip, malformed TXI stride/offset/termination, Unicode/control preservation, malformed BPAK header/count/name bounds.
- Export directory: C:/Users/Dan/Desktop/rebge/assets/legacy-exports/stage1-localization. Temporary storage may be cleaned by Windows; rerun the documented command to regenerate or choose a durable external directory. No assets committed or exported into workspace.
- Metadata-only result: localization-validation.json. Reader and exporter: bpak_reader.py, jade_localization.py; tests: test_localization.py; dependencies: requirements.txt. README.md documents usage and limitations.
- Rust/cargo not present in PATH or C:/Users/Dan/.cargo/bin, and no standard .rustup/toolchains found. No toolchain was installed.
- Stage 1 acceptance satisfied for read-only localization and lossless export. In-game typography/control rendering and modified asset roundtrip remain unverified. Next requested stage: one real scene and its dependency formats.

## Стадия 2 — проверенный статический срез (2026-10-08)
Подтверждение пользователя получено. Найдены 70 828 GAO и 637 WOW в bounded census, 440 payloads >8 MiB пропущены, ошибок декодирования остальных нет. Восстановлена сцена D90057F0 / 00_01_home_sas_hangar: список D90057EF содержит302 GAO. Export viewer:91 visual objects,173 batches,73875 triangles;61 unique type1 meshes,10 LOD resources.46 textures decoded,34 used by draws; unsupported texture27000502 container12. Mesh and texture known fields roundtrip; unknown fields retained.6 synthetic format tests passed. WebGL actual screenshot visually verified, saved outside repo TEMP/rebge-assets/stage2-hangar/preview.jpg. Local viewer http://127.0.0.1:8181 (serve_scene.py). Spatial grids10x10 and3 collision primitive records recovered; exact physical semantics unverified. Full schemas, function addresses, limits in SCENE_FORMATS.md. No game modifications. Stage3 Bevy requires next stage confirmation.

## Стадия 3 — первый Bevy runtime (2026-10-08)
Пользователь подтвердил стадию. Установлены официальные Rust stable 1.99.0 (minimal + rustfmt) и Microsoft Visual Studio 2022 Build Tools с VCTools/Windows SDK, installer exit0. Cargo выбрал Bevy0.19.1; версии сохранены в Cargo.lock. Официальные примеры custom mesh/screenshot и локальный исходный код Bevy использованы для API, включая FontSize/FontSource.

src/main.rs читает внешний scene.json и PNG, проверяет finiteness/triangle stride/texture paths до открытия окна. Jade (x,y,z) -> Bevy (x,z,-y), единицы без масштабирования. 91 visual object,173 batches,73875 triangles. Материалы unlit, two-sided, alpha mask0.2, repeatUV; это diagnostic preview, не native rendering. Camera arrows/zoom/Home реализованы; реальный input injection не проверялся.

Первый кадр содержал только UI; runtime ещё не был принят. Сохранение мешей в MAIN_WORLD|RENDER_WORLD и synchronous_pipeline_compilation плюс явные Transform/Visibility исправили отображение. Отдельно не определено, какая из этих настроек была необходимой причиной. Bevy default font не содержал кириллицу; Windows Arial читается локально без копирования/распространения. RU InvC_Menu_NewGameStandard отображается как literal control token + текст; semantics управляющих кодов не восстановлены.

Финальная сборка и cargo test --locked успешны (coordinate handedness/length). cargo fmt --check успешен. Missing assets и MissingRecord дают exit2 до GUI. Run-Rebge.ps1 -Locale ru -Capture завершился exit0; NVIDIA RTX3060Ti, Vulkan, driver617.14. PNG1280x720 сохранён C:/Users/Dan/Desktop/rebge/assets/legacy-exports/stage2-hangar/bevy-20261008-014511.png и визуально просмотрен: стены пещеры, настилы, ограждения с оригинальными текстурами, русская локализация читается. Журнал bevy-run.log; metadata bevy-validation.json. Полное совпадение native frame, нормали/освещение, active visibility, анимация, collision behavior и gameplay не подтверждены. Game executable/OLD_TEST не запускались, установка игры не изменена. Stage3 завершена в объёме статического Bevy viewer; Stage4 требует подтверждения.

## 2026-10-08 — Стадия 4, статический реверс управления и компонентов
Одобрена пользователем. Восстановлены 3864 native callbacks, фильтр ввода clamp(delta*12), структура actor tail и компоненты4/20. Аддитивные vertex deltas подтверждены native update1409d3670; skeleton не заявлен. Условная длина component20 уточнена по Ghidra memory константе1.001. Два реальных GAO прошли byte roundtrip и контроль границы collision tail; два Python теста проверяют truncation/conditional length/bit preservation. Rust filter tests(3)/build/fmt прошли. STAGE4_REVERSE.md хранит адреса и ограничения. Критерий управляемого персонажа пока не достигнут; оригинал не запускался.
Подстадия4.1: update component20 проверен через Ghidra, RET0; гипотеза timeline driver исключена. Создана именованная функция в базе анализа и база сохранена; bge.exe не изменялся. Стадия4 разбита на4.1–4.6, следующая задача идентификация Sally/GAO. Readers tests2 passed.

## Организация проекта и продолжение4.2
116entries разложены по bevy/tools/reports/docs/references, актуальные пути в README и manifest. Python report paths независимы отcwd, guards экспорта поroot. Проверено12Python+3Rust tests, чтениереальныхactorfields, missingassets exit2, HTTP200 preview. OLD_TEST не перенесён окончательно из-за Windowslock; перемещённые файлы возвращены.
Ghidra: Sally_sa_init141313190, lookup140aeac00, scriptcontext140b272a0 прочитаны. 10ключей изSallyinit существуют вResources.pak; новые metadata/probe сохранены. DAT1420d6620 не постоянныйplayerpointer: executioncontext переключается/восстанавливается. 4.2не завершена; следующееGAOflagsbit1/22 иbrain/action/mesh association.

## 4.2 — Behavior graph Sally
РазобраныGAOpre-actionbranches,serializedmatrixstride132. Подтверждена цепочка71003F5A->71003F58->71000CDD/71003F60; definition79tagrecords,78ofc сnativeSallycallbacks. Bit5hierarchylabel исправленнаbehavior вновомprobe; native loaders подтверждены. 710047BC связан сGlobal_glob, а неplayer. Skinreload1411b0430 прочитан, дальнейшиеключи0700654D/9E001C0D/71000CDC. 12tests passed, actualreadbounds passed. Уточнение:3864 PE callbacks являютсяheuristiccandidates, служебныеlowkeys иFFFFFFFF исключеныизсовпадений;78ofcподтвержденыотдельно. Meshещёнепривязан,4.2не завершена.

## Typed assets and system layout
Development plan updated; known assets exported to private permanent library, catalog470entries withsourcekeys/hashes/deps/limits. 61mesh46texture53material9groups1scene300texts; allhashes/300roundtripsverified. Pending formats explicit. Bevy split into7functional modules, nestedscene loading, newlibrary default; build/fmt/3tests passed and screenshot visually reviewed. FullSallymesh still unresolved: geometry47GAOparts has early8vertex meshes,235actrecords found; materials identified. Stage4.2 continues.

## Storage unified by explicit user request
Assets/captures/legacyexports/rawGhidraoutputs/installers migrated fromAppData/TEMP toproject. ActiveGhidradb savedviaMCP, userclosedapp, bge.gpr/bge.rep relocated toghidra/project. Exportandlaunchdefaults/guards/docs/Gitignore updated.470assetSHAverified,12Pythontests passed. Userstorageinstruction overridespriorUMexternaldirectoryguideline. Originalgame andsharedtoolchain untouched.

2026-10-08 stage4.2: Sally action list corrected to 235 slots / 199 actions / 36 empty. Added jade_actions.py and probe_sally_actions.py; 199 real-resource byte-exact roundtrips, all 214 first-resource links present, 3 targeted tests pass. Native loaders 140b442c0/140b43db0 and third callback 153629c80 cached in reports/ghidra/raw. Variable tracks and opaque action tails remain incomplete. See STAGE4_REVERSE.md.

2026-10-08: Stage4.2 animation pass. Added jade_animation.py, jade_pose.py and
bounded export probes. 214 resources parse to EOF/roundtrip source segments;
97481 keys, 77644 local rotation samples, no delta quaternion samples. Saved
private typed JSON and pose matrices under assets/animations/sally. Four reader/
pose tests pass. Rig hierarchy/translation/skinning/Bevy playback still pending;
see STAGE4_REVERSE.md and stage4-sally-local-poses.json for evidence and limits.

2026-10-08: Stage4.2 parent/translation pass. Native1409b4e70 confirms bit22
parent chains. Extracted47-object acyclic graph (45internal/1external links),
19533 position keys across214 animations. Added native translation curves and
cycle validation;6 tests pass. Saved skeleton/translation JSON and SHA256
manifest. Full pose assembly, scale composition, native timing and playback
remain pending; next actions recorded in CONTEXT.md.

2026-10-08: Stage4.2 external root/matrix pass. Closed Sally graph at48objects,
confirmed native parent*local multiplication, exported original linked pose.
7tests pass. Saved GAO world/local matrices differ; no visual parity claim.
Indexed animation binding/native timing/skinning/Bevy playback remain pending.

2026-10-08: Stage4.2 binding/timing pass. Confirmed47-slot indexed Sally
binding through descriptor/list/cloning/native consumers. Exported binding
and probes for214resources/9613tracks. Restricted transform timing supports
9522tracks;91control tracks preserved and rejected explicitly.9tests pass.
Native quaternion interpolation/events/cloned parent mapping still pending.

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

Final build attempt blocked by existing user hangar preview PID36868 started13:56:10 (sceneD90057F0, no capture). Left running. Source cargo tests3pass; Sally snapshot rendered using existing executable. Latest Home-reset source change not linked into executable yet.

2026-10-08: Stage4.3 started. Ghidra1409bcd20 transition duration=(byte59+1)/60; elapsed=ushort5a/15360+delta. Constants confirmed via MCP memory. Read-only Sally capture extended with action/phase/instance headers; py_compile passed. Live validation pending loaded scene; no animation parity claimed. See STAGE43_ANIMATION_TRANSITIONS.md.

2026-10-08 14:40: Read-only live Sally capture succeeded with47 palette matrices and animation headers. Transition inactive (component byte1 bit2 clear); actionFFFF/phase0/speed56. Added restricted native1409bcd20 float32 transition clock,6tests passed. No clip playback/weight direction parity claim; active transition trace next.

2026-10-08: Stage4.3 MCP15358c6f0/1535912b0 confirms root XYZ ratio direction: increasing ratio restores saved primary position. Added bounded float32 root-position helper;8transition tests pass. Does not prove bone blending or full animation runtime. Next clip-link layout/track state and active live oracle.

2026-10-08: Stage4.3 native clip link/40-byte definition/12-byte state layout recovered via MCP1532461d0 and earlier140b28360/140b272a0. Bounded capture decoder added with3passing tests. No resource identity inferred from pointers; live validation next.

2026-10-08 14:48: Live44tracks read. Fixed indexed-slot offset20 (old144732 labels incorrect), added bounded24byte frame headers. Candidate matcher yields primary26000546/transition2600313F by ordered slot/tick/flags only; transform identity not proven. Snapshot144810+candidate report saved. Stage4.3 ongoing.

2026-10-08 14:50: Native transform payload capture succeeded. Compared724keys: primary682max1.9483e-6 fails1e-6 threshold; transition42max5.96e-8 passes.271keysunverified. Full clip/pose parity not claimed; reportstage43-runtime-clip-candidates.json. Source float32 arithmetic residual investigation next.

2026-10-08: Stage4.3 float32 decoder discrepancy resolved against native oracle:724packedXYZ keys exact after native arithmetic order. Decoder corrected;float3 payload oracle added.928keys match exactly,67unverified.29animation tests pass. Historical exported JSON not regenerated; source integers retained, matcher recomputes. No full animation/Bevy parity claim.

2026-10-08: Stage4.3 remaining67keys decoded as uncompressed quaternion10hex. All995key payloads checked:88transitionexact;907primary equivalent with33whole-quaternion sign flips. Zero rotation-equivalent error; direct equality fails explicitly.5runtime-reader tests passed. No pose/gameplay parity claimed. Next runtime state→sampled local transforms and native palette assembly.

2026-10-08: Stage4.3 timed42track channel oracle added from saved145025. Positionmax3.45e-6, rotation fails0.23949 atslot20, plus10/9.2roottracks excluded; no fullposeparity. Native modifier/localmatrix investigation next. Original game not needed for current static investigation.

2026-10-08: Stage4.3 exceptional rotations persist against palette-local oracle. Found native140b49ba0 modifier/update write guards; extended capture actual linkedlocal/parent and guard flags. Rootcause not yet proved. Need next live scene to distinguish skipped channels from post-animation modification.

2026-10-08 14:57: Newlive localmatrix snapshot verifies parentmapping and excludes tested rotation skipguards atslots9/10/20.3rotation discrepancies persist; other18rotation/21position tracks agree. Currentprimary2600313F+transition260006DE all654keypayloads exact. Need post-animation writer tracing/static callchain; fullpose not achieved.

2026-10-08: Found named eye-follow callback140e02760→actortracking1409b3b20→role resolver1409c18e0, roles0/1/12 optional. It writesrotations/restoresposition+scale. Candidate explanation only until role-to-slotmapping captured. Added runtime role tag read,py_compile passed. Ghidra evidence saved. Game not needed until role verification.

2026-10-08: A9001F3E source role table decoded142bytes47records. Roles0/1/12 map20/10/9 exactly3exceptional pose nodes; matches eye-follow writer1409b3b20. No live writer causality or procedural output parity yet. Source report saved; no asset manifest mutation.

2026-10-08: Stage4.3 tracking numeric constants recovered26floatvalues; yaw/pitch helpers via MCP. Restricted unit-vector pitch helper3tests pass; no full procedural tracking or poseparity. Next resolve actual10callerparameters and dynamicangle state; no gameinput performed.

### 2026-10-08 — проверены аргументы Sally eye-follow
Через Ghidra MCP сохранены три страницы listing 140e02760..140e02c18 (`stage43-eye-follow-listing*.json`). Обе инструкции CALL 140e02b2f и 140e02bd7 подтверждают Windows x64: RCX actor, RDX target XYZ, XMM2 strength, R9D mode; стек +20/+28/+30/+38/+40/+48 — параметры 5..10 с масками 80000000/40000000/20000000/10000000/08000000/04000000. Mode = combined & 03FFFFFF. Combined вычисляется ADD двух DWORD (brain+604 и brain+618), не OR; перенос и переполнение существенны. В ветке нулевой цели bit16 brain+618 очищается до сложения. При strength<1 порядок SSE: strength * float32(delta * multiplier), затем clamp [0,1].
`tools/jade/jade_tracking_call.py` реализует только эту упаковку после выбора ветки; специальная обработка цели/фазы, разрешение handles и полный writer ещё не реализованы. Пять новых проверок плюс три проверки pitch прошли. В capture добавлены counter +AF и gate +B2 для следующего снимка. Игра для этого шага не потребовалась; live данные новых полей пока отсутствуют.

### 2026-10-08 — условия фаз процедурного взгляда
Ghidra MCP: `stage43-tracking-handle-storage.json` раскрывает 1400bf6a0: индекс дескриптора = encoded>>16, индекс элемента = encoded&FFFF; дескриптор stride12, type short+8, base offset DWORD+0; типы27/28/2B/2F используют stride8, тип29 stride64, остальные без индексного смещения. Это адрес хранилища значения VM, не самостоятельное разрешение actor handle. Caller затем отдельно разрешает значения 0/1/2 через PTR_DAT_14193f710.
Сохранены listing `stage43-tracking-phase-listing*.json`; реализован ограниченный `jade_tracking_phase.py` для 1409b3c55..1409b3e11. Для допустимой основной фазы бит4 разрешает обычную коррекцию; при component high byte!=1 учитывается валидность переходной фазы и её бит4. Разрешённый путь сбрасывает +AF. Заблокированный путь с control8000 увеличивает байтовый +AF на trunc(float32(delta/0.01666666567+0.5)), weight=counter/16; при counter>=16 прекращает выполнение. С control1000 выполнение прекращается без изменения счётчика; иначе счётчик повышается до6, weight=.4, шестой вызов уже не проходит. Байт складывается с переполнением, что сохранено. Шесть новых граничных проверок и восемь прежних прошли (14 всего). Функция принимает уже разрешённые фазы, не выполняет поиск в памяти и не изменяет позу. Полный writer, цель и live причинная проверка остаются незавершёнными.

### 2026-10-08 — адресация и координаты цели
`jade_tracking_target.py` переносит подтверждённые ветки 1400bf6a0: stride дескрипторов12, индекс/элемент из DWORD, смещение из unsigned DWORD, тип signed short; возвращает адрес значения, не actor. Лимит дескрипторов обязан задаваться вызывающей стороной для известных коротких таблиц (в самой структуре count не доказан). Разрешение actor references0/1/2 отделено от чтения VM storage. Ghidra MCP `stage43-tracking-target-position.json` подтверждает 140b33020: null→XYZ0; actor flags bit1 clear→world matrix+30/+34/+38. Ветка linked actor выполняет иерархическую композицию и пока явно отвергается. Пять новых проверок, всего19 tracking tests, прошли. Текущий выбор цели callback/список исключений/особый режим bit16 не перенесены; полный procedural writer не готов.
Следующий live шаг: новые role_tags, AF/B2 и текущие фазовые данные; снимок без остановки процесса, без управления вводом. Цель — подтвердить роли и условия уже восстановленных веток, не заявлять полную идентичность pose.

### 2026-10-08 15:17 — live роли и gate подтверждены
Пользователь вышел из меню. Read-only снимки151723/151757:47palette, роли всех47клона совпадают с A9001F3E; roles0/1/12→slots20/10/9. component_flags257 (highbyte1), AF0, B2=144 (бит8 clear). Текущий descriptor1phase, flags12 (бит4 set), control16: восстановленный gate продолжает коррекцию и сбрасывает AF, что согласуется с AF0. `probe_tracking_live_state.py` сохраняет stage43-tracking-live-state.json; strength/delta placeholders допустимы только для этого allowed gate, не реальные параметры writer.
Primary2600313F88keys,transition260006DF724keys:812payloads с нулевой ошибкой и без непроверенных ключей. Sample42tracks:21translations <=4.3721e-6,18rotations <=1e-5,3rotation deviations persist (max.424302). Actorroot2tracks исключены. Это подтверждение данных/role mapping/gate, не покадровая трасса writer и не полная pose parity. Захват phase block сначала имел ошибку длины32n+4; исправлено32n+8, повторный снимок успешен.19tracking tests pass. Пользователь может оставить игру в меню; дальнейшая статическая работа не требует сцены.

### 2026-10-08 — математика процедурных матриц
Ghidra MCP сохранены stage43-tracking-math-1409b4e70/1409b59d0/140aec970/140aec520.json, trig-first и basis-rotation-listing. 1409b4e70 композиционно строит world из local цепочки при actor400000 и наличии parent, иначе копирует world. 1409b59d0 вычисляет inverse(parent world)*actor world в linked local, проверяет scale metadata и вызывает140aed9a0 normalization. Полный перенос этих веток пока не сделан.
`jade_tracking_rotation.py` переносит подтверждённый SSE update140aec970: Y'=float32(Z*s+Y*c), Z'=float32(Z*c-Y*s), XYZ basis only, flags|4; X/translation/scale storage не меняет. Коэффициенты передаются явно: идентичность native trig library не заявляется.3новые проверки знака четвертьоборота, сохранения позиции, обратимости scaled basis и flags прошли; всего22tracking tests. 140aec520 содержит битовые sign flips, которые decompiler ошибочно показывает как численные int conversions; до проверки listing эта функция не переносится. Следующий шаг — нормализация140aed9a0 и проверка writer matrices на saved snapshot, затем интеграция полной angle/state цепочки. Игра пока не нужна.

### 2026-10-08 — нормализация базиса и проверка гипотезы
1400369e0 через Ghidra MCP сохранён в stage43-vector-normalize.json; 140aed9a0 использует normalize X, normalize(Z cross X)→Y, normalize(X cross Y)→Z. `jade_basis_normalize.py` переносит обычные finite float32 ветки, включая сохранение нулевого вектора (без подмены identity), и не изменяет translation/scale metadata.3новых теста passed. Full caller scale restoration/world-local pipeline ещё не реализован.
Oracle151757 теперь отдельно сравнивает normalized expected local. Slot9 error .038305978→.038305975;slot10 .015471814→.015471809;slot20 .424302028→.424302042. Одна нормализация ожидаемой анимационной матрицы не устраняет расхождения. Это проверка узкой гипотезы, не доказательство полного writer исполнения/полной причины расхождения. Исходные21position/18rotation совпадения сохраняются. Следующий шаг — yaw sign axis и protected bit flips в directional basis writer, затем объединение ограниченных helpers. Игра пока не нужна.

### 2026-10-08 — направленный базис
Listing140aec520 сохранён stage43-directional-basis-listing/2.json. ADD DWORD80000000 меняет signbit float; decompiler int-conversion неверен. `jade_directional_basis.py` реализует ordinary nonzero finite branch: Y=-normalize(direction). Supplied up: X=normalize(-(direction cross normalize(up))), затем Z=X cross Y. Без up: X=normalize(existingZ cross Y), затем Z=X cross Y; это другая знаковая ветка (подтверждена listing). Translation/metadata сохраняются, flags|4. Native reset-byte branch и near-parallel perturbation явно неподдержаны. Порог parallel raw cross = floatbits30897060.4теста passed; исходное ошибочное ожидание identity для null-up исправлено согласно инструкциям.
Yaw helper использует triple product с DAT1420b0b98/b0ba0; значения оси ещё не подтверждены, потому yaw не реализован с угаданной Z. Full directional writer integration/live pose parity остаются незавершёнными. Игра сейчас не нужна.

### 2026-10-08 — знак yaw подтверждён listing
Сохранены yaw-axis-references/axis-writer/call-listing/sign-listing/2.json. Инициализатор140997a70 пишет global1420b0b98 XY=0,140997a7b пишет Z=1. Есть ещё WRITE154b1b439: runtime неизменность оси не доказана. Поэтому `yaw_difference(first,second,sign_axis)` требует явную ось.
Декомпиляция140036db0 ошибочно опускает третий аргумент и хвост возврата: listing сохраняет R8 в RBX, в140036f37..f57 вычисляет dot(cross(first,second),axis) и меняет знак длины cross при отрицательном dot.1409b4d30 использует этот знак для acos(dot(normalizedXY)), принимает antiparallel +pi при нулевом cross. Restricted finite nonzeroXY helper добавлен в jade_tracking_angles.py; использует host acos, не native bit-exact transcendental library.3новых теста passed,25tracking tests всего. Направленный базис4теста и нормализация3теста предыдущего шага отдельно. Полное смешивание/ограничения/обратная композиция writer не объединены; live pose parity не заявляется. Следующий шаг — runtime sign_axis capture и numeric angle limits/correction chain. Игра пока не нужна.

### 2026-10-08 — параметры ограничений углов
`jade_tracking_limits.py` переносит блок инициализации1409b3b20 из сохранённой Ghidra decompilation и подтверждённых float constants. Режим0: основной предел60°, диапазон±120°, offset0;1:offset30°/upper25°;2:offset35°/upper7°;3:offset21.25°/upper25°;прочие offset0. Остальные значения сохранены под native decompiler local names, без предположений об окончательном clamp order. При parameter10=0 вторичные limits=None вместо native uninitialized scratch.
Глобальные override1421015ac/b4/a0/59c/a4/b0/a8 принимаются только явно; sentinel1000 оставляет preset. Затем offset прибавляется к двум pitch locals float32; parameter6 unrestricted последним заменяет шесть основных locals на±pi. Вторичные limits не меняются этим блоком.3новые проверки passed;28tracking tests всего. Это подготовка параметров, не полный angle limiter и не pose parity. Следующий шаг — восстановить потребителей этих locals и разнести коррекцию между roles0/1/12. Игра пока не нужна.

### 2026-10-08 — blend/clamp scalar corrections
Listing1409b4700..47e1 сохранён stage43-tracking-clamp-listing.json. `jade_tracking_correction.py` переносит ограниченные блоки delta=float32((desired-current)*strength + accumulated), затем clamp(current+delta), возвращая bound-current при выходе. Upper-first порядок сохранён даже при противоречивых override ranges; никакой guessed shortest-arc/wrap не добавлено. Pitch использует accumulated0, вторичные yaw используют прежнюю correction лишь при native continuity predicate. Predicate и особые role0 yaw crossing branches ещё не перенесены, caller должен передавать доказанные inputs.
4новых проверки (result angle vs delta, accumulation after weight, inverted range branch, no wrap) прошли;32tracking tests всего. Writer вызывает yaw/pitch затем directional basis дляrole0;role1 имеет дополнительный near-horizontal gate abs(normalized worldZ.z)<.05;role12 optionalparameter10. После world→local восстанавливает localpositions/scales. Это пока кодовый анализ распределения, не полностью подключённая анимационная система и не live pose parity. Далее — continuity predicate/crossing branches, восстановление вызова yaw rotator154bffba0 и объединение ограниченной цепочки.

### 2026-10-08 — crossing branches, world yaw, next live oracle
Ghidra MCP confirmed 154bffba0 listing: each X/Y basis pair rotates x'=x*c-y*s, y'=x*s+y*c with separate float32 operations; Z, translation and metadata preserved, flags|4. Implemented rotate_world_xy with explicit trig coefficients; native transcendental precision is not claimed.
Verified 1409b45c8..46b9 continuity predicate and role0 crossing branches. tracking_corrections combines resolved role angles, existing limits, previous correction and strength. Opposite-limit guard uses native floatbits3a83126f (read at1417363c0), zeros all corrections; previous-crossing branch bypasses weighting/clamp. Optional role12 rejects absent initialized secondary limits. No guessed role/target inputs.
37 tracking tests pass. Capture script syntax checked; collector extended with runtime yaw sign axis, delta, multiplier, global overrides and bounded active-context brain604..61f values. Active/default actor is explicitly compared with Sally; unrelated callback context must not be attributed to her. Reads remain unsynchronised and do not establish writer invocation.
Apply listing1409b47e1..494d proves XMM1 angle arguments absent in decompiler: role1 pitch is rebuilt-current (RBP-10 minus RSP48), role12 pitch likewise (RSP58 minus RSP34), applied unconditionally in their enabled branches. World->local/scale restoration and full native trig remain incomplete.
Next gate: a fresh loaded-scene snapshot is needed to establish actual callback inputs/sign axis and whether active context belongs to Sally before choosing the applicable tracking branch. Bevy integration/full pose parity remain unproven; stage4.3 stays in progress.

### 2026-10-08 — live snapshot153652
User confirmed loaded scene. Readonly snapshot stage4-sally-runtime-20261008-153652.json captured47palette entries. Primary2600313F88keys +transition260006DE566keys =654 decoded channel keys exact, no sign flips. All47role tags match source; roles0/1/12 map20/10/9. Allowed phase flags12/control16 resets AF0; no actual callback invocation proof.
Global yaw sign axis observed(0,0,1), delta.0166015625, multiplier20, seven override globals zero. Active default actor183889d2e38 differs Sally1836115e278. Active brain fields appear implausible as tracking parameters (strength5.42e-43); retained as raw observations, not interpreted as Sally state or passed to correction pipeline. Need resolve Sally callback/VM context ownership before requesting another live oracle. Current capture does not validate full tracking correction. User may leave game in menu during static analysis.

### 2026-10-08 — actor-owned Sally context recovered
Ghidra MCP140b29720/listing confirms actor+28 modifier, modifier+8 AI context. Global1420c3490/defaultactor are temporarily assigned during callbacks and restored; snapshot global context is not actor ownership. Added bounded jade_actor_script_context.py and collector integration. Shared callback descriptor is **context (count+58/table+60); extra context+90/count,+98/table entries24 bytes carry record/index/owner. No callbacks executed.
Snapshots153937/154028 directly identify Sally context1838d6229a8, brain1838d3cfc68, VM1838a323e48. Shared callback2 relocates to140fb1fe0, extra callback3 ownerSally relocates140bd1110. Actual tracking strength .05000000074505806, baseword0, trackingword84010000, encoded target014B0000. VM storage183be4f8e90 resolves to Sally herself. These replace unrelated-global guesses; still unsynchronised observations, not proof of invocation.
Target selection140e02760 recovered: bit16 clears; role0 point plus native Z+.25 when offsetZ<=10000, self target retains offsets, other target zeros offsets. Sentinel offsetZ>10000 subtracts10000 then uses actor-position path. Zero target preserves offset storage. Added jade_tracking_target_selection.py with explicit resolved caller decisions; near target role0 uses linked hierarchy in native140b33020, not simply stored world translation. Full linked target evaluation not yet integrated. Missing blocked-target list/native callback execution timing prevent final input oracle.
41tracking tests+3actor-context tests passed. Next runtime check should capture active loaded scene while Sally takes a short movement, to compare owned state/target selection across poses; original input remains user controlled. No full tracking/Bevy parity claim.

### 2026-10-08 — movement snapshot154401
User moved Sally and stopped; readonly snapshot154401 captured. Actor-owned context unchanged1838d6229a8. Position changed72.7284/18.8991/4.5000 to78.4879/17.6625/4.5000, displacement about5.89. Target VM storage still resolves Sally. Strength .05->.15, offset(.7392,-.3246,.5901)->(.9543,.2988,0); words unchanged84010000/base0. compare_tracking_snapshots.py writes strict JSON comparison report; this is observed correlation, not causality.
Primary7100B0E8:898checked/5unverified,2quaternion sign flips; transition7100B5A4:430checked/3unverified,23sign flips. Maximum rotation-equivalent error0 for all1328checked keys. Raw component comparisons are NOT exact because sign flips;8keys remain unverified. Probe sampled primary pose42tracks:0rotation tracks within1e-5,11positions within1e-5,maxrotation.5678/maxposition.03984. Do not attribute all differences to tracking; active transition blending and unsynchronised sampling are not reproduced.
User can leave game in menu. Next static work: linked target hierarchy140b33020 composition, blocked-target filtering, full transition pose combination before interpreting tracking-only differences. Stage4.3 remains incomplete.

### 2026-10-08 — linked target, gate and capture timing
Implemented jade_target_hierarchy.py from140b33020 listing and140ae9420/140ae9c00 no-scale listing: bottom-up raw affine parent*local with float32 MUL/ADD, final root world. Explicit missing-parent fallback returns original world; cycle/missing node/scale branches rejected. Unlike skin preprocessing, this consumer directly reads stored matrix fields even with flags2/4 clear.5tests pass. Snapshot154401 points roles1/12 exact;role0 mismatch.01155. Fresh passive snapshot154853 all3 target-role positions exact, demonstrating saved local chain can reconstruct those points; no final pose parity proved.
Added resolved-target gate: blocked reference table compares resolved actor directly and clears VM targetstorage; phase bit4 rejection only selects zero-target.2tests pass. Collector reads bounded count1421015b8 and entries142101690. Snapshot154853 targetreference0,blockedfalse,phaseallows true; zero-target branch selected. Native strength is transformed .15*delta*20 to.04980469 in this snapshot.43tracking tests+5hierarchy tests pass.
Pose oracle now requires --instance primary/transition and verifies source/runtime frame headers; previously selecting transition source with primary state produced invalid comparisons, corrected.2tests pass. Correct transition-only154401 comparison still0rotationmatches; primary-only comparison remains0. Neither proves final transition logic wrong: actual read timestamps differed.
Found capture ordering uncertainty: full clip payload decoding preceded bone matrices. Collector now prepares mutable link/descriptor/definitions/state bytes first, reads matrices before full payload/geometry, reports pose_read_window_ms. Payloads remain live/unsynchronised; this is not an atomic pause.6runtime-track tests pass, including immutable prepared-state preservation; collector syntax checked. Next needs loaded stationary scene for one timing-improved pose oracle, before interpreting residual errors. No game input injected.

### 2026-10-08 — fast pose oracle155659
User confirmed stationary loaded scene. New readonly snapshot155659 pose_read_window_ms2.04. Primary7100B0E7:179decoded keys exact, transition7100B2E4:361exact/3unverified;540checked exact total. All3role targetpoints reproduced exactly by linked hierarchy. Targetreference0 and phaseallows true ->zero-target branch; strength argument.0498046912.
Primary pose42ordinarytracks:18/21rotations within1e-5,all21positions within1e-5,maxposition5.4298656e-6. Actual linked local errors ordinary18bones<=1.06e-7; residuals onlyroles12(slot9).02982099,role1(slot10).01995510,role0(slot20).01742627. Root2tracks excluded. Snapshot uses different clip than154401, so reduced mismatch cannot be attributed solely to capture reordering. Read window is shorter, not atomic; no complete tracking/final pose/Bevy parity proved.
Game can remain in menu. Next static task: reproduce zero-target correction branch using rebuilt source basis and native world->local/translation+scale restoration, then compare these3residuals against155659. Stage4.3 remains in progress.

### 2026-10-08 — zero-target matrix pipeline with explicit prior state
MCP recovered140aea110 transpose/negative-translation inverse,140ae9fb0 vector transform and140aea6e0 scale restore. Added jade_tracking_local.py no-scale parent inverse/raw affine product/basis normalization/original local position restoration. Scale-reference vectors are explicit: initializer140997a28 sets unit(1,1,1),140997a85 sets zero(0,0,0); another writer exists. No runtime constancy assumed. Metadata restore treats either reference within native1e-4 threshold as no-scale. General scaled inverse/product remains unsupported.4tests pass.
Added jade_tracking_zero_target.py: already resolved allowed zero-target branch, caller supplies prior stored world matrices, current local pose, roles0/1/12, continuity actor, strength/limits/axis and trig coefficients. Desired basis comes from rebuilt local hierarchy, current angles from supplied stored world. Role0 weighted/clamped yaw/pitch; secondary yaw weighted, secondary pitch rebuilt-current unconditionally. Apply yaw/pitch/directional basis, then restore local in order12/1/0 while rebuilding updated parents. Original positions preserved; no-scale only, near-horizontal role1 fallback explicitly rejected. Host acos/native trig precision limitation retained.2integration tests (full strength recovery, zero strength prior yaw/no input mutation) pass;49tracking tests total. Not validated against final native pose because prior writer input is absent from a single post-correction snapshot.
Prepared capture_tracking_sequence.py readonly bounded128samples(max256/5seconds), primary states/headers and actor/world/local matrices, no geometry/payload copying. Tracks primary elapsed marker before/after and primary instance stability; equal markers are consistency evidence, not atomic frame proof. Does not drive/pause game or write its memory.7runtime-track tests pass, including deferred state preservation and header-only no payload reads; sampler syntax checked, not live-run yet.
Next needs loaded stationary original for brief temporal capture. Samples may repeat/skip frames, so reject unsupported frame gaps rather than infer exact prior state. No fulltracking/Bevy parity claimed; stage4.3 in progress.

### Temporal capture160742
2026-10-08: sequence160742 analysis

128 read-only samples span0.5290553 seconds. Pose read windows0.9398..2.1271ms.
Actor position remains(80.00886536,9.91706467,2.80000997); actor-owned brain block unchanged.
One primary instance;44track ordered headers match only local resource260006DE.
No payload bytes checked in this sequence.

Four runs of first-track elapsed marker, five distinct world poses. One adjacent
pose change occurs without a marker change. Therefore first-track marker equality
is insufficient to establish a coherent pose or callback order. All128 local
before/after marker checks passed; this does not override the observed limitation.
No native frame counter captured: adjacent samples must not be assumed consecutive
game frames or used blindly as previous-world inputs for zero_target_step.

Sampler strengthened to retain/compare all primary track states before/after bone
reads, and compare instance link/resource identities. Those new checks have not
been exercised live yet; old sequence contains no full-state check fields.
Targets, phase gates and transition state remain absent from this sequence.
No final tracking pose or Bevy parity claim. Stage4.3 remains in progress.


### 2026-10-08 — local pose blend before callback3
Ghidra MCP caller1409ce1be resolves function1409cd5e0. Its linked-local pose loop calls140aed7b0 and writes the blended local matrix back before140b29720(actor,3), bracketed by14210c150=1/0. This establishes local blend before callback3 in this path; it does not establish the age of stored bone-world matrices at callback entry. Separate initialization path1409ce4e0 evaluates1409bd3b0 with delta temporarily zero, restores delta, then dispatches callback3 before palette1409ce210. Do not treat initialization and normal blend as identical paths.
Listing1409ce01e confirms RCX=destination scratch,RDX=linked-local matrix,R8=same scratch,XMM3=weight.140aed7b0 extracts operand quaternions, chooses shortest sign, computes acos and reciprocal sqrt, then140aed150 interpolates and normalizes;140aed650 writes rotation. Threshold14173c8e4 bytesfeff7f3f (float just below1). At threshold the angle-zero branch copies first quaternion rather than nlerp. Rotation weight is passed unclamped; caller separately clamps translation weight to0..1. Matrix extraction/native quaternion normalization and transcendental bit parity are not ported yet.
Added jade_pose_blend.py numerical quaternion stage with explicit extracted operands and float32 arithmetic. Four tests cover antipodal sign, midpoint, extrapolation and near-identical copy. Tests pass; these are semantic checks, not live/native final pose validation. No Bevy integration or stage completion claim. Next recover matrix-to-quaternion and normalization routines, then integrate blend into saved-state pose oracle. Game may remain in menu.

### 2026-10-08 — matrix quaternion extraction and float32 normalization
MCP recovered140aecd40 four branches: positive trace, dominantX/Y/Z including tie decisions; half constant14173c670=bytes0000003f. Added jade_matrix_quaternion.py with float32 branch arithmetic and14009bae0 normalization norm order(y*y+x*x)+z*z+w*w, float32 sqrt result/reciprocal/products. Rejects degenerate/nonfinite inputs; does not remove scale or orthogonalize. Three tests cover all branches/sign-equivalent rotations, translation independence, zero norm rejection.
Updated jade_pose_blend final normalization to this recovered float32 arithmetic. Four existing blend tests pass. Host sin/acos remains numerical; native exception/transcendental bit parity unproven.
probe_matrix_quaternion.py tests saved sequence160742:295distinct unscaled world/local matrices. Matrix->quaternion->matrix maximum basis error world5.37763356e-7/local5.67391810e-7, zero skipped. This validates reconstruction of these saved rotation bases, not native quaternion output or final animation blend/tracking parity. Report stage43-matrix-quaternion-roundtrip.json.
Stage4.3 remains in progress; next integrate matrix blend into pose oracle with explicit operand/weight provenance, then tracking. Game not needed for this static step.

### 2026-10-08 — transition operands and saved channel blend probe
1409cd5e0 dispatches slots using component high byte low nibble. Slot0 points component70 (primary); saved scratch copies its evaluated linked locals. Slot1 points78 (transition), evaluates channels then calls140aed7b0(destination scratch,current linked local,saved primary,weight). Weight read through transition+8 link -> link+8 state array -> first state+4 auxiliary_f32. Instance signed byte57<0 suppresses this blend. Thus pointer presence alone is not active transition evidence; callback3 follows local writeback.
Added probe_transition_pose.py unique ordered-header source matching and independently sampled channels. Only intersects channels present in both clips, with explicit skips; never seeds missing input using final captured output. Captured154401 activeflags0301, primary7100B0E8,transition7100B5A4,weight0.4266183078. Against actual linked local:9/21rotations and20/21positions within1e-5. Worst basis discrepancy0.5768589 slot14; several nontracking slots mismatch. Therefore full transition reconstruction remains unvalidated; unsupported source channel semantics/state read timing/other writes require investigation. Do not attribute all differences to tracking.
155659flags0101 activates only primary; probe correctly rejects two-clip blend although transition pointer/resource are present. Earlier18/21primary matches consistent with inactive transition, not proof of crossfade parity. Saved sequence lacks transition state; cannot act as full transition oracle. Report154401-transition-pose.json preserved separately from single-clip reports. Next verify channel interpolation endpoints/native mutable state and pose scheduling before runtime integration. Game can staymenu.

### 2026-10-08 — native segment rotation and pose consistency
MCP140b482f0 confirms current/next frame branch: zero ticks/missing next/no-interpolation flag hold current; elapsed>=float32(ticks/60) selects next; interior fraction float32(elapsed/duration) passed140aecfd0. Quaternion channel interpolation uses dot order(y*y+x*x)+z*z+w*w, shortest sign, clampdot1, epsilon14173c1f0, sine weights and14009bae0 normalization. Added jade_rotation_channel.py direct native segment state with four tests; alternate endpoint/matrix/time-remap branches reject. Updated transition probe to use this rotation consumer.154401 remains9/21rotations and20/21positions; float32/time reconstruction correction does not explain large residuals. Parent/reference conversions and other native writes remain relevant unsupported branches, not claimed as implemented.
Added jade_clip_consistency.py and full collector pose_consistency: whole state arrays before/after bones for both clips, link/resource headers, instance headers and component prefix compare. Three tests prove second-track changes and resource switches are detected despite unchanged first track. Collector syntax passes. Checks are consistency filters, not atomic frame proof; not live-run yet. Prepared source headers/state retained for analysis; slow payloads still deferred.
Old154401 has no before/after checks; saved128sequence has primary only and no transitions/gates. Need a fresh loaded-scene capture with new checks to distinguish live-read skew from channel/reference pipeline mismatch. User must leave menu; no input automation. Stage4.3 remains in progress, no final pose or Bevy parity claim.

### 2026-10-08 — fresh consistent primary pose162528 and target branch
User confirmed loaded scene. Readonly capture162528:47bones,pose window2.4944ms; component prefix, both full state arrays, link/resource descriptors and both instance headers unchanged across pose read. These filters improve evidence but do not prove atomic callback inputs. Activeflags0101 means primary2600313F only; retained transition260006DF inactive.88primary+724transition decoded payload keys exact,812total,noneunverified. Fixed copies162528-runtime-clip-candidates/runtime-sampled-pose/tracking-target-hierarchy preserve provenance.
Primary ordinary pose42tracks excluding2actor-root:18/21rotations and21/21positions match1e-5. Actual-local residuals onlyslot9=.09851181,slot10=.05178129,slot20=.35078256. Hierarchical positions roles0/1/12 exact. Targetgate allows target, resolved role0_position target(78.99535370,9.80328655,4.66432381),strengthargument.0166015625. Therefore zero-target-only writer is not applicable to this snapshot.
MCP1409b3b20 target branch uses normalized(target-rebuiltrole0worldposition), yaw/pitch relative actor-forward. If parameter5 enabled and desired yaw outside limits expanded by14173c468=.17453294, it falls back to rebuilt forward; pitch offset applies only accepted target branch. Added jade_tracking_desired.py explicit resolved/pre-correction inputs; phase/VM and prior world not inferred. Secondary role1 targetyaw/3 by default, parameter7 fulltarget overrides parameter8 rebuilt yaw. Secondary12 targetyaw/5. Constants verified bytes00004040@14173cb3c and0000a040@14173cbd0. Seven branch/distribution tests,56tracking tests total pass.
Game may remain menu. Next integrate resolved-target branch with explicit prior world and native phase decision; single final pose does not supply prior correction input. Full writer/Bevy/native parity remains unproven. Stage4.3 in progress.

### 2026-10-08 — resolved-target tracking matrix pipeline
Moved shared writer body to jade_tracking_step.py. Integrates role0_desired (resolved target, phase decision, target yaw guard and pitch offset), secondary_desired (parameter7/8 and optional12 distribution), tracking_corrections, world yaw/pitch/directional basis and local restoration12->1->0 with parent recomposition. jade_tracking_zero_target.py retains explicit zero-target entry point; both existing zero-target tests still pass.
Added3integration tests: accepted target yaw distributes1/3 and1/5, blocked phase returns rebuilt forward, behind target chooses yaw fallback. All verify input nodes unmodified and original local translations preserved.59tracking tests pass. This is synthetic semantic validation, not observed native pose parity. No scales, near-horizontal role1 special path, VM/phase decisions or bundled CRT bit precision inferred. Caller supplies actual pre-correction locals and stored world inputs; post-correction snapshot162528 cannot independently establish those inputs or their age.
Next: obtain frame/callback scheduling evidence for stored bone-world inputs, add provenance-aware trace replay; no final Bevy integration or stage4.3 completion yet. Game not needed for current static scheduling investigation.

### 2026-10-08 — stored world publication and update-pass ordering
Ghidra MCP1409cc8a0 includes local evaluation/blend, callback140b29720(actor,3) at1409cd45d, then indexed palette1409ce210 at1409cd52e.1409ce210 publishes actor_world*palette to bone+10 when signed updateflags>=0 (scale normalization conditional). This is proven static order for this combined helper; only DATA xrefs to1409cc8a0 found, so its execution for Sally is NOT assumed.
Observed direct caller routes:1409adf00 calls1409cd5e0 at1409ae43b after several1409ac510 passes and callback2;1409ce910 calls it at1409ce95c.1409cd5e0 blends local matrices then callback3;1409ac510 explicitly updates linked object+10=parentworld*local using parent traversal/visited byte33. These facts distinguish stored world from rebuilt local hierarchy; they do not establish each stored matrix's frame age at Sally callback.
Added probe_palette_world.py saved publication relation.162528all47bones checked: actor*palette matches captured world exactly, zero basis/position error, no scale/negative-update skips. Report162528-palette-world.json. This is output-storage agreement, not native input chronology or tracking parity.
World-update-pass counter DWORD1419a1480 has only xref1409ae449 READ_WRITE; listing confirms INC dword after actor local callback pass in1409adf00. Collector now records counter before/after pose read with equality and caveat: not proven unique rendered/gameplay frame. Syntax checked; new counter fields not live-run. No automatic input or new game capture performed.
Next use update-pass marker alongside full mutable clip-state checks in temporal capture; prior-world age/callback trace still needed before native tracking oracle. Stage4.3 remains in progress, game may staymenu.

### 2026-10-08 — palette-only routes and temporal input provenance
MCP callers of1409ce4e0:1409b1f00 at1409b20e7 and140a853c0 at140a8567c. Both can rebuild linked actor world before palette pass. In1409ce4e0 initial evaluation/callback occurs only componentlowbyte==0 withprimarypresent; otherwise publishes palette without this callback. Snapshot162528component0101 would skip initial callback in this helper, but no execution trace proves which route ran.1409ce910 local-only pass has DATA xref only; do not infer runtime invocation.
Added jade_pose_scheduling.py explicit candidate predicates from1409adf00/1409ce910 and palette initialization gate;3semantic tests pass. Predicates do not replace unported scheduler or assert snapshot path execution.
Temporal collector now records update-pass counter before/after, component equality, full primary state/link/resource/instance consistency, actor-owned brain block and resolved VM target reference/current phase flags. Brain and targetstorage rechecked, no writes. Older captures lack these fields; analyzer distinguishes available checks and fully checked samples, never treats absent checks as success. Blocked target table and transition state not recorded, so targetgate/active-transition traces remain incomplete. Syntax checked; enhanced collector has not live-run. No final tracking parity claim.
Static route analysis complete for these helpers. Next needs short loaded-stationary sequence to observe pass boundaries/world changes with strengthened markers. Stage4.3 remains in progress; user input needed only to leave menu for capture.

### 2026-10-08 — temporal capture163738
User confirmed loaded stationary scene.128readonly samples over0.5063654s. Fullprimary state arrays identical in all128, instance/header/link/resource/component/brain/target checks stable. Update-pass counter620875->620905 (30increments),31distinct beforevalues;7reads crosspassboundary atindices2/23/48/52/73/102/119.121samples pass all recorded consistency checks; equal checks do not prove atomic callback inputs. Pose windows0.8932..2.3260ms.
One world pose and one primary state array across series;44headers uniquelymatch2600313F,activecomponent0101. Actor stationary(80.00891113,9.91706467,2.80000997); phaseflags12; owned VM targetresolvesSallyself. Brainoffset(-.81355047,-.53103513,.23693295),strength.05,word84010000. Globaldelta varies across passes. This demonstrates update-pass marker rejects reads missed by unchanged clip state, but provides no changing pose to identify world input age. Do not infer game paused: updatepass continues.
Analyzer now records passdelta/crossingindices/distinctfullstatearrays. Source and analysis stage43-tracking-sequence-20261008-163738*.json retained. No finaltracking orBevyparity proved. Next discriminating native recording requires deliberate pose/movement changes with temporal input provenance; stationary oracle cannot resolve scheduling. Game maystaymenu until requested. Stage4.3 remainsinprogress.

### 2026-10-08 — motion trace preparation
Temporal sampler now prepares retained transition alongside primary before bone reads; records both header-only clips and transition state/link/resource/instance checks. Primary raw header captured before and compared after. Final update-pass marker moved after checks/header reads (previous early marker did not bracket them all). New --start-delay0..10s and --interval-ms0..50;samplelimit256 and5secondcapturelimit retained. Suggested motion run256samples,10msinterval,3sstartdelay; no game input or writes.
Added jade_trace_consistency.py explicit rejection reasons: absent/changed primary/component/brain/target/header/pass checks, unsupported active slots, active-transition missing/changed checks. Adjacent-update-pass pair is only a candidate; no inferred previous callback input, skippedpass/changedactor/target reject. Four tests cover missing checks, transition gaps, DWORDwrap, skippedpasses. Pass;sampler/analyzer syntaxpass. Analyzer exposes motion qualification/reasons and candidateindices separately from older basic check counts. Old163738lackprimaryheadercheck and must not be promoted to qualified motion evidence.
Need user movement during upcoming capture: loaded safe scene, after readiness confirmation move/turn gently for8..10seconds. Collector will start after3seconddelay, record about3seconds; user controls input. Fulltargetgate blockedtable/transitionphase metadata remains incomplete; no finalnativepose/Bevyparityclaim. Stage4.3 in progress.

### 2026-10-08 — motion capture164240: ordinary rotation crossfade oracle
User confirmed and controlled Sally movement. Readonly sequence256samples3.3507386s,214worldposes,198positions,194primary state arrays.201updatepassincrements,219unchangedpasses,217motion-qualifiedsamples. Detected37passcrossings,15statechanges,17componentchanges,2linkchanges,11primaryheaderchanges; transition state/headerchanges also flagged. Four primary header candidates2600055F/260004C1/7100B1C3/7100B0E9. Target reference remained Sallyself,brain198variants. Game can staymenu.
Added probe_motion_pose.py qualified source-channel/transition comparisons against actual linked locals, excluding root tracks and tracking slots9/10/20. Unique source headers required. Active transition uses transition-current first/savedprimary second and firststateauxiliary_f32 weight.24qualifiedsamples skipped for unsupported channel segments (21transition,3primary);193samples evaluated. Seven clip combinations present; detailed per-slot rows retained.
Ordinary rotations:primary-only2754/2754within1e-5(max4.90077323e-7);activecrossfade720/720(max4.43449342e-7),3474checkedtotal. This validates restricted ordinary rotation/interpolation/crossfade on this trace, not all clips or full pose.
Positions:primary2601/2754,transition680/720. All193positionfailures are slot0; excluding slot0 all3281positionsmatch(max5.96046448e-8). Slot0 actor/reference conversion not yet reproduced. Keep failures visible, not reclassify them as proved matches. Roottracking/unsupportedsegments/scales/transcendental bitparity/Bevy integration remain unvalidated. Earlier154401differentclips/unsynchronised snapshot not invalidated solely by this result.
Source164240.json, analysis164240-analysis.json and motion-pose report retained. Next static recover slot0 reference translation, then replay tracking with explicit stored-world input provenance. Stage4.3 notcomplete.

### 2026-10-08 — float32 positions and slot0 root/reference investigation
Added jade_translation_channel.py native segment interpolation140b49fb0 with float32 linear/quadratic/cubic operation order, boundary/hold semantics; explicit time-remapping/alternate-endpoint/mirrored-curve unsupported branches reject.2tests pass. Used in shared channel and motion probes. All3281positions excluding slot0 nowexact(error0) on193evaluated motion samples;3474rotation matches unchanged.
Slot0 restricted cancellation(bodytranslation-roottranslation) with sampled identity rootrotation matches190/193within1e-5,maxerror1.55093148e-5. Raw193slot0failures remain visible; cancellation is narrow diagnostic, not general root/reference reconstruction. No parameter fitting.
Important provenance distinction:1409bbd60 sets3470=instance+10, but primary1409bd3b0 sets3470=140032490(actor). MCP140032490 returnsnullwithoutactorbit26, elseactorworldpointer+88 ifbit16, +44otherwise. Trial treating primary header+10 as reference failed strongly; removed invalid route assumption from probe. Saved164240does not include actor reference block or componentB4 height, so exact primary slot0 conversion cannot be reconstructed from it. Native140b49fb0 composes reference*inverseactor, transforms position, adds componentB4 whenactorflag2.
Temporal collector now captures selectedactorreference68bytes with before/after comparison and componentB4 from preparedcomponentprefix. Syntaxchecked, newfieldsnotlive-run. Need later fresh motion capture for general reference/slot0oracle; can continue statictracking provenance first. Stage4.3 inprogress; game maystaymenu.

### 2026-10-08 — tracking input audit and complete primary trace preparation
Added audit_tracking_trace.py:164240has156qualified adjacent-update-pass pairs,111primary-only,5primaryresource-switch pairs. All156lack actorreference matrix/check,B4height,roles,trackingglobals,currentphasecontrol,AFcounter/B2gate. Adjacent pass evidence cannot establish exact native callback input age; no synthetic final-pose substitution used. Audit report164240-tracking-input-audit.json.
Temporal collector now retains roles fromcomponent68, current phase controlword24, AF/B2, actual signaxis1420b0b98, strengthmultiplier14173ccac,7global limitoverrides and bounded rawblocked-target table. Rechecks globals/roles after reading, selected actorreference checked too. All files privateunderrebge. Collector syntax passes; extended fields notlive-run. Active transition phase lookup and otheractorrole0 still require explicit capture/support. No native tracking parity claim.
Next needs new short user-controlled movement capture with completed primary inputs, then conditional previous-pass replay and comparison. Rootreference actor accessor from32490 alreadyproven; no reason to reuse invalid primaryinstance+10. Stage4.3 inprogress.

### 2026-10-08 — capture165629 extended inputs and slot0 reference probe
User performed movement;256readonlysamples3.4764521s,222worldposes,208passincrements,201motionqualified,145adjacentpasscandidates/130primaryonly. Missing required input audit counts nowempty. Actorreference unchanged201samples;trackingglobals/roles unchanged256. These checks are not atomic callback proof.
New trace ordinary rotations3222/3222primary and216/216transition match1e-5;max5.58182365e-7. Positions excluding slot0 all3247EXACT.10qualifiedsamples skippedunsupported channel segments;191evaluated.
Added jade_actor_reference.py native no-scale inverseactor/reference composition/vector float32 ordering plus explicitB4height;2tests pass. Slot0 actorreference branch:primary159/176within1e-5,max1.57356262e-5; active transition0/12,max1.9764905. Therefore applying actor reference identically to both transition operands is disproved on this trace. Do not promote slot0 to solved or adjust tolerance to hide differences. Full native reference route/input timing remains unresolved; actor linked/scaled branch rejected.
Raw position failure metric retained alongside conditional actorreference and identityrootcancel metrics. Identityrootcancel186/191(max1.14440918e-5) is diagnostic, not general conversion. Source/analysis/inputaudit/motionpose165629reports retained. Next static transition reference selection and small primary conversion/input-order discrepancy, then tracking replay. Stage4.3 stillinprogress; game maystaymenu.


### 2026-10-08 — transition reference selection, trace165629
Ghidra MCP refreshed 1409bbd60: DAT_1420c3470 = transition instance +0x10. In the captured active transition, this 68-byte matrix has flags0x6; primary instance +0x10 has flags0 and is not a valid raw reference matrix. Primary accessor and transition instance routes must remain distinct.
probe_motion_pose now checks actor-reference primary plus transition-instance reference before position blending. On 165629, 11/12 transition slot0 positions match tolerance1e-5; maximum1.1852942407131195e-5 (previous shared actor reference:0/12,max1.97649). Ordinary3438 rotations and3247 positions remain matched. Reference validity restricted to flags2+4, no scale8; captured post-update matrices do not establish callback-input timing. Remaining small primary/transition error unresolved; no full pose parity.
Saved MCP evidence: stage43-transition-reference-evaluator.json, stage43-reference-affine-product.json, stage43-reference-raw-product.json. Raw product140ae9420 confirms three float products plus translation; swapping first two additive terms does not change binary rounding. Next inspect inverse/reference refresh arithmetic and tracking callback input timing; game not required yet.


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


2026-10-08: user requested pause. Saved explicit checkpoint docs/RESUME.md; no new game recording or input. Resume stage4.3 with manual movement capture after return.


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


184441 readonly collector smoke check after adding second-phase metadata:256samples, no capture errors. See transition-phase-field-check.json for counts; this recording is not active transition evidence unless dual slots present.
{"active_flags": {"257": 256}, "phase_checks": 256, "distinct_poses": 1}


### 2026-10-08 — second-phase evidence, Rust channels, corrected tracking target
184552:192 qualified poses (157primary/35blend),45/45 secondary-phase consistency checks. Flags12/44 all allow bit4. Ordinary2826 rotations and blend630 rotations match (max3.99e-7/5.01e-7);3264nonroot positions EXACT. Primary root156/157,transition reference34/35 within1e-5;small residuals remain. Transition clock27/27active+counters EXACT,26ratios EXACT. Tracking phase148/148counter comparisons agree,including28transition pairs;counter evidence does not prove native writer execution or strength.
Rust animation/tracking_phase.rs andchannels.rs now implement phase gating and decoded local rotation/translation sampling. Full cargo test --offline -- --include-ignored:14/14PASS. Private walking fixture2880 rotations matches tolerance1e-5 and nonroot positions EXACT;local blend684 max5.9604645e-8. These modules remain numerical core,not ECS skeletal playback;primary clip advancement/root/tracking/skin integration incomplete.
MCP140e02760 invokes140b33020 for role0 target position. Re-read140b33020 confirms current linked local hierarchy composition,not stale child world position. Corrected both replay probes to use linked_target_position on reconstructed current ordinary nodes. Preserved old reports as180728/181411-before-target-hierarchy.json. Conditional intermediate replay now48/48 and30/30rotations match,max1.6987324e-6/1.5497208e-6;all78positions EXACT. Existing hierarchy tests5PASS. Sequential observations and template inputs still conditional;not callback-entry/full tracking parity. This resolves prior four idle role0 residuals,not independent walking root-reference residuals.
190347fresh sequence:256samples,one actor position,phaseflags8/control32784;203qualified260006DEposes.3654ordinary rotations match,max9.76e-8;3451nonroot positions and203root reference positions EXACT. Fast190431:1189observations but0qualifying ordinary-to-tracking events. Frozen actor/ineligiblephase is not walking tracking validation. Next intervention: active scene and gentle manual walk/stop~2s each for15seconds to obtain qualified active tracking publication boundary. No automatic input. Stage4.3 IN PROGRESS.


### 2026-10-08 — movement190657 and clip-aware fast collector
User manually walked/stopped.256samples,233stable markers;185qualified poses150primary/35blend.2700ordinary+630blend rotations match max4.07e-7/4.77e-7;3145nonrootpositions EXACT. Rootprimary143/150,max1.52752e-5;transitionreference33/35,max1.18613e-5. Clock26/26flags+counters,25/25ratios EXACT. Trackingcounter141/141matches,27transitionpairs. Rootprecision residuals remain.
Fast1907131138observations only55stable primary states;clip7100B2E4 switched during capture. Primary-source pose165comparisons only6ordinarylocals;0qualifiedtrackingevents. This is missing valid input chronology,not new arithmetic failure.
Collector now refreshes instance/link/resource/states/count after clip switches and writes immutable clip_catalog plus per-row resource. Metadata resource/link rechecked before catalog admission. New split_tracking_order_clips.py retains contiguous runs (A->B->A stays3runs),rejects state-length mismatch or changed actor identity;2regression tests PASS.
190919 live collector smoke:502observations,oneclip7100B5B0,one contiguous run;0qualifiedtrackingevents. Clip switch branch NOTliveverifiedyet. No automatic game input,no writes/injection. Need next active walking interval (steady walking~15s,no sharpturn/run/jump) for intermediate tracking boundary capture. Stage4.3 remains IN PROGRESS;ECS integration notclaimed.


### 2026-10-08 — walking tracking191037: input lifetime audit
Fast1910371106observations,4contiguous clip runs7100B5A4/7100B0E8/7100B5E3/7100B1C3. Clip switch metadata handling LIVE exercised successfully. Walking run003 supplies3ordinary-to-corrected events,9diagnostic rotations:3within1e-5,maxerror.002594657;9positions EXACT.
Audit shows actor_world changes between ordinary observation and corrected/repeated publications in ALL3events;some corrected reads also have unstable inputs/pass. New jade_tracking_window.py retains errors but marks0stable-input-window comparisons. Do not call this a validated writer regression or accept the3fitting cases as proof. Existing reconstruction uses actor world sampled too early for these windows;native callback-entry chronology unresolved.2window tests PASS.
MCP1409cd5e0 explicitly brackets140b29720(actor,3) with global14210c150=1 then0;dispatcher runs native callbacks and VM scripts. Marker identifies wholecallback3scope,not unique eye-follow entry. Collector now records marker before/after and rechecks actorworld68bytes after the row. py_compile passes.191344live502rows smoke verified added fields;singleclip/static scene,notmovingvalidation.
Next active-scene capture can use callback3marker to distinguish postblend scope and moving actor lifetime;ordinary source pose time must not be silently substituted for eye-follow actor input. Root reference precision separate.4.3INPROGRESS;Rust skeletal wiring stillpending.


### 2026-10-08 — callback scope191518 and Rust linked hierarchy
Manual walking fast1915181072observations,4clipruns;markers(0,0)1011,(1,0)32,(0,1)29;0rows whollyinsidecallback3.888actorworldendchecks stable. Walking run003 has1publication event/3diagnostic rotations,nonewithin1e-5(max.00127484),positionsEXACT.0stableinputwindows. Brain offsets,actor reference andactorworld change between ordinary andcorrected samples;not an accepted nativewriter oracle. No tolerance relaxation,no extrapolated parity claim.
Repeated ordinary-to-corrected recordings cannot resolve exact callback inputs merely by more user walking. Need focused callback-entry capture or static reconstruction of prior VM/rootmotion input ordering. Do not request another identical movement loop until capture method changes. Game no longer needed for current offline work.
Added Bevy animation/hierarchy.rs: bounded linked-parent traversal,currentlocal composition,originalworld missing-parent fallback,no-scale nativef32 affineproduct;cyclic/missing/scale branches fail explicitly. Two branch/regressiontests cover staleworldoverride,fallback,rotationorder,rawflag fields andscale/cycles. This is numericalcore,notECSbone/skin wiring or nativeposeproof.
Next offline: link readable Sally skeleton data to native hierarchy representation;keep rootreference/tracking inputs separate and explicit. Before next dynamic tracking validation resolve VM-brain andactor input chronology,not reuse ordinary publication actor as callbackentry.4.3INPROGRESS.

Bevy animation/skeleton.rs now loads private readable gao-parent-links.json,validates uniqueGAOkeys/animation slots,finite matrices,complete links,knownparents/cycles andreturnsparent-firsttopologicalorder. Real extracted48objects/47slots test PASS;sourceflags preservedwithoutinventingliveclonebits. Source skeleton loader andhierarchy core are not ECS/skinnedmesh playback yet.16fullRusttests passed afterhierarchy;addedSallyskeletontestpassed separately. Next offline: bind animation slots to source skeleton and compose source-local poses;world/rootreference/tracking stages mustretain explicit inputs.


### 2026-10-08 — short offline milestone: explicit animation binding
Added bevy/src/animation/binding.rs. Reads animation-binding.json,checks schema/object-list identity against skeleton,unique complete47slot mappings andGAO identity. Maps each clip track tosourcebone index;65535 explicitlyRootOrEvent,never silently mappedto bone0. Unknown/mismatched/duplicate/incomplete mappings rejected.
Realprivateasset integration test loaded ALL214Sallyclips andresolvedeverytrackagainst48objectsource skeleton. Observed trackslots0..23,30,65535. CorruptedGAO-slot identity rejected. Full cargo test --offline -- --include-ignored:18/18PASS. Not autonomousclipclock,ECSboneplayback,skinning,trackingorfullcharacterparity. No livegame capture ormanual input needed this milestone.
Next: compose sampled local poses through resolvedrig,keeping root/events andproceduraltracking separate;then ECSskeletal integration. Current movingtracking input chronology limitation remainsopen.4.3INPROGRESS.


### 2026-10-08 — sparse local pose assembly in Bevy
Added animation/local_pose.rs connecting source rig,binding,clip and explicit per-track segment states. Produces per-bone optional rotation/translation writes,lists unsampled tracks andseparates65535root/event tracks. Missingchannels preserve explicitpriorlocal matrix;no identity/rest/finalnativeoutput silently supplied as missinginput. Native sourceorder permits separate rotation/translation tracks forsame bone. Rootposition here remains sourcechannel space,not actorreference conversion.
Integration compared2880assembled rotationwrites against recorded walking native locals within1e-5;providednonroottranslationwrites EXACT. Also checked unwritten translation/priorlocal preservation. Full cargo test --offline -- --include-ignored:19/19PASS. This is sparse localpose assembly,notcompleteframe/worldpose,ECSskinning orautonomousclipclock.
Next: assemble explicit fullpriorlocal pose and compose parent-first world matrices;validate distinctsource/runtimeflag semantics androotreference conversion beforeECSskin integration. Movingtrackingcallback input chronology stillunresolved.4.3INPROGRESS;no livegame neededthismilestone.


2026-10-08 — PAUSED by user. Updated README,STAGES,CONTEXT,RESUME,MODDING_PLAN andhistorical evidence headers. Current19tests PASS,stage4.3incomplete. No code modifications,livecaptures orgameinput duringpause. Priorcontext/resume/plan archived indocs/history.


### 2026-10-09 — resumed, explicit runtime world hierarchy
Addedhierarchy::compose_tracking_world andworld_pose.rs:bit400000 followslinkedparents independently oftarget-positionbit1;child-to-root accumulationpreservesnativef32association,explicitrootworld,cycles/missing/scaleproductbranchesfail. Outputworldmap doesnotmutate nativegame.
export_bevy_world_fixture.py produced8qualified190347samples/360observedlocal->storedworld comparisons;slots27/28 excludedbyknownmodifier24scope beforecomparison,nofilterbyerror. Rust360comparisons pass1e-5,20/20fullRusttestsPASS. Flagsnotcompared;explicitfinalrecordedlocalsnotordinarysource-onlychannels;nocallbackentry/source->world/renderparityclaim. Knownslot28fullrawhierarchyprobe deviation.06544 independentlyretained,separatemodifierpipeline.
Next explicitpriorlocals+source/runtimeclonemap+rootconversionbeforeconnectingsparseanimatorandworldcomposer/ECSskin. Game notneedednow.4.3INPROGRESS. Pausecheckpoint20261008preservedhistorical.


### 2026-10-09 — explicit actor/root translation core
Addedanimation/actor_reference.rs: no-scale transposeinverse,reference*inverse(actor) relative matrix,nativeXYZsumordering andoptionalB4height;refresh_reference savedactor*inverse(evaluatedroot). Inputs explicit,cannotinferwhich reference/actorpose belongedtonativecallback. Scaleproductbranchesfail.
export_bevy_actor_reference_fixture.py selectedfirst32qualifiedprimaryslot0cases from190347,sourcepositionsfromuniqueclipchannels,observedactor/reference/native localposition;selectionnotbyerror. Rust32/32positions EXACT,rotatedactorrefresh/height/scalerejectiontestPASS. Full22/22RusttestsPASS.
Stationaryprimaryonlyproof;movingrootresiduals~1.5e-5,transitionreferenceselection,inputlifetime androotrotation/referencecompositionremainopen. ModuleisnotyetcoupledtoECSplayback orfull source->worldpipeline. Next explicitpriorlocalstate/runtimeclonemap androotcontexts,preservingmissingchannels beforeworldcomposition. No game needed thisstep.4.3INPROGRESS.


### 2026-10-09 — explicit runtime pose and ordinary channel bridge
Addedruntime_pose.rs: checks48sourceobjects->capturedruntimeaddresses includingexplicitactorrootalias;staticparentmapping validatedagainstnativeclones,doesnotreplace sourceflags withruntimeflags. Transactionalpreparedlocalwrites preservepriornodes,requireexplicitflags, rejectinvalid/scale/destination/parentcontexts.
Restrictedwith_plain_channel_writes connects sampler->mappedlinkedlocal->worldcomposer forcaller-selectedordinarybones. Rootchannels explicitly rejected withoutreferencecontext;rebased/proceduraldestinationsremaincallerresponsibility. Native140b49fb0matrix+40OR2/OR4evidence checkedfromcacheddecomp;outputflagssetaccordingly.
Integrated2720nonrootordinary walking localwrite comparisons pass1e-5rotation,providedpositionsEXACT;source/runtime mapping aliases/wrongparents/scales/rootcontext rejected. Worldcomposer runsafterwrites,butwalkingnativeworldparityNOTtestedbecauseotherinputsareexplicitstationarytemplate. Full23/23RusttestsPASS. NoECSanimation orfullstate-machine/runtimeparityclaim.
Nextcomplete root/reference rotation/context thenexplicitframe pipeline,ECSintegration. Userrequestsautonomousordinarywork,notifyonlywheninput/gameattentionneeded.4.3INPROGRESS.


### 2026-10-09 — root basis/context, forward clocks and palette
Rootreference basis140ae9870 read fromcachedGhidra,ordinary140b49fb0 root path selectsrelative reference via reference*inverse(actor). Addedbasis-onlynativeoperationordering/identityflagcopies,RootReferenceContext andruntime rootwritewith explicitactor matrix/parent.32stationaryrootpositionsEXACT/32basiscomparisonswithin1e-5;identityflagrawstorage branchtestpassed. Fullmoving/transitionrootparitystillopen.
GhidraMCPdecompiled140b272a0 andreadcallers. 1409bbd60scalesglobaldelta ((speedbyte(instance+2)*delta)/60),thenrestoresglobal. Usingunscaledglobalfailed5334ordinarycomparisons;applyingobservedbyte56 gives5250EXACTstates. Remaining84aretwoall-trackcontrollerrootepochs(69->70,204->205),excludedbyindependentfirstrootclockdrop,notoutputerror.
Addedtrack_clock.rs restrictedforwardtransform-onlyclock:outgoingkeyexactboundary,flags4,overflow/explicitterminalbehavior,boundedzero-durationtraversal. Root/evententrykeys,auxrestarthelper,clipcontrollerrestartsunsupported. Fixture5250nativeframeindex/elapsed/stateflags EXACT;2root epochsrecorded separately. No autonomousfullclip/controllerstate-machine claim.
Addedskin_palette.rs inverse(actor)*postproceduralworld;47nativepalettes checkedwithin1e-5,lowflags6agree. Snapshot172956usedoffline,notlivepointers. Vertexdeformation/bind/renderingstillseparate. Full27/27RusttestsPASS.
Newprobe_clip_epochs.py identifies2oldrootdrops;residualcandidateerror<=2.3283e-10. Oldrecords lackcomponentAArepeatandB8delta. Fullsequencecollector now retainsalreadyread/checkedAA..B5/B8/speedbyte;py_compilePASS,newfieldsliveunverified. Need freshmanualsteadywalking10s afterready to observecontrollerrestart phase/repeat/delta;THIS IS CLOCK-EPOCH validation,notrepeat offailedtrackingentrytest. No automaticinput.
Allordinarycode saved.4.3INPROGRESS;ECSskeletal/skinplayback notwired. Nextrequiredmanualgamecaptureforclockrestartmetadata,thenstaticcontroller resetbranch+frameintegration.
`n2026-10-09 — W/S capture 023957: 256 samples, 241 stable markers; AA..B5/B8 live verified. 13 root drops with exact residual, two repeat increments; controller identification open. Nonroot positions3162 exact; rotations2304/2322 primary and1023/1026 transition. Clocks47/47, ratios44/44, phase146/146. Handoff docs/HANDOFF.md and AGENTS.md saved; RESUME refreshed. Rust unchanged; ECS parity not claimed.
# 2026-10-09 — explicit moving/transition root basis

probe_root_rotation.py keeps every qualified sample, independent source ID,
observed primary accessor/secondary instance+10 reference and actor matrix.
023957-root-rotation.json:129/129primary and57/57transition basis comparisons
within1e-5. Previously raw rotation comparison failed21slot0cases; reference
composition explains those failures without changing tolerance or ordinary
interpolation. Native actor_reference Rust regression consumes all186cases:
maximum1.013279e-6;28/28testsPASS. Sequential post-update input limitation
remains; root positions and fullframe/ECS parity are not established.

Readonly Ghidra chain1409bd3b0→140b28660→140b27970 recovered. Primary controller
incrementsAD on root completion, unscales remainder `(remaining*60)/speed`,
handles phase repeat threshold/next phase and dispatches again. Root-special
clock has epsilon14173c1f8 bytesacc52737; terminal index entry resets elapsed/index
foraux!=255, whileaux255 invokes140b27b90 active-state reset. Entryframebit4 invokes
140b27eb0 reference copy/callback; not a clock-only side effect. Both repeat
snapshots leave eventtrack44 atindex4 while transform states restart. Root source
flags128 vs runtime132 now explicit in resume audit; flags must not be conflated.
No generic whole-controller reset was added based on this evidence. Next root
clock/controller port needs explicit dispatch gates, phase repeat limits and
reference side-effect inputs. Raw functions and constant read saved privately.

# 2026-10-09 — offline resume audit 4.3

Read HANDOFF/STAGES and relevant transition/context evidence; refreshed readonly
Ghidra1409bbd60/140b28360 into reports/ghidra/raw/stage43-*-resume-20261009.json.
Added tools/jade/audit_resume_sequence.py: SHA256 provenance, unique source
signature mapping, root index/flags/ticks, every existing rotation failure with
primary/transition key context. No fitting or new trace qualification.

Latest023957:11drops without repeat increments are forward root segment
boundaries in26003A36 (indices advance by1, ticks2/3), NOT observed controller
restarts or root loops. Remaining2 are7100B1C3 root0→0 tick40 repeat0→1→2;
exact controller cause remains open. All21rotation failures are slot0:
18primary-only and3transition. Nonroot rotation comparisons in existing report
have no failures; root reference composition has not yet been replayed here.
Audit stored beside capture as -resume-audit.json. Full private Rust validation
27passed/0failed. No Rust runtime changes, no ECS playback or full pose claim.
Next: trace repeat/reset controller separately and reconstruct slot0 reference
basis consumer with explicit primary/secondary contexts. No new game needed yet.

## 2026-10-09 — пользователь подтвердил управление Jade в ангаре

По прямому запросу пользователя зафиксирована рабочая контрольная точка.
`run-hangar.cmd` запускает управляемую Jade в source hangar; source clips,
start/walk/stop/idle, root continuation и dynamic skinning подключены.
Последняя полная проверка: 55 private-inclusive tests PASS; binary собран.
Пользователь лично проверил управление и назвал результат хорошим.

Его наблюдения: отсутствуют анимации быстрого разворота, поворот выглядит
неточным, камера не управляется. Причина camera input issue ещё не проверена;
наличие orbit controls в коде не опровергает наблюдение пользователя.
Steering остаётся приближением; collision/gravity отсутствуют. Плоскость
D90057F2 — вода по сообщению пользователя; translucent blue preview material
не восстанавливает native water shader/reflections/physics.

Обновлены текущие HANDOFF/CONTEXT/STAGES; исторические записи сохранены.
`reports/bevy/user-checkpoint-20261009.json` содержит наблюдения, ссылки на
raw evidence и SHA256 текущего binary/ключевых source files/сцены.
Это документированный baseline, не резервная копия и не закрытие stage4.3.
Следующее: воспроизвести проблему камеры, native fast-turn selection/clips,
уточнить steering; затем контакты с независимыми native доказательствами.


## 2026-10-10 — Ghidra debug/cheat search
Live MCP confirms Cheats/Enabled -> DAT_1419A0279; Global_glob_exec_cheat_mode141234B60 writes six f32 values0.1/0.25/0.5/1/2/5 behind key gates. Sally cheat callback141196030 is MOV EAX,1000;RET. Cheat_Manager_cm_display1413189A0 contains debug-object free movement and position/forward/second-vector bookmark -> request fields global brain486C..48A8; downstream Jade restore and physical controller chord unresolved. Two RSDS bge.pdb references, matching PDB files not found on E:. No established command console. Static inspection only; original/config/live memory unchanged. One Ghidra function definition added for141234B60; executable bytes unchanged. Evidence/limits: reports/ghidra/debug-cheats-investigation-20261010.md; raw debug-*-20261010 responses retained.


## 2026-10-10 — concrete Cheats activation route
Ghidra startup->140AD45F0 confirms BGE.ini;15312BDA0->140AE7D40 loads archive data. Engine.pak BGE.ini extracted; stock has no Cheats section. Bool1409A0A10 accepts1. Concrete gate setting [Cheats] Enabled=1. Prepared private Engine-cheats.pak via tools/jade/prepare_cheat_config.py; all other4payloads exact, header/index roundtrip verified. Installation and running original unchanged; activation still requires replacement/restart and relocated1419A0279 observation. Details: reports/ghidra/debug-cheats-investigation-20261010.md.


2026-10-10: User installed cheat Engine.pak/restarted; candidate SHA256 matches. ReadProcessMemory confirms relocated global1419A0279=01 in PID31636. Global Cheats activation now live-verified; menu/chords/position restoration remain untested. Evidence reports/ghidra/cheats-config/live-flag-pid31636-20261010.json.


2026-10-10 hotkey qualification: root tested Ctrl+NumPad1/4 VK and scan modes; game physical scan buffer sees keys, legacy cheat buffer stays00 and global brainDE4 stays1. Ctrl+NumPad recipe disproved for current runtime; gate remains01. All keys released. Raw reports/ghidra/cheats-config/hotkey-probe-20261010-{004204,004839}.json; details debug-cheats-investigation-20261010.md.


### Cheat input route, 2026-10-10
Fresh Ghidra provider chain and live read-only keyboard bindings establish mode-cycle candidate C held + Tab rising; XInput equivalent LT+Back/Select (not Start). Slot8 is Back bit20, slot9 is Start bit10. Gate1 and initialized bookmark pointers live. No game input performed; readiness required for new mode-cycle block. Raw reports and limitations in reports/ghidra/debug-cheats-investigation-20261010.md. Restore remains unverified, distinct debug object.

### Free camera confirmed by user; pause mechanism qualified statically
User confirms C+Tab. Mode1 suspends category entries with counter/flag, exiting adjusts clock offset; not proven timescale0. Mode2 leaves that block, external camera choice unresolved. Found Jade callback binding restore-position pointer but no reader of its alias; teleport unproven. Updated read-only manager observer records command/mode/pause latch. Evidence debug-cheats-investigation-20261010.md.

### Live cheat cycle0->1->2 confirmed despite map, 2026-10-10
Two authorized C+Tab chords: manager0/0/0->0/1/1->0/2/0, input mapping unchanged. Second screenshot is map: ordinary UI opens alongside actual cheat state transition. Corrects hypothesis that repeated chord does not reach manager. Finally release and ChatGPT focus success; no memory writes. Raw trace cheats-config/mode-cycle-20261010-010817/trace.json. Third chord/teleport not tested.

### Cheat mode2 suppresses movement explicitly
User-qualified exit C+Tab -> Tab -> Tab restores Jade. Fresh Global_glob_exec_joy140D01010 checks Cheat_Managerbrain34==2, zeros movement vectors/strengths, returns. Explains WASD failure independently of pause. Current read-only manager0/0/0. Inventory exit restores VM behavior, exact cheat-mode reset writer unresolved. No new input. Raw/report debug-cheats-investigation-20261010.md updated.
