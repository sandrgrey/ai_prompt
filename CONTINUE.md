# Передача контекста — Image → Prompt

Обновлено: 19 сентября 2026. Пользователь просит продолжить работу в другом чате.

## Где находится проект

- **Рабочий проект: `E:\codex\ai_image`. Открыть эту папку в новом чате.**
- Исходная папка чата: `C:\Users\sandr\Documents\ChatGPT\ai_image`. Запись туда блокировалась Windows Defender Controlled Folder Access; там нет рабочей копии приложения. Защиту не отключали.
- GitHub: https://github.com/sandrgrey/ai_prompt
- Ветка `main`, настроен `origin/main`; опубликован коммит `790d348aadffc806c350737edaef3225bc662216`.
- Перед созданием этого документа git status был чистым. Этот документ пока не коммитили и не отправляли.
- Архив исходников: `.runtime\ai_prompt-source.zip` (создан до этого документа).
- Полное исходное ТЗ: `C:\Users\sandr\.codex\attachments\99082d82-18a4-41b1-ae7d-bb127510f8ff\pasted-text.txt`.

## Что сделано

Создано локальное приложение: изображение → JoyCaption → мастер-описание → Ollama/Qwen → промпт для выбранного генератора.

- Тёмный интерфейс Gradio, загрузка JPEG/PNG/WEBP, проверка размеров, EXIF/RGB.
- Режимы Universal, FLUX, SDXL, Stable Diffusion, Leonardo, Midjourney; настройки подробности и точности реконструкции, фильтры категорий, optional negative prompt, пользовательские MJ-параметры.
- Structured JSON с валидацией Pydantic и одной попыткой исправления; Character DNA без сцены/позы/освещения.
- Кэш анализа и генерации, явный повторный анализ, сохранение мастер-описания при недоступной Ollama.
- Экспорт TXT/JSON по действию пользователя, копирование, диагностика.
- AUTO/BF16/4BIT/CPU, обработка OOM; локальные запросы к Ollama, отключение телеметрии.
- Windows setup/start scripts, README, тесты, документация.
- Исправлены исключения квантования Transformers 5: `model.vision_tower`, `model.multi_modal_projector`, `lm_head`; добавлен regression-тест. Реальный GPU inference после исправления ещё не подтверждён.

## Среда

- Python 3.11.16: `.venv\Scripts\python.exe`.
- torch 2.10.0+cu126, transformers 5.17.0, accelerate 1.15.0, bitsandbytes 0.50.2, Gradio 6.27.0.
- RTX 2060 SUPER 8 ГБ; аппаратного BF16 нет.
- Официальная модель: `fancyfeast/llama-joycaption-beta-one-hf-llava`; все 4 шарда (~17 ГБ) скачаны в `.cache\huggingface`.
- Ollama: `http://127.0.0.1:11434`, модель `qwen3:4b` скачана. Чужую установленную `qwen3.8:27b` не изменяли.
- `.env`: AUTO, Qwen на CPU (`OLLAMA_NUM_GPU=0`), timeout 600 сек. AUTO выбирает 4BIT только при свободных ≥6.5 ГБ VRAM, иначе CPU. CPU требует много RAM и работает медленно.
- В последней проверке было свободно лишь ~1.4 ГБ VRAM; не останавливать сторонние ComfyUI/прочие процессы пользователя.

## Что реально проверено

- `pytest -q`: **64 passed**, последняя проверка 19 сентября.
- `pip check`: **No broken requirements found**; compileall проходил ранее.
- Сервер приложения запускался, HTTP GET localhost:7860 возвращал 200. Полная проверка действий в браузере ещё не выполнена.
- Реальная Ollama из вручную заданного мастер-описания выдала FLUX (~29 сек), SDXL (~12 сек) с negative prompt; Character DNA для геометрии корректно пустая. Результат `.runtime\ollama-live.json`.
- JoyCaption ранее загрузилась в 4BIT на GPU, но завершённый анализ изображения не получен до прерывания. **Полный цикл с реальной JoyCaption пока НЕ подтверждён.**
- Последний smoke загрузил модель и начал анализ **на CPU**, а не GPU. Последняя строка `.runtime\smoke-current.log`: `Analysis start mode=CPU max_tokens=384`. Успешного завершения пока нет.

## Процессы на момент передачи

Последняя проверка обнаружила app.py PID 29308 и smoke_test.py PID 9436/22960 (venv launcher и дочерний Python), родитель PowerShell PID 20572. Эти PID могут устареть.

**Сначала проверить существующий smoke и его лог; не запускать второй тяжёлый анализ параллельно.** Процесс мог пережить прерывание чата. Если потребуется остановить зависший тест, сверить командную строку и остановить только принадлежащий этой проверке процесс. Работающие процессы сейчас не останавливали.

## Что осталось сделать

