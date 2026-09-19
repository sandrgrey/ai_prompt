"""Run from any working directory: python scripts/check_gpu.py."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Settings
from core.diagnostics import diagnostics
from core.model_manager import detect_hardware, select_mode


def main():
    settings = Settings.from_env()
    settings.configure_environment()
    report = diagnostics(settings)
    try:
        report['recommended_mode'] = select_mode(settings.joycaption_mode, detect_hardware())
    except Exception as exc:
        report['device_selection_error'] = str(exc)
    from core.ollama_client import OllamaClient
    client = OllamaClient(settings)
    report['ollama'] = client.status()
    client.close()
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
