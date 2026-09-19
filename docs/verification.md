# Проверка реализации

Проверки перед первой публикацией:

- Python 3.11.16, PyTorch 2.10.0+cu126, Transformers 5.17.0, Gradio 6.27.0.
- Чистое `.venv`; зависимости установлены, `pip check`: No broken requirements found.
- `pytest -q`: 64 passed. Проверка syntax/import через compileall прошла.
- Приложение запущено, GET http://127.0.0.1:7860/ вернул HTTP 200.
- NVIDIA GeForce RTX 2060 SUPER, 8 ГБ: CUDA доступна, BF16 аппаратно не поддерживается, AUTO выбирает 4BIT.
- Тесты проверяют изображения, EXIF/RGB, SHA-256, кэш, одновременные запросы, JSON repair, Ollama errors, UI state, export, OOM recovery.
- Qwen3 4B реально выполнила FLUX (~29 сек) и SDXL (~12 сек) из тестового описания, включая negative prompt. Character DNA корректно вернула пустые характеристики для геометрических фигур.
- Официальные веса JoyCaption полностью скачаны. Первый прогон загрузил модель на GPU; законченный результат vision inference не был получен до прерывания сессии. **Полный end-to-end GPU smoke пока не подтверждён.**
- После этого исправлены исключения квантования vision tower/projector для путей модулей Transformers 5; добавлен regression-тест.

Воспроизведение полного прогона:

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\check_gpu.py
.venv\Scripts\python.exe scripts\smoke_test.py --stage all
```

Smoke создаёт собственное геометрическое изображение и проверяет JoyCaption → FLUX/SDXL, TXT/JSON export, работу без Ollama и число vision-вызовов. Результаты — `.runtime/smoke/`.

Исходная папка Documents защищена Windows Controlled Folder Access. Проект создан в `E:\codex\ai_image`; настройки защиты не изменялись.
