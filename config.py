"""Validated, project-relative configuration; no model imports at UI startup."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


def _bool(value: str) -> bool:
    if value.lower() not in {'true', 'false', '1', '0', 'yes', 'no'}:
        raise ValueError(f'Expected true/false, got {value!r}')
    return value.lower() in {'true', '1', 'yes'}


@dataclass(frozen=True)
class Settings:
    joycaption_model: str = 'fancyfeast/llama-joycaption-beta-one-hf-llava'
    joycaption_mode: str = 'AUTO'
    ollama_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen3:4b'
    ollama_timeout: float = 600
    ollama_num_gpu: int = 0
    max_new_tokens: int = 768
    temperature: float = 0.6
    top_p: float = 0.9
    do_sample: bool = False
    output_directory: Path = ROOT / 'outputs'
    gradio_host: str = '127.0.0.1'
    gradio_port: int = 7860
    hf_home: Path = ROOT / '.cache' / 'huggingface'
    local_files_only: bool = False
    image_max_side: int = 2048
    image_max_pixels: int = 40_000_000
    cache_size: int = 16

    def __post_init__(self):
        if self.joycaption_mode not in {'AUTO', 'BF16', '4BIT', 'CPU'}:
            raise ValueError('JOYCAPTION_MODE: expected AUTO, BF16, 4BIT or CPU')
        parsed = urlparse(self.ollama_url)
        if (parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {'', '/'}):
            raise ValueError('OLLAMA_URL must be a local HTTP endpoint (localhost/127.0.0.1/::1).')
        if not self.ollama_model.strip() or 'cloud' in self.ollama_model.lower():
            raise ValueError('OLLAMA_MODEL must name a downloaded local model, not a cloud model.')
        if not self.joycaption_model.strip():
            raise ValueError('JOYCAPTION_MODEL cannot be empty')
        if not 32 <= self.max_new_tokens <= 4096:
            raise ValueError('MAX_NEW_TOKENS must be between 32 and 4096')
        if not 0 < self.temperature <= 2 or not 0 < self.top_p <= 1:
            raise ValueError('TEMPERATURE must be > 0 and <= 2; TOP_P must be > 0 and <= 1')
        if not 1 <= self.gradio_port <= 65535 or self.gradio_host not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('GRADIO_HOST must be loopback and GRADIO_PORT between 1 and 65535')
        if self.ollama_timeout <= 0 or self.ollama_num_gpu < -1:
            raise ValueError('Invalid Ollama timeout or num_gpu')
        if not 336 <= self.image_max_side <= 8192 or not 1 <= self.image_max_pixels <= 100_000_000:
            raise ValueError('Invalid image limits')
        if not 1 <= self.cache_size <= 128:
            raise ValueError('CACHE_SIZE must be between 1 and 128')
        for name in ('output_directory', 'hf_home'):
            path = Path(getattr(self, name)).expanduser()
            object.__setattr__(self, name, (ROOT / path).resolve() if not path.is_absolute() else path.resolve())

    @classmethod
    def from_env(cls, env_file: Path = ROOT / '.env') -> 'Settings':
        values = {**dotenv_values(env_file), **os.environ}
        converters = {
            'ollama_timeout': float, 'ollama_num_gpu': int, 'max_new_tokens': int,
            'temperature': float, 'top_p': float, 'do_sample': _bool,
            'output_directory': Path, 'gradio_port': int, 'hf_home': Path,
            'local_files_only': _bool, 'image_max_side': int, 'image_max_pixels': int, 'cache_size': int,
        }
        kwargs = {}
        for name in cls.__dataclass_fields__:
            value = values.get(name.upper())
            if value is not None and value != '':
                kwargs[name] = converters.get(name, str)(value)
        return cls(**kwargs)

    def configure_environment(self):
        # Set before importing Hugging Face/Gradio. Never enable external telemetry.
        os.environ['HF_HOME'] = str(self.hf_home)
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        os.environ['DO_NOT_TRACK'] = '1'
        os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
        os.environ['GRADIO_TEMP_DIR'] = str(ROOT / '.runtime' / 'gradio')
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
        if self.local_files_only:
            os.environ['HF_HUB_OFFLINE'] = '1'