1. Проверить `.runtime\smoke-current.log`, процессы и наличие `.runtime\smoke\all-report.json`. Определить, завершился ли текущий CPU smoke.
2. Получить завершённый реальный анализ изображения JoyCaption. При достаточной свободной VRAM проверить 4BIT после исправления исключений квантования. Не объявлять CPU результат GPU-проверкой.
3. Довести smoke до конца: JoyCaption → FLUX/SDXL через Qwen → TXT/JSON; кэш должен исключать повторный vision-вызов. Скрипт также проверяет сохранение мастер-описания при недоступной Ollama через тестовый порт 11435, не выключая пользовательскую Ollama.
4. Проверить интерфейс в браузере: загрузка, анализ, смена генератора без повторного vision, negative, Character DNA, копирование, экспорт и сообщения ошибок.
5. При обнаружении ошибок исправить причину, добавить релевантный regression-тест, повторить нужные проверки.
6. Обновить `docs\verification.md` и README реальными результатами. Сейчас фраза в verification «AUTO выбирает 4BIT» описывает прошлую проверку при свободной памяти; фактический выбор зависит от VRAM.
7. При публикации исправлений проверить diff, тесты, commit/push и совпадение local/remote SHA. Пользователь ранее явно просил отправить проект в указанный GitHub.

## Команды продолжения (PowerShell)

```powershell
Set-Location E:\codex\ai_image
Get-Content .runtime\smoke-current.log -Tail 30
nvidia-smi
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\check_gpu.py
# Только после проверки, что предыдущий smoke завершён:
.\.venv\Scripts\python.exe scripts\smoke_test.py --stage all
# Запуск UI, если сервер ещё не работает:
.\start.bat
```

UI: http://127.0.0.1:7860

## Карта кода

- `app.py`, `ui.py`, `assets\style.css` — запуск, интерфейс, состояние сессии.
- `config.py` — настройки/env.
- `core\joycaption_engine.py`, `model_manager.py`, `vision_engine.py` — модель, выбор режима, inference.
- `core\service.py`, `image_utils.py` — pipeline, кэш, изображения.
- `core\ollama_client.py`, `prompt_engine.py`, `schemas.py`, `prompts\` — текстовая модель, шаблоны, схемы.
- `core\export.py`, `diagnostics.py` — экспорт, диагностика.
- `scripts\smoke_test.py`, `tests\` — реальная проверка и unit-тесты.
- `docs\implementation-plan.md`, `docs\verification.md` — план и статус.

Общаться по-русски, кратко. Для вопросов API/библиотек пользователь требует Context7: сначала resolve-library-id, затем query-docs. Не считать загрузку модели или HTTP 200 подтверждением полной работоспособности приложения.

## Обновление: GitHub отключён

По просьбе пользователя удалён remote `origin`. `git remote -v` теперь пустой; локальная ветка `main`, история и файлы сохранены. Сведения выше о настроенном origin/main больше не актуальны. Удалённый репозиторий на GitHub не удаляли. Не восстанавливать подключение и не выполнять push без новой просьбы пользователя.

## Проверка 19 сентября: Git снова подключён

По новой просьбе пользователя восстановлен `origin` → https://github.com/sandrgrey/ai_prompt.git и upstream `main` → `origin/main`. При подключении обе ветки указывали на `790d348`.

Обнаружено завершение прошлого vision-теста: `.runtime/smoke-current.log` содержит `Vision passed`, CPU, 276.36 секунды, 133 слова; проверка кэша прошла. Затем тест остановился с HTTP 404 от Ollama: настроенная `qwen3:4b` отсутствовала в текущем списке моделей. Повторные unit-тесты: 64 passed, pip check без ошибок. Начата повторная загрузка `qwen3:4b` и проверка реального анализа через браузер. Эти запуски пока не считать завершёнными; итог ниже будет обновлён после проверки.

## Итог проверки 19 сентября (актуальнее предыдущих разделов)

Git подключён к `sandrgrey/ai_prompt`, main отслеживает origin/main. Qwen3 4B восстановлена. Старый сервер перезапущен с актуальным кодом. Реальный браузерный цикл на GPU **успешен**: JoyCaption 4BIT, загрузка 27.50 сек, анализ 9.85 сек → FLUX/SDXL → TXT/JSON. Проверены копирование, JSON STRUCTURE, Character DNA и отсутствие повторного vision при смене генератора. Отдельный `--stage prompts` успешно проверил экспорт и fallback при недоступной Ollama. Подробный актуальный статус: `docs/verification.md`.

Осталось улучшить качество negative prompt (Qwen добавляет слишком общие исключения), оценить реальные фотографии/портреты и остальные генераторы. Новый `--stage all` не выполнялся: GPU pipeline проверен через настоящий UI. Не запускать вторую JoyCaption, пока работающий сервер держит модель в GPU. Активный сервер этой проверки пишет `.runtime/server-current.log`, UI localhost:7860. Старые PID выше больше не использовать.
