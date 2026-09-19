# Продолжение работы — Image → Prompt

Обновлено 19 сентября 2026. Этот файл описывает текущее состояние, без устаревших промежуточных статусов.

## Проект и Git

- Рабочая папка: **E:\codex\ai_image**. Открывать её в следующем чате.
- GitHub: https://github.com/sandrgrey/ai_prompt, remote origin, main отслеживает origin/main.
- Последний опубликованный коммит приложения: **b59639c** — исправление замены изображения. UI: 23dde59 и 08f1f87.
- Этот документ обновлён после b59639c; актуальный статус публикации проверять через git status и git log.
- Исходная папка C:\Users\sandr\Documents\ChatGPT\ai_image блокировала запись через Controlled Folder Access. Защиту не отключали; рабочая копия находится на E:.
- Полное исходное ТЗ: C:\Users\sandr\.codex\attachments\99082d82-18a4-41b1-ae7d-bb127510f8ff\pasted-text.txt.

## Реализовано

Локальный pipeline: изображение → JoyCaption → Master Analysis → Qwen/Ollama → Final Prompt для Universal, FLUX, SDXL, Stable Diffusion, Leonardo или Midjourney. Есть negative prompt, JSON-структура, Character DNA, кэш, диагностика, экспорт TXT/JSON, Windows setup/start, валидация изображений и обработка ошибок.

Текущий UI:

- Header 30 px, название и LOCAL в одну строку; лишние заголовки/отступы удалены.
- ANALYZE IMAGE, RE-ANALYZE, GENERATE PROMPT стоят в одном ряду.
- Reconstruction и Include in prompt свёрнуты по умолчанию.
- Final Prompt компактный; «Показать больше / Свернуть» меняет высоту без обрезания данных.
- На широком экране низ поля выровнен с кнопками анализа, Copy / Save — с Target generator.
- Негативный промпт остаётся отдельной вкладкой по желанию пользователя.
- При перетаскивании нового изображения старое заменяется, старые результаты сбрасываются. Исправление в assets/app.js сохраняет File-ссылки до асинхронной очистки Gradio. Пользователь подтвердил работоспособность.

ANALYZE IMAGE создаёт только Master Analysis. GENERATE PROMPT форматирует результат через Qwen; если анализа ещё нет, сначала выполняет его. Смена параметров промпта очищает прежний результат — затем нужна генерация. Пользователь ранее принял это за ошибку, но подтвердил, что всё работает.

## Среда

Python 3.11.16, .venv\Scripts\python.exe; torch 2.10.0+cu126, transformers 5.17.0, Gradio 6.27.0, bitsandbytes 0.50.2. RTX 2060 SUPER 8 ГБ, аппаратного BF16 нет.

JoyCaption: fancyfeast/llama-joycaption-beta-one-hf-llava, веса скачаны в .cache\huggingface. Ollama: localhost:11434, qwen3:4b (восстановлена после обнаружения её отсутствия). Чужие модели и ComfyUI не удалялись.

.env: AUTO, OLLAMA_NUM_GPU=0. AUTO выбирает 4BIT при свободных ≥6.5 ГБ VRAM, иначе CPU; для BF16 требуется поддержка и ≥20 ГБ. При занятой VRAM загрузка сильно замедляется. Не запускать вторую JoyCaption параллельно серверу на этой GPU.

## Проверено

- Последний прогон: **64 Python-теста и 2 JS regression-теста прошли**.
- Реальный браузерный GPU-цикл: JoyCaption 4BIT → Qwen → FLUX/SDXL → TXT/JSON. Загрузка модели ~27.5 сек, анализ ~9.85 сек на синтетической картинке после освобождения VRAM.
- Копирование, JSON STRUCTURE, Character DNA, диагностика и повторное использование vision-анализа проверены.
- Предыдущий CPU-анализ: 276.36 сек. Сохранён в .runtime/smoke/analysis-record.json.
- Отдельный --stage prompts прошёл: FLUX/SDXL, экспорт и сохранение master при недоступной Ollama. Отчёт .runtime/smoke/prompts-report.json.
- Полный --stage all после исправлений заново не выполнялся; не путать это с успешным браузерным GPU-циклом.
- Перетаскивание: тест сначала воспроизвёл ошибку, после исправления прошёл; пользователь подтвердил замену реальным drag-and-drop.

## Текущий запуск

UI: http://127.0.0.1:7860. Последний сервер запущен с логом .runtime/server-drop-fix.log. Наличие процесса/порта проверять заново; PID не фиксировать. Перезапуск очищает сеансы и выгружает модель. Старый .runtime/ai_prompt-source.zip не отражает последние изменения — пользоваться Git.

## Что дальше

- Пользователь хочет менять UI **поэтапно**, убирая лишнее, без самовольной полной переработки.
- Качество промптов пока устраивает; улучшение отложено. Известное замечание: Qwen иногда добавляет в negative слишком общие исключения (background, composition, lighting).
- Отдельно остаются оценка фотографий/портретов, остальных генераторов и адаптивной вёрстки на разных размерах.
- После последующих изменений обновлять документацию, проверять относящиеся к ним сценарии. Отправлять в Git по просьбе пользователя.

## Команды

```powershell
Set-Location E:\codex\ai_image
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/drop_upload.test.cjs
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\check_gpu.py
# Если сервер ещё не запущен:
.\start.bat
```

Node.js нужен только для JS regression-тестов, не для запуска приложения. Перед тяжёлым smoke проверить процессы/VRAM и не дублировать работающую модель.

## Карта файлов

- app.py, ui.py, assets/style.css, assets/app.js — запуск, UI, стили, drop-fix.
- config.py — env и настройки.
- core/joycaption_engine.py, model_manager.py, vision_engine.py — vision и режимы.
- core/service.py, image_utils.py — pipeline, кэш, изображения.
- core/ollama_client.py, prompt_engine.py, schemas.py, prompts/ — текстовая модель и шаблоны.
- core/export.py, diagnostics.py — экспорт и диагностика.
- tests/, scripts/smoke_test.py — автоматические и реальные проверки.
- README.md, docs/verification.md, docs/implementation-plan.md — инструкции, доказательства и план.

Общаться по-русски, кратко. Пользователь требует Context7 для вопросов API/библиотек. Не приравнивать HTTP 200 или загрузку модели к завершённому inference.
