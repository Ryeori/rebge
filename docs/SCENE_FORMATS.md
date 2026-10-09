# Статический срез ангара Jade Anniversary

Выбрана сцена `D90057F0`, `00_01_home_sas_hangar`. Источник — пользовательский Resources.pak. Отображение проверено в локальном WebGL viewer. Это статический экспорт для следующей стадии Bevy; игровая логика, анимация, точное освещение и правила видимости не реализованы.

## Подтверждённая цепочка

- WOW loader `1409b6150`: `.wow`, версия 3, имя в диапазоне 16..79, матрица 80..147, пять ссылок с offset 208. Сцена содержит 302 записи в `D90057EF`.
- GAO list loader `153509980`: записи key32 + `.gao`, stride 8.
- GAO loader `1409ea250`: версия +4, flags +12; native матрица начинается +28 (16 float32 + uint32 flags), затем bounding-volume block. Блок BV начинается +100; размер 24 без bit19, 48 с bit19. Геометрия и материал для flags12+14 — первые два key32 следующего блока; после них три word32 и count*4.
- Object dispatch `140a39860`: type32 + legacy metadata length32 + metadata, затем тело. Geometry type1 reader `140a30a00`; LOD type8 reader `140a40590`.
- Type1: counts vertex/color/UV/submesh, legacy word, auxiliary flag и mask. Vertex positions float32x3, затем legacy normals float32x3 на вершину. Color words и UV float32x2. Заголовки submesh 40 bytes; triangle records `6H2I`, 20 bytes. Границы и индексы проверены. Extended header `1542eec90` и skin blocks поддержаны. Unknown gaps и tail сохраняются при read/write round trip.
- Type8: после общего заголовка byte count, legacy byte и шесть byte thresholds; далее count ключей. Preview выбирает первый непустой LOD; переключение по расстоянию пока отсутствует.
- Material type4 `154638380`: count32 и ссылки на другие материалы. Type5 `154634d20`: восемь word32 тела, затем связанная цепочка слоёв по 20 bytes с texture key в +16. Preview использует первый слой. Семантика submesh selector и дополнительных material flags ещё требует проверки в renderer.
- Texture `140a081e0`: `uint16 14`, пять uint32 (variant, stream_count, unknown, primary_size, secondary_size), byte alpha и uint32 levels; всего 27 bytes. Выбор первой длины: alpha ? primary : secondary. Variant5 применяет выбранную длину ко всем потокам. Данные потоков, variant extension и footer идут последовательно.
- Footer `140a06750`: 32 bytes, width16 +8, height16 +10; три последних magic words `CAD01234`, `00FF00FF`, `C0DEC0DE`. Первая текстура интерпретируется как BC1/BC3 по flag и размеру. DDS/Pillow декодирование проверено тестом известного красного BC1-блока и визуальным просмотром оригинальных текстур. Preview ограничен 1024px; другие потоки ещё не применяются.

## Полученный срез

91 объект с геометрией, 173 draw batches, 73 875 треугольников. Прочитаны 61 уникальный type1 mesh и 10 LOD-ресурсов. Декодированы 46 связанных текстур; 34 уникальных текстуры используются текущими draw batches. Остальные объекты сцены могут быть служебными, логическими или иметь пустые visual keys; число 302 не означает 302 видимых меша.

Все прочитанные известные mesh fields заново сериализованы поверх сохранённых unknown gaps; байты совпадают. Контейнеры текстур реконструированы из header, streams, extension и footer без потерь. Большие bounds включают служебную геометрию: preview пока не применяет native active/visibility flags. Это не доказательство ошибочного масштаба и не основание произвольно отбрасывать объекты.

Матрицы и исходные единицы сохранены без масштабирования. Z-up согласуется с визуальным кадром настила и ограждений. Физическое соотношение единиц с метрами и соответствие исходной камере пока не измерялись; точное сравнение с native frame остаётся необходимым до переноса физики.

## Пространственные и collision records

`1409e9e60` читает grids `D9006AA6` / `D9005818`. Dimensions int16 по +40/+42, массив cell uint32 начинается +60; обе таблицы имеют 10×10 cells и размер 460 bytes. Key по +8 ведёт к отдельному списку; его callback `153d18040`. Семантика cell offsets и использование для collision/culling пока не доказаны.

GAO flags `0x600` направляют ресурс в `1409e7a50`, затем первый key в `1409e7f30`. В выбранной сцене найдены:

- `D9005D4A` → `D9005D5A` → `D0000F4B`: две записи kind2, по четыре float32.
- `3D0030FF` → `3D003DA2` → `3D003D9E`: одна запись kind2, четыре float32.

Ссылки локализованы обратным разбором version2 tail: 20-byte RGBA/word, 20-byte native legacy fields, variable-length skipped payload; проверены единственность кандидата и существование обоих ключей. Shape header: два byte, два legacy byte, 16-byte таблица, затем записи с four-byte header, extra-length32, extra bytes, legacy byte и kind-specific floats (kind1:6, kind2:4, kind3:5). Найденные записи kind2 проходят exact consumption и read/write round trip. Названия sphere/box/capsule и активность примитивов не объявляются доказанными без поведенческого oracle стадии 4.

## Ограничения

Texture `27000502` — container12; его анимированный/специальный маршрут не поддержан. Пользователь 2026-10-09 идентифицировал красную плоскость object `D90057F2` как воду ангара. First-layer texture `8F00109F` материала type5 `0C018705` сама по себе не воспроизводит водный shader. Source export сохранён; объединённый playable preview использует explicit `preview_water` с полупрозрачным синим tint. Это приближение; native lighting, normal/material auxiliary streams и специальные эффекты не восстановлены. Полный collision solver не реализован.

Evidence: `hangar-export-validation.json`, `hangar-spatial-validation.json`, `hangar-mesh-validation.json`, `jade-world-inventory.json`, `scene-resource-census.json`. Полные Ghidra выводы — TEMP/rebge-*.json. Извлечённый контент и preview — TEMP/rebge-assets/stage2-hangar, вне репозитория.

Community reference: [JadeStudio Texture sources](https://github.com/4g3v/JadeStudio/tree/master/JadeStudio.Core/FileFormats/Texture). Старый reader описывает palette/TGA aggregate и не был принят за спецификацию Anniversary texture14.
