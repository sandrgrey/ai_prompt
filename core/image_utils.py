from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


@dataclass
class PreparedImage:
    image: Image.Image
    sha256: str
    name: str


def prepare_image(path: str | Path, max_side=2048, max_pixels=40_000_000) -> PreparedImage:
    if not path:
        raise ValueError('Загрузите изображение JPG, PNG или WEBP.')
    path = Path(path)
    try:
        if path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError('Файл больше 50 МБ. Уменьшите изображение.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Поддерживаются только JPG, JPEG, PNG, WEBP.')
                if source.width * source.height > max_pixels:
                    raise ValueError(f'Изображение превышает лимит {max_pixels:,} пикселей.')
                if getattr(source, 'n_frames', 1) > 1:
                    raise ValueError('Используйте статичное изображение, не анимацию.')
                source.load()
                oriented = ImageOps.exif_transpose(source)
                if 'A' in oriented.getbands() or 'transparency' in oriented.info:
                    rgba = oriented.convert('RGBA')
                    image = Image.new('RGB', rgba.size, 'white')
                    image.paste(rgba, mask=rgba.getchannel('A'))
                else:
                    image = oriented.convert('RGB')
        # Hash original normalized pixels before thumbnail: changed images never alias
        # merely because downsampling erased the difference.
        digest = hashlib.sha256(f'RGB:{image.width}x{image.height}:'.encode())
        digest.update(image.tobytes())
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return PreparedImage(image, digest.hexdigest(), path.stem)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('Не удалось прочитать изображение: повреждено, слишком велико или недоступно.') from exc
