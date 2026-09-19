# Image → Prompt · JoyCaption + Qwen

Локальное приложение для Windows 10/11: изображение → подробное описание JoyCaption → Qwen в Ollama → промпт для выбранного генератора. Изображения не отправляются в облако. Ключи и платные API не нужны.

## Быстрый запуск

Откройте терминал в папке проекта:

```bat
setup_windows.bat
ollama pull qwen3:4b
start.bat
```

Откройте **http://127.0.0.1:7860**. Загрузите JPG/PNG/WEBP, нажмите **ANALYZE IMAGE**, затем **GENERATE PROMPT**. Первая загрузка JoyCaption скачивает около 17 ГБ весов. Интерфейс запускается до загрузки модели; прогресс загрузки весов виден в консоли.

При желании скачайте веса заранее:

```bat
.venv\Scripts\python.exe scripts\download_model.py
```

## Запуск с рабочего стола

После установки можно создать ярлык командой PowerShell:

```powershell
.\scripts\create_shortcut.ps1
```

Дважды нажмите **Image to Prompt** на рабочем столе. Запускатель проверяет приложение и Ollama, запускает недостающие процессы без консольного окна и открывает браузер после готовности. Повторный запуск использует существующий сервер. Ошибки показываются отдельным окном; логи запуска — `logs/launcher-app.log` и `logs/launcher-ollama.log`.

Модели должны быть установлены заранее. Закрытие вкладки не останавливает сервер и не выгружает модель. Значок в трее и кнопка завершения пока не реализованы. `start.bat` остаётся вариантом запуска с видимой консолью (Ctrl+C останавливает такой экземпляр). После перемещения проекта пересоздайте ярлык.

## Что установить заранее

