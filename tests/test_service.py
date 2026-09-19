from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
import pytest

from config import Settings
from core.service import ApplicationService
from core.vision_engine import AnalysisOptions
from core.prompt_engine import PromptOptions
from core.export import export_results


class CountingVision:
    def __init__(self):
        self.calls = 0

    def analyze(self, image, options):
        self.calls += 1
        return f'A red rectangle on white paper. Analysis {self.calls}.'


class Formatter:
    def generate(self, master, options):
        return {'prompt': f'{options.generator}: {master}', 'negative_prompt': ''}


def test_one_image_three_formats_uses_one_vision_call(tmp_path):
    path = tmp_path / 'test.png'
    Image.new('RGB', (32, 32), 'red').save(path)
    engine = CountingVision()
    service = ApplicationService(Settings(), vision=engine, prompt_engine=Formatter())
    for name in ('FLUX', 'SDXL', 'Leonardo'):
        record = service.analyze(path, AnalysisOptions())
        assert service.generate(record, PromptOptions(generator=name))['prompt'].startswith(name)
    assert engine.calls == 1
    service.analyze(path, AnalysisOptions(), force=True)
    assert engine.calls == 2
    service.analyze(path, AnalysisOptions(max_new_tokens=128))
    assert engine.calls == 3
    Image.new('RGB', (32, 32), 'blue').save(path)
    service.analyze(path, AnalysisOptions())
    assert engine.calls == 4


def test_simultaneous_cache_misses_do_not_duplicate_inference(tmp_path):
    path = tmp_path / 'test.png'
    Image.new('RGB', (16, 16), 'red').save(path)
    engine = CountingVision()
    service = ApplicationService(Settings(), vision=engine, prompt_engine=Formatter())
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.analyze(path, AnalysisOptions()), range(2)))
    assert results[0].master == results[1].master
    assert engine.calls == 1


def test_failed_analysis_not_cached(tmp_path):
    path = tmp_path / 'test.png'
    Image.new('RGB', (16, 16)).save(path)
    class FailingOnce(CountingVision):
        def analyze(self, image, options):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError('OOM')
            return 'A black square.'
    engine = FailingOnce()
    service = ApplicationService(Settings(), vision=engine, prompt_engine=Formatter())
    with pytest.raises(RuntimeError):
        service.analyze(path, AnalysisOptions())
    assert service.analyze(path, AnalysisOptions()).master == 'A black square.'
    assert engine.calls == 2


def test_export_only_explicit_and_paths_cannot_escape(tmp_path):
    path = tmp_path / 'test.png'
    Image.new('RGB', (16, 16)).save(path)
    settings = Settings(output_directory=tmp_path / 'outputs')
    service = ApplicationService(settings, vision=CountingVision(), prompt_engine=Formatter())
    record = service.analyze(path, AnalysisOptions())
    assert not settings.output_directory.exists()
    record = replace(record, image_name='../../CON:<evil>')
    result = service.generate(record, PromptOptions(generator='FLUX'))
    paths = export_results(settings, record, result, {'subjects': []}, {}, 'txt')
    assert paths
    for saved in paths:
        assert settings.output_directory in __import__('pathlib').Path(saved).parents
        assert __import__('pathlib').Path(saved).exists()
    json_paths = export_results(settings, record, result, {'subjects': []}, {}, 'json')
    import json
    data = json.loads(__import__('pathlib').Path(json_paths[0]).read_text('utf-8'))
    assert data['master_analysis'] == record.master
    assert data['result']['generator'] == 'FLUX'
