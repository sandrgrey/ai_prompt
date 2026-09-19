"""Download official weights only; never reads or uploads a user image."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Settings


if __name__ == '__main__':
    settings = Settings.from_env()
    settings.configure_environment()
    from core.joycaption_engine import JoyCaptionEngine
    print('Downloading JoyCaption weights (about 17 GB). Existing downloads are reused.', flush=True)
    print(JoyCaptionEngine(settings)._model_path(), flush=True)
