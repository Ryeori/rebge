# План реконструкции BG&E Anniversary на Bevy

Статус: работа возобновлена по просьбе пользователя, 2026-10-09. Текущая подстадия 4.3 не завершена.
Установка: E:/SteamLibrary/steamapps/common/Beyond Good and Evil - 20th Anniversary Edition.
Проект: C:/Users/Dan/Desktop/rebge. Движок оригинала Jade, native x64; точная ревизия неизвестна.

Цель: проверяемый собственный исходный код всех игровых систем на Bevy,
редактируемые оригинальные ассеты и совпадение поведения с оригиналом.
Это критерий итоговой приёмки, а не текущая готовность или восстановленный исходный код разработчиков.

Актуальный план стадий: STAGES.md. Готово/не готово: CONTEXT.md.
Точка возобновления: RESUME.md. История и доказательства: MODLOG.md,
STAGE4_REVERSE.md, STAGE43_ANIMATION_TRANSITIONS.md.

Ближайшее: sparse local writes -> full explicit local pose -> world hierarchy/root references -> ECS skeletal playback/skin.
Затем движение/коллизии, камера и управляемый персонаж в сцене; далее игровые системы и расширение покрытия.
Извлечённые данные и анализ приватные, не публиковать. На паузе не проводить live captures.
