# Подключаемый runtime pack

`asset-packs/stage43-runtime` — независимый asset root для --assets/REBGE_ASSETS.
Scene paths: scenes/sally-hangar/scene.json и scenes/sally-playback/controlled-scene.json.
Общий embedded bank: scenes/sally-playback/controlled.json;38textures.
Геометрия, rig/materials/clip channels находятся в JSON.

```powershell
python tools/assets/export_runtime_pack.py --source assets --output asset-packs/stage43-runtime
python tools/assets/export_runtime_pack.py --check-pack asset-packs/stage43-runtime
```

41 payload files, около170MiB плюс manifest. Source/payload SHA256, dependency closure,
нормализация provenance сохранены в manifest. Абсолютные provenance paths в копиях заменены
на project-relative; runtime поля не изменены. Проверка не требует исходной library.

Library assets/ не удаляется/не заменяется. При новых экспортах заново создать и проверить pack.
Локализация, все214clips отдельно, аудио/Ghidra/recordings не включены.
Private Rust tests пока используют полную local library. Оригинальный игровой контент
хранится отдельно от source repository.
