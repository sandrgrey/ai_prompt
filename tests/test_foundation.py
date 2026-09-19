import hashlib
from pathlib import Path

import pytest
from PIL import Image

from config import Settings
from core.image_utils import prepare_image
from core.model_manager import Hardware, select_mode
from core.vision_engine import AnalysisOptions


def test_image_is_rgb_oriented_and_original_unchanged(tmp_path):
    path = tmp_path / 'photo.png'
    image = Image.new('RGBA', (80, 40), (255, 0, 0, 128))
    exif = Image.Exif()
    exif[274] = 6
    image.save(path, exif=exif)
    original = path.read_bytes()
    prepared = prepare_image(path, max_side=50)
    assert prepared.image.mode == 'RGB'
    assert prepared.image.size == (25, 50)
    assert path.read_bytes() == original


def test_hash_identifies_pixels_not_filename(tmp_path):
    a, b, c = [tmp_path / name for name in ('a.png', 'b.png', 'c.png')]
    Image.new('RGB', (20, 30), 'red').save(a)
    Image.new('RGB', (20, 30), 'red').save(b)
    Image.new('RGB', (20, 30), 'blue').save(c)
    assert prepare_image(a).sha256 == prepare_image(b).sha256
    assert prepare_image(a).sha256 != prepare_image(c).sha256


def test_rejects_bad_unsupported_and_oversized_images(tmp_path):
    path = tmp_path / 'broken.png'
    path.write_text('not an image')
    with pytest.raises(ValueError):
        prepare_image(path)
    Image.new('RGB', (10, 10)).save(path, format='BMP')
    with pytest.raises(ValueError):
        prepare_image(path)
    Image.new('RGB', (20, 20)).save(path)
    with pytest.raises(ValueError):
        prepare_image(path, max_pixels=100)


def test_settings_env_validation_and_project_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setenv('MAX_NEW_TOKENS', '512')
    settings = Settings.from_env(env_file=tmp_path / 'absent')
    assert settings.max_new_tokens == 512
    assert settings.output_directory.is_absolute()
    assert settings.gradio_host == '127.0.0.1'
    monkeypatch.setenv('MAX_NEW_TOKENS', '-1')
    with pytest.raises(ValueError):
        Settings.from_env(env_file=tmp_path / 'absent')


@pytest.mark.parametrize('url', ['https://example.com', 'http://ollama.com', 'http://localhost.evil.com:11434'])
def test_no_remote_ollama_by_default(url):
    with pytest.raises(ValueError):
        Settings(ollama_url=url)


def test_analysis_options_reject_invalid_values():
    with pytest.raises(ValueError):
        AnalysisOptions(max_new_tokens=0)
    with pytest.raises(ValueError):
        AnalysisOptions(top_p=1.5)


@pytest.mark.parametrize('hardware, expected', [
    (Hardware(False, '', 0, 0, False, False), 'CPU'),
    (Hardware(True, '8GB GPU', 8, 7, False, True), '4BIT'),
    (Hardware(True, '24GB GPU', 24, 22, True, True), 'BF16'),
    (Hardware(True, 'Busy GPU', 24, 3, True, True), 'CPU'),
    (Hardware(True, 'No BNB', 8, 7, False, False), 'CPU'),
])
def test_auto_uses_available_hardware(hardware, expected):
    assert select_mode('AUTO', hardware) == expected


def test_explicit_bf16_not_silently_emulated():
    with pytest.raises(ValueError):
        select_mode('BF16', Hardware(True, 'Turing', 8, 7, False, True))
