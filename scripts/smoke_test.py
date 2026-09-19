"""Opt-in real-model smoke test. Generates its own geometric test image.

python scripts/smoke_test.py --stage all
Never run as part of pytest: downloads/loads actual models and performs inference.
"""
import argparse
from dataclasses import asdict, replace
import json
import logging
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['all', 'vision', 'prompts'], default='all')
    args = parser.parse_args()
    settings = Settings.from_env()
    settings.configure_environment()
    logging.basicConfig(level=logging.INFO)
    from PIL import Image, ImageDraw
    from core.service import ApplicationService, AnalysisRecord
    from core.vision_engine import AnalysisOptions
    from core.prompt_engine import PromptOptions
    from core.export import export_results
    folder = ROOT / '.runtime' / 'smoke'
    folder.mkdir(parents=True, exist_ok=True)
    image_path = folder / 'geometric-reference.png'
    if not image_path.exists():
        image = Image.new('RGB', (768, 512), '#f8f3e7')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 350, 768, 512), fill='#d5c4a1')
        draw.ellipse((80, 115, 310, 345), fill='#c93e38')
        draw.rectangle((370, 150, 610, 345), fill='#24528c')
        draw.polygon([(590, 100), (690, 100), (640, 20)], fill='#35825a')
        image.save(image_path)
    service = ApplicationService(settings)
    options = AnalysisOptions(max_new_tokens=384, do_sample=False)
    report = {}
    if args.stage in {'all', 'vision'}:
        started = time.monotonic()
        record = service.analyze(image_path, options)
        report['vision_seconds'] = round(time.monotonic() - started, 2)
        report['mode'] = service.vision.mode
        report['master_words'] = len(record.master.split())
        assert len(record.master) > 40
        again = service.analyze(image_path, options)
        assert again.master == record.master
        assert service.vision.analysis_count == 1
        (folder / 'analysis-record.json').write_text(json.dumps(asdict(record), indent=2), 'utf-8')
        print('Vision passed:', json.dumps(report), flush=True)
    else:
        data = json.loads((folder / 'analysis-record.json').read_text('utf-8'))
        data['options'] = AnalysisOptions(**data['options'])
        record = AnalysisRecord(**data)
    if args.stage in {'all', 'prompts'}:
        for generator in ('FLUX', 'SDXL'):
            started = time.monotonic()
            result = service.generate(record, PromptOptions(generator=generator, detail='Short', negative=generator == 'SDXL'))
            assert result['prompt'].strip()
            if generator == 'SDXL':
                assert result['negative_prompt'].strip()
            structured = service.structured(record)
            paths = export_results(settings, record, result, structured, {}, 'json')
            paths += export_results(settings, record, result, structured, {}, 'txt')
            report[generator] = {'seconds': round(time.monotonic() - started, 2),
                                 'words': len(result['prompt'].split()), 'exports': paths}
            print(generator, 'passed', flush=True)
        if args.stage == 'all':
            assert service.vision.analysis_count == 1
        from core.ollama_client import OllamaClient
        from core.prompt_engine import PromptEngine
        from ui import UIHandlers, Session
        unavailable = replace(settings, ollama_url='http://127.0.0.1:11435', ollama_timeout=2)
        offline_client = OllamaClient(unavailable)
        assert not offline_client.status()['available'], 'Smoke failure port must be unused'
        service.prompt_engine = PromptEngine(offline_client)
        session = Session(record=record, source_path=str(image_path))
        session = UIHandlers(service, settings).run('generate', session, str(image_path), record.options, PromptOptions())
        assert session.record.master == record.master
        assert session.status == 'Ollama unavailable — raw JoyCaption analysis is still available.'
        report['ollama_unavailable_preserves_master'] = True
        offline_client.close()
    (folder / f'{args.stage}-report.json').write_text(json.dumps(report, indent=2), 'utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
