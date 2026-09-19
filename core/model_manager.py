"""Small, testable device policy. GPU imports happen only when needed."""
from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(frozen=True)
class Hardware:
    cuda: bool
    gpu: str
    total_gb: float
    free_gb: float
    bf16: bool
    bnb: bool


def detect_hardware() -> Hardware:
    import torch

    if not torch.cuda.is_available():
        return Hardware(False, '', 0, 0, False, False)
    free, total = torch.cuda.mem_get_info()
    capability = torch.cuda.get_device_capability()
    return Hardware(True, torch.cuda.get_device_name(0), total / 2**30, free / 2**30,
                    torch.cuda.is_bf16_supported(including_emulation=False),
                    find_spec('bitsandbytes') is not None and capability >= (6, 0))


def select_mode(requested: str, hw: Hardware) -> str:
    if requested == 'AUTO':
        if hw.cuda and hw.bf16 and hw.free_gb >= 20:
            return 'BF16'
        if hw.cuda and hw.bnb and hw.free_gb >= 6.5:
            return '4BIT'
        return 'CPU'
    if requested not in {'BF16', '4BIT', 'CPU'}:
        raise ValueError('Неизвестный режим модели.')
    if requested == 'BF16' and not (hw.cuda and hw.bf16):
        raise ValueError('GPU не поддерживает аппаратный BF16. Используйте AUTO, 4BIT или CPU.')
    if requested == '4BIT' and not (hw.cuda and hw.bnb):
        raise ValueError('4BIT требует CUDA и bitsandbytes. Установите requirements-4bit.txt или выберите CPU.')
    return requested
