from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from dataclasses import asdict, dataclass, replace
from threading import RLock

from config import ROOT, Settings
from .image_utils import prepare_image
from .vision_engine import AnalysisOptions

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisRecord:
    image_hash: str
    image_name: str
    master: str
    options: AnalysisOptions
    key: str


class ApplicationService:
    def __init__(self, settings: Settings, vision=None, prompt_engine=None):
        self.settings = settings
        if vision is None:
            from .joycaption_engine import JoyCaptionEngine
            vision = JoyCaptionEngine(settings)
        if prompt_engine is None:
            from .ollama_client import OllamaClient
            from .prompt_engine import PromptEngine
            prompt_engine = PromptEngine(OllamaClient(settings))
        self.vision = vision
        self.prompt_engine = prompt_engine
        self._cache = OrderedDict()
        self._lock = RLock()

    def analyze(self, path, options: AnalysisOptions, force=False) -> AnalysisRecord:
        prepared = prepare_image(path, self.settings.image_max_side, self.settings.image_max_pixels)
        try:
            instruction = (ROOT / 'prompts' / 'analysis.txt').read_text('utf-8')
            key = hashlib.sha256(json.dumps([prepared.sha256, asdict(options),
                self.settings.joycaption_model, self.settings.joycaption_mode,
                self.settings.image_max_side, instruction], sort_keys=True).encode()).hexdigest()
            # Lock covers cache check + inference + insert: concurrent misses compute once.
            with self._lock:
                if key in self._cache and not force:
                    self._cache.move_to_end(key)
                    log.info('Analysis cache hit')
                    return replace(self._cache[key], image_name=prepared.name)
                master = self.vision.analyze(prepared.image, options)
                record = AnalysisRecord(prepared.sha256, prepared.name, master, options, key)
                self._cache[key] = record
                self._cache.move_to_end(key)
                while len(self._cache) > self.settings.cache_size:
                    self._cache.popitem(last=False)
                return record
        finally:
            prepared.image.close()

    def generate(self, record, prompt_options):
        if record is None:
            raise ValueError('Сначала проанализируйте изображение.')
        result = self.prompt_engine.generate(record.master, prompt_options)
        return {**result, 'generator': prompt_options.generator, 'options': asdict(prompt_options)}

    def structured(self, record):
        if record is None:
            raise ValueError('Сначала проанализируйте изображение.')
        return self.prompt_engine.structured(record.master)

    def character(self, record):
        if record is None:
            raise ValueError('Сначала проанализируйте изображение.')
        return self.prompt_engine.character(record.master)

    def diagnostics(self):
        from .diagnostics import diagnostics
        result = diagnostics(self.settings, self.vision)
        if hasattr(self.prompt_engine, 'client'):
            result['ollama'] = self.prompt_engine.client.status()
        result['cached_analyses'] = len(self._cache)
        return result
