import platform
from importlib import metadata


def diagnostics(settings, vision=None):
    result = {'python': platform.python_version(), 'joycaption_model': settings.joycaption_model,
              'joycaption_status': getattr(vision, 'status', 'Not loaded'),
              'quantization_mode': getattr(vision, 'mode', settings.joycaption_mode),
              'ollama_model': settings.ollama_model, 'ollama_num_gpu': settings.ollama_num_gpu,
              'hf_home': str(settings.hf_home), 'offline': settings.local_files_only}
    for package in ('torch', 'transformers', 'accelerate', 'bitsandbytes', 'gradio', 'Pillow'):
        try:
            result[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            result[package] = 'Not installed'
    try:
        import torch
        result.update(cuda_available=torch.cuda.is_available(), cuda_version=torch.version.cuda,
                      gpu='', total_vram_gb=0, free_vram_gb=0, allocated_vram_gb=0)
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            result.update(gpu=torch.cuda.get_device_name(0), total_vram_gb=round(total / 2**30, 2),
                          free_vram_gb=round(free / 2**30, 2),
                          allocated_vram_gb=round(torch.cuda.memory_allocated() / 2**30, 2),
                          bf16_supported=torch.cuda.is_bf16_supported(including_emulation=False))
    except Exception as exc:
        result['torch_error'] = str(exc)
    return result
