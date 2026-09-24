"""
Watermark preparation, loading, serialization, and reconstruction utilities.
"""

from pathlib import Path
from typing import Tuple, Union, Dict, Any
import cv2
import numpy as np

from .payload import (
    load_watermark_image,
    serialize_watermark,
    deserialize_watermark,
    unpack_header,
)


def create_default_watermark(path: Union[Path, str], size: Tuple[int, int] = (128, 128)) -> np.ndarray:
    """
    Generate a clear, high-contrast watermark image containing 'JND' logo
    and save it if it does not already exist.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    w, h = size
    img = np.full((h, w, 3), 245, dtype=np.uint8)

    # Draw border
    cv2.rectangle(img, (2, 2), (w - 3, h - 3), (40, 20, 180), 2)
    cv2.circle(img, (w // 2, h // 2), min(w, h) // 3, (220, 230, 255), -1)

    # Draw centered text 'JND'
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.5, w / 150.0)
    thickness = 2
    text = "JND"
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    tx = (w - text_size[0]) // 2
    ty = (h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), font, font_scale, (40, 20, 180), thickness, cv2.LINE_AA)

    cv2.imwrite(str(path_obj), img)
    return img


def load_watermark(
    source: Union[Path, str, np.ndarray],
    size: Tuple[int, int] = None,
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Load an arbitrary watermark image from file path or numpy array.
    If size is specified, resizes it; otherwise preserves original dimensions.

    Returns:
        watermark_img: 2D or 3D numpy array.
        orig_dims: Tuple of (original_width, original_height).
    """
    img, info = load_watermark_image(source)
    orig_w, orig_h = info["width"], info["height"]

    if size is not None and (orig_w, orig_h) != size:
        resized = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
        return resized, (orig_w, orig_h)

    return img, (orig_w, orig_h)


def watermark_to_bits(watermark_img: np.ndarray) -> np.ndarray:
    """Legacy helper: Convert 2D binary watermark image {0, 1} into a 1D bitstream array."""
    return watermark_img.flatten().astype(np.uint8)


def bits_to_watermark(bits: np.ndarray, size: Tuple[int, int] = (32, 32)) -> np.ndarray:
    """Legacy helper: Reshape 1D bitstream into a 2D image."""
    expected_bits = size[0] * size[1]
    if len(bits) < expected_bits:
        raise ValueError(f"Not enough bits ({len(bits)}) for watermark of size {size} ({expected_bits} bits).")

    watermark_2d = bits[:expected_bits].reshape(size)
    return (watermark_2d * 255).astype(np.uint8)