1. **Python 3.11 x64** с [python.org](https://www.python.org/downloads/windows/). В установщике включите Python Launcher и Add Python to PATH. Если установлено несколько версий, проверяйте `py -3.11 --version`. Приложение протестируется именно на Python 3.11; Python 3.14 не заменяет его автоматически.
2. **Git** с [git-scm.com](https://git-scm.com/downloads/win) нужен для клонирования/обновления репозитория. Для распакованного проекта и повседневного запуска Git не требуется.
3. **Драйвер NVIDIA** с [сайта NVIDIA](https://www.nvidia.com/Download/index.aspx), совместимый с CUDA runtime выбранного PyTorch. Setup не меняет драйверы и не устанавливает CUDA Toolkit.
4. **Ollama** с [официального сайта](https://ollama.com/download/windows). Запустите приложение Ollama; если сервер не работает, откройте отдельный терминал и выполните `ollama serve`.
5. Около **30 ГБ свободного места** для окружения и весов JoyCaption, дополнительно около 2.5 ГБ для Qwen3 4B. Для 4-bit рекомендуется 16–32 ГБ RAM; CPU-режим требует порядка 40+ ГБ свободной RAM и существенно медленнее.

Проверка:

```bat
python --version
py -3.11 --version
git --version
nvidia-smi
ollama list
```

Если используете `uv`, можно подготовить Python и окружение так:

```bat
uv python install 3.11
uv venv --python 3.11 --seed .venv
setup_windows.bat
```

## Установка вручную

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu126
python -m pip install -r requirements.txt
python -m pip install -r requirements-4bit.txt
copy .env.example .env
python -m pip check
python scripts\check_gpu.py
ollama pull qwen3:4b
python app.py
```

`requirements-4bit.txt` опционален для BF16/CPU, но необходим для небольших GPU. PyTorch wheel включает необходимые CUDA runtime-библиотеки; отдельный CUDA Toolkit для обычного inference не требуется. Setup использует CUDA 12.6 build PyTorch 2.10.0. Для CPU-only установки перед setup задайте `set TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu`.

Не копируйте `.venv` между компьютерами: заново запустите setup. Можно переносить `.cache/huggingface` с весами.

## Модели и совместимость

- **JoyCaption:** `fancyfeast/llama-joycaption-beta-one-hf-llava` — официальный Beta One, не заменён другой vision-моделью.
- **Ollama:** `qwen3:4b` по умолчанию. Можно указать `qwen3:8b` или другую локальную Qwen в `.env`, предварительно выполнив `ollama pull ИМЯ`.
- `OLLAMA_NUM_GPU=0` оставляет Qwen на CPU: JoyCaption остаётся в VRAM, между форматами не перезагружается. При большом объёме VRAM можно поставить `-1`, но тогда нужно обеспечить память для обеих моделей. После запроса Qwen освобождается (`keep_alive=0`).
- Python 3.11; PyTorch 2.10.0+cu126; Transformers 5.17.0; Accelerate 1.15.0; Gradio 6.27.0; bitsandbytes 0.50.2.

Перед реализацией проверены [официальный JoyCaption](https://github.com/fpgaminer/joycaption), [model card](https://huggingface.co/fancyfeast/llama-joycaption-beta-one-hf-llava), [Ollama API](https://docs.ollama.com/api), [bitsandbytes Windows support](https://huggingface.co/docs/bitsandbytes/installation) и [Gradio 6 migration](https://www.gradio.app/guides/gradio-6-migration-guide).

Используется официальный порядок: `AutoProcessor` → `apply_chat_template(tokenize=False)` → processor с изображением → `LlavaForConditionalGeneration.generate`. В новом Transformers аргумент типа данных — `dtype`; старый `torch_dtype` не используется. UI параметры `theme`, `css`, `js` передаются в `launch`, как требует Gradio 6. В upstream приведён пример окружения Transformers 4.51.3; здесь выбран текущий API и его совместимость проверяется реальным smoke-тестом. Не нужны torchaudio, Triton, vLLM, ComfyUI или отдельный сервер vision.

## Режимы памяти

| Режим | Поведение |
|---|---|
| AUTO | BF16 при аппаратной поддержке и ≥20 ГБ свободной VRAM; иначе NF4 при наличии CUDA/bitsandbytes и ≥6.5 ГБ свободной VRAM; иначе CPU |
| BF16 | Полные веса на GPU, без эмуляции BF16; ориентир 24 ГБ VRAM |
| 4BIT | NF4 double quantization текстовой модели; vision tower/projector остаются полноточными, вычисления BF16 или FP16 по возможностям GPU |
| CPU | FP32 в RAM, медленно; не требует CUDA |

Ориентиры не гарантируют, что любой запрос поместится: память зависит от длины генерации, backend и других приложений. Для **RTX 2060 SUPER 8 ГБ**: AUTO/4BIT, Qwen CPU, 512–768 новых токенов. При OOM закройте другие GPU-приложения, сократите токены до 256–512. На GPU с 4–6 ГБ может понадобиться CPU. После изменения `.env` перезапустите приложение.

## Использование

1. Загрузите статичное изображение. EXIF orientation исправляется, прозрачность компонуется на белом фоне, данные преобразуются в RGB. Исходник не изменяется. Ограничение — 50 МБ / 40 мегапикселей; копия уменьшается до 2048 пикселей, затем официальный processor применяет размер входа модели.
2. **ANALYZE IMAGE** создаёт MASTER VISUAL DESCRIPTION. **RE-ANALYZE** принудительно повторяет vision inference. Изменение visual generation parameters также инвалидирует анализ.
3. Выберите Universal, FLUX, SDXL, Stable Diffusion, Leonardo или Midjourney. Переключение формата использует готовый master. Qwen сначала формирует валидированный JSON, затем получает только выбранные категории.
4. Detail: Short ≈50–100 слов, Medium ≈100–200, Detailed ≈200–400, Extreme ≈400–800. Это инструкции модели, а не механическое обрезание текста. Промпты выводятся на английском.
5. Exact не добавляет новых элементов; Close допускает минимальную оптимизацию; Balanced улучшает структуру с сохранением содержания; Creative может усилить художественную атмосферу.
6. Include controls действительно фильтруют факты, передаваемые форматтеру. Для SDXL/Stable Diffusion отрицательный промпт включается по умолчанию при выборе генератора, но его можно отключить. Для Midjourney параметры добавляются только из отдельного пользовательского поля.
7. **JSON STRUCTURE** выводит структурированный анализ, **EXTRACT CHARACTER** — постоянные признаки персонажа и пригодный для копирования CHARACTER PROMPT. Текущие поза, выражение, камера и фон исключаются из входа Character DNA.
8. **COPY PROMPT** копирует финальный промпт. **SAVE TXT / SAVE JSON** сохраняют только по запросу. Повторные экспорты создают новые каталоги и не затирают предыдущие.

Если Ollama недоступен, откройте **Master Analysis**: JoyCaption продолжает работать самостоятельно. Нельзя получить Qwen-форматирование, JSON или Character DNA без локальной текстовой модели.

## Текущий интерфейс

- Интерфейс центрирован на широком экране; максимальная ширина контейнера 1480 px.
- Advanced analysis содержит короткие пояснения параметров в скобках; Temperature и Top P действуют при включённом sampling.
- Шапка высотой 30 px: название и LOCAL в одну строку, без лишних заголовков и верхних отступов.
- ANALYZE IMAGE, RE-ANALYZE и GENERATE PROMPT находятся в одном ряду под изображением.
- Reconstruction и Include in prompt свёрнуты по умолчанию; выбранные значения сохраняются при сворачивании.
- Final Prompt открывается в компактном виде. «Показать больше / Свернуть» меняет высоту, не обрезая текст для копирования и экспорта.
- На широком экране низ компактного поля выровнен с кнопками анализа, а Copy / Save — с блоком Target generator.
- Negative Prompt остаётся отдельной вкладкой. Он заполняется при генерации с включённым Generate negative prompt.
- Новое изображение можно перетащить поверх старого: оно заменяет старое, а результаты предыдущего изображения сбрасываются. Сам файл не сохраняется в outputs автоматически; загрузка хранится во временном кэше Gradio.

Master Analysis — описание изображения от JoyCaption. Final Prompt — результат отдельной генерации через Qwen. Одна кнопка анализа не заполняет Final Prompt. Изменение настроек промпта сбрасывает прежний результат; после этого нажмите GENERATE PROMPT.

## Конфигурация

Скопируйте `.env.example` в `.env`. Переменные окружения имеют приоритет над `.env`.

| Параметр | Значение по умолчанию |
|---|---|
| JOYCAPTION_MODEL | fancyfeast/llama-joycaption-beta-one-hf-llava |
| JOYCAPTION_MODE | AUTO |
| OLLAMA_URL | http://127.0.0.1:11434 |
| OLLAMA_MODEL | qwen3:4b |
| OLLAMA_NUM_GPU / OLLAMA_TIMEOUT | 0 / 600 секунд |
| MAX_NEW_TOKENS / TEMPERATURE / TOP_P | 768 / 0.6 / 0.9 |
| DO_SAMPLE | false (temperature/top_p применяются при true) |
| OUTPUT_DIRECTORY | outputs |
| HF_HOME | .cache/huggingface |
| LOCAL_FILES_ONLY | false |
| GRADIO_HOST / GRADIO_PORT | 127.0.0.1 / 7860 |
| IMAGE_MAX_SIDE / IMAGE_MAX_PIXELS | 2048 / 40000000 |
| CACHE_SIZE | 16 текстовых анализов |

Относительные пути считаются от папки проекта. `HF_HOME=E:/models/huggingface` позволяет хранить веса на другом диске. Можно задать локальную папку весов в `JOYCAPTION_MODEL`.

После успешного скачивания поставьте `LOCAL_FILES_ONLY=true`: загрузчик использует только кэш, даже без проверки обновлений Hugging Face. После загрузки модели inference всегда локальный. Веса загружаются один раз на процесс, runtime-переключение режима не поддерживается.

## Приватность

HTTP сервер и Ollama ограничены loopback. Share/tunneling отключены. Cloud-модели Ollama запрещены; HTTP-клиент не использует proxy environment и не следует redirect. Внешние API inference, ключи, telemetry и внешние шрифты не используются.

Gradio технически создаёт **временную локальную копию upload** в `.runtime/gradio`. Она очищается через `delete_cache` (проверка каждые 10 минут, возраст 1 час); это не экспорт исходника. После аварийного завершения оставшийся временный каталог можно удалить при остановленном приложении. Результаты в памяти ограничены кэшем и состоянием вкладки, после перезапуска исчезают. В `outputs` ничего не пишется до SAVE. В лог не записываются изображения, master или полный пользовательский prompt; технический traceback ошибок пишется в `logs/app.log` с ротацией.

## Структура

```text
app.py, ui.py, config.py          запуск, UI, настройки
core/
  vision_engine.py              интерфейс и AnalysisOptions
  joycaption_engine.py          единственный JoyCaption + OOM handling
  image_utils.py                проверка, EXIF/RGB, SHA-256
  model_manager.py              политика AUTO/BF16/4BIT/CPU
  service.py                    orchestration и ограниченный кэш
  ollama_client.py               локальный HTTP transport
  prompt_engine.py, schemas.py   форматирование, фильтры, JSON validation
  export.py, diagnostics.py      явный экспорт и диагностика
prompts/                        анализ, 6 форматов, JSON, Character DNA
assets/style.css, assets/app.js  стили и исправление замены изображения
scripts/                        setup/start/check_gpu/download_model
tests/                          unit/integration boundaries
outputs/                        только явные экспорты
docs/                           план и результаты проверки
setup_windows.bat, start.bat     команды из корня
requirements*.txt, .env.example зависимости и пример настроек
```

## Проверки

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
.venv\Scripts\python.exe scripts\check_gpu.py
```

Результаты проверок и ограничения тестовой машины зафиксированы в [docs/verification.md](docs/verification.md). Unit-тесты используют подмену тяжёлых vision/HTTP границ и сами по себе не доказывают успешный GPU inference. Реальный браузерный цикл JoyCaption 4BIT → Qwen → FLUX/SDXL → экспорт подтверждён; ограничения качества и детали проверки приведены в отчёте.

## Troubleshooting

- **Python не найден / выбрана 3.14:** установите 3.11; используйте `py -3.11`, создайте новое `.venv`. Не удаляйте другую версию Python.
- **Windows не позволяет создать файл в Documents:** Controlled Folder Access может блокировать процессы Python/Codex. Используйте рабочую папку вне защищённых Documents, например `E:\codex\ai_image`; не требуется отключать Defender.
- **CUDA False:** проверьте драйвер `nvidia-smi`, активное `.venv` и установку CUDA wheel. Строка CUDA в nvidia-smi показывает возможности драйвера, а не вариант установленного PyTorch.
- **bitsandbytes import/kernel error:** проверьте `python -m bitsandbytes`; установите `requirements-4bit.txt` и совместимый CUDA PyTorch. Ошибка показана в логах; можно выбрать CPU. AUTO проверяет доступность пакета и архитектуру, но не гарантирует работу всех binary kernels до первого inference.
- **CUDA OOM:** модель остаётся доступной для повторного запроса, временные тензоры освобождаются. Уменьшите токены/закройте другие GPU задачи; затем попробуйте 4BIT или CPU. Запуск Qwen на GPU вместе с JoyCaption особенно требователен к памяти.
- **Ollama unavailable:** запустите Ollama, проверьте `ollama list`, `OLLAMA_URL`, затем `ollama pull qwen3:4b`. Master сохраняется и работает без Ollama.
- **Ollama timeout:** увеличьте `OLLAMA_TIMEOUT`, выберите меньшую Qwen. CPU-генерация значительно медленнее GPU. Проверка статуса ограничена 5 секундами.
- **JSON invalid:** производится одна попытка ремонта; если ошибка сохраняется, повторите запрос или выберите более сильную Qwen. Неверный JSON не выдаётся как успешный.
- **Модель не скачивается:** проверьте интернет и свободное место на диске `HF_HOME`. Повторный download продолжает кэш; не включайте LOCAL_FILES_ONLY до завершения загрузки.
- **Порт 7860 занят:** остановите другой экземпляр или смените `GRADIO_PORT`.
- **Описание неточное:** JoyCaption может ошибаться в количестве объектов, лево/право, текстах, небольших деталях и фотопараметрах. Exact уменьшает допустимые домыслы инструкцией, но не гарантирует абсолютную точность. Оценки объектива/фокусного расстояния должны оставаться неопределёнными; проверьте результат вручную.

### Проверка перетаскивания для разработчиков

```bat
node --test tests/drop_upload.test.cjs
```

Для этой проверки нужен Node.js; для обычного запуска приложения он не требуется. Тест моделирует потерю доступа к файлам нативного drop-события после его обработки. `assets/app.js` сохраняет ссылки на файлы синхронно до асинхронного обработчика Gradio, сохраняя штатную загрузку и валидацию.
