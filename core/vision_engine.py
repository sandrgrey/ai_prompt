from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class AnalysisOptions:
    max_new_tokens: int = 768
    temperature: float = 0.6
    top_p: float = 0.9
    do_sample: bool = False

    def __post_init__(self):
        if not isinstance(self.max_new_tokens, int) or not 32 <= self.max_new_tokens <= 4096:
            raise ValueError('max_new_tokens: 32–4096')
        if not 0 < self.temperature <= 2 or not 0 < self.top_p <= 1:
            raise ValueError('temperature: (0, 2]; top_p: (0, 1]')


class VisionEngine(ABC):
    @abstractmethod
    def analyze(self, image: Image.Image, options: AnalysisOptions) -> str:
        """Return a visual description; do not persist the image."""
