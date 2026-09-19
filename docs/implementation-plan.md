# Image → Prompt: план реализации

Спецификация: пользовательское ТЗ, 30 разделов.
Цель: локальный Gradio → JoyCaption → Qwen pipeline на Windows/Python 3.11.

## Решения и интерфейсы

- Один лениво загружаемый JoyCaptionEngine, сериализация GPU-запросов.
- fancyfeast/llama-joycaption-beta-one-hf-llava, AutoProcessor + LlavaForConditionalGeneration.
- AUTO: BF16 на поддерживаемой GPU с запасом памяти, иначе NF4/FP16 или CPU.
- Qwen по умолчанию CPU (OLLAMA_NUM_GPU=0), JoyCaption остается в VRAM.
- SHA-256 нормализованного изображения + параметры + инструкция + модель: ключ ограниченного текстового кэша.
- State отдельной сессии. Смена формата использует master, без vision inference.
- JSON: Pydantic и одна попытка ремонта локальной LLM.
- Изображения не экспортируются; Gradio временно кэширует upload с очисткой.
- Экспорт только кнопками, уникальный каталог на каждый экспорт.
- Никаких внешних API inference, внешних шрифтов или telemetry.

config.Settings: joycaption_model, joycaption_mode, ollama_url, ollama_model, ollama_timeout,
ollama_num_gpu, max_new_tokens, temperature, top_p, do_sample, output_directory,
gradio_host, gradio_port, hf_home, local_files_only, image_max_side, image_max_pixels.

core.vision_engine.AnalysisOptions frozen dataclass(max_new_tokens=768, temperature=.6, top_p=.9, do_sample=False).
VisionEngine.analyze(PIL.Image, AnalysisOptions) -> str.

core.prompt_engine.PromptOptions frozen dataclass(generator='FLUX', detail='Detailed', reconstruction='Exact', include: tuple[str,...], negative=False, mj_parameters='').
Include names: subject, environment, camera, lighting, composition, colors, materials, style.
PromptEngine(client).generate(master, options) -> dict(prompt, negative_prompt).
PromptEngine.structured(master) -> dict. PromptEngine.character(master) -> dict.
OllamaClient(settings).status() -> dict; .chat(messages, schema=None) -> str.

core.service.ApplicationService(settings, vision=None, prompt_engine=None):
analyze(path, options, force=False) -> AnalysisRecord;
generate(record, prompt_options) -> dict; structured(record) -> dict; character(record) -> dict;
diagnostics() -> dict. AnalysisRecord: image_hash, image_name, master, options, key.

core.export.export_results(settings, record, result, structured, character, format) -> list[str].

## Выполненные фазы (актуализировано 19 сентября 2026)

- [x] 1. Python 3.11, чистое .venv, зависимости, диагностика.
- [x] 2. Тесты validation/hash/config/device; JoyCaption/image_utils/model_manager.
- [x] 3. Тест кэша: одна картинка → FLUX → SDXL → Leonardo = один vision call.
- [x] 4–6. OllamaClient, templates, JSON, Character DNA; HTTP failure/repair/filter tests.
- [x] 7–9. Gradio UI, TXT/JSON экспорт, diagnostics, понятные ошибки.
- [x] 10. Windows setup/start, README, pytest, pip check, compileall.
- [x] Реальный smoke: GPU master → Qwen FLUX/SDXL → экспорт; отсутствие Ollama; browser UI.

## Журнал

- Исходная пустая папка Documents заблокирована Windows Controlled Folder Access (Defender event 1123). Работа перенесена в E:\codex\ai_image без изменения защиты.
- Проект опубликован в https://github.com/sandrgrey/ai_prompt, ветка main. Git после временного отключения снова подключён по просьбе пользователя.

## Последующие работы

- [x] Уменьшить header до 30 px, убрать лишние отступы и заголовки.
- [x] Собрать анализ, повторный анализ и генерацию в один ряд.
- [x] Сделать Reconstruction и Include in prompt сворачивающимися.
- [x] Добавить компактный/развёрнутый Final Prompt и выровнять блоки на широком экране.
- [x] Исправить замену изображения через drag-and-drop; автоматические тесты и подтверждение пользователя получены.
- [ ] Позже улучшить качество negative prompt — пользователь отложил работу над качеством.
- [ ] Отдельно оценить фотографии, портреты и остальные генераторы на реальных примерах.

GPU pipeline проверен через браузер; отдельный `--stage all` отчёт не завершён. Детали и границы проверок — в verification.md. Следующие изменения UI делать небольшими шагами по указаниям пользователя.

## Упрощение запуска и последние UI-правки

- [x] Ярлык рабочего стола, скрытый запуск, проверка готовности и повторное использование сервера.
- [x] Автозапуск отсутствующей Ollama и понятное сообщение об ошибках запуска.
- [x] Центрирование на широком экране, пояснения Advanced analysis.
- [ ] Возможный следующий этап: трей и завершение скрытого сервера. Отдельного запроса на реализацию пока нет.
