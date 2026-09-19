"""Exercise error recovery at the expensive model.generate boundary."""
import torch
from PIL import Image
import pytest

from config import Settings
from core.joycaption_engine import JoyCaptionEngine
from core.vision_engine import AnalysisOptions


def test_transformers5_keeps_vision_and_projector_unquantized():
    from transformers.quantizers.quantizers_utils import should_convert_module
    from core.joycaption_engine import QUANTIZATION_EXCLUSIONS
    assert not should_convert_module('model.vision_tower.vision_model.encoder.layers.0.mlp.fc1', QUANTIZATION_EXCLUSIONS)
    assert not should_convert_module('model.multi_modal_projector.linear_1', QUANTIZATION_EXCLUSIONS)
    assert not should_convert_module('lm_head', QUANTIZATION_EXCLUSIONS)
    assert should_convert_module('model.language_model.layers.0.mlp.up_proj', QUANTIZATION_EXCLUSIONS)


class Inputs(dict):
    def to(self, device):
        return self


class Processor:
    @property
    def tokenizer(self):
        return self

    def apply_chat_template(self, conversation, **kwargs):
        return 'image prompt'

    def __call__(self, **kwargs):
        return Inputs(input_ids=torch.tensor([[1, 2, 3]]), pixel_values=torch.zeros((1, 3, 2, 2)))

    def decode(self, tokens, **kwargs):
        assert tokens.tolist() == [4, 5], 'Prompt input tokens must not leak into output.'
        return 'A detailed red circle.'


def test_oom_does_not_poison_loaded_engine_or_cache(monkeypatch):
    class Model:
        calls = 0
        def generate(self, **kwargs):
            self.calls += 1
            assert 'temperature' not in kwargs, 'Greedy inference must omit sampling-only arguments.'
            if self.calls == 1:
                raise torch.cuda.OutOfMemoryError('simulated GPU OOM')
            return torch.tensor([[1, 2, 3, 4, 5]])

    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    engine = JoyCaptionEngine(Settings())
    model = Model()
    engine.model, engine.processor = model, Processor()
    engine.device, engine.dtype, engine.mode = 'cpu', torch.float32, 'CPU'
    image = Image.new('RGB', (2, 2))
    with pytest.raises(RuntimeError, match='VRAM'):
        engine.analyze(image, AnalysisOptions())
    assert engine.model is model
    assert engine.analysis_count == 0
    assert engine.analyze(image, AnalysisOptions()) == 'A detailed red circle.'
    assert engine.analysis_count == 1
    assert engine.model is model


def test_sampling_parameters_reach_model(monkeypatch):
    class Model:
        def generate(self, **kwargs):
            assert kwargs['temperature'] == 0.35
            assert kwargs['top_p'] == 0.8
            assert kwargs['max_new_tokens'] == 128
            assert kwargs['do_sample'] is True
            return torch.tensor([[1, 2, 3, 4, 5]])

    engine = JoyCaptionEngine(Settings())
    engine.model, engine.processor = Model(), Processor()
    engine.device, engine.dtype = 'cpu', torch.float32
    assert engine.analyze(Image.new('RGB', (2, 2)), AnalysisOptions(128, .35, .8, True))
