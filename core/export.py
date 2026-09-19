"""Explicit, non-overwriting exports; never writes source images."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid


def export_results(settings, record, result, structured, character, format):
    if record is None:
        raise ValueError('Сначала выполните анализ.')
    format = format.lower()
    if format not in {'txt', 'json'}:
        raise ValueError('Ожидается txt или json.')
    name = re.sub(r'[^\w-]+', '_', record.image_name, flags=re.UNICODE).strip('_. ')[:64] or 'image'
    # Always prefix; Windows reserves CON, AUX, NUL, COM1 etc even with extensions.
    root = Path(settings.output_directory).resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    target = root / f'image-{name}-{record.image_hash[:8]}' / f'{stamp}-{uuid.uuid4().hex[:8]}'
    target.mkdir(parents=True, exist_ok=False)
    paths = []

    def write(name, text):
        path = target / name
        path.write_text(text, encoding='utf-8')
        paths.append(str(path))

    if format == 'txt':
        write('master_analysis.txt', record.master)
        if result and result.get('prompt'):
            generator = re.sub('[^a-z0-9_]', '', result.get('generator', 'universal').lower().replace(' ', '_'))
            write(f'prompt_{generator}.txt', result['prompt'])
        if result and result.get('negative_prompt'):
            write('negative_prompt.txt', result['negative_prompt'])
        if character:
            write('character.txt', '\n'.join(f'{k}: {v}' for k, v in character.items()))
    else:
        bundle = {'image_name': record.image_name, 'image_sha256': record.image_hash,
                  'master_analysis': record.master, 'analysis_options': asdict(record.options),
                  'joycaption_model': settings.joycaption_model, 'ollama_model': settings.ollama_model,
                  'result': result or {}, 'structured_analysis': structured or {}, 'character': character or {}}
        write('result.json', json.dumps(bundle, ensure_ascii=False, indent=2))
        if structured:
            write('analysis.json', json.dumps(structured, ensure_ascii=False, indent=2))
        if character:
            write('character.json', json.dumps(character, ensure_ascii=False, indent=2))
    return paths
