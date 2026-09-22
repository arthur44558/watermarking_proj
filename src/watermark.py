"""
Watermark preparation, binary conversion, and reconstruction utilities.
"""

from pathlib import Path
from typing import Tuple
import cv2
import numpy as np


def create_default_watermark(path: Path | str, size: Tuple[int, int] = (32, 32)) -> np.ndarray:
    """
    Generate a clear, high-contrast binary watermark image containing 'JND' pattern
    and save it if it does not already exist.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    w, h = size
    # Create white canvas with a distinct geometric/text pattern
    img = np.zeros((h, w), dtype=np.uint8)

    # Draw border
    cv2.rectangle(img, (1, 1), (w - 2, h - 2), 255, 1)

    # Draw centered text 'JND'
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.45
    thickness = 1
    text = "JND"
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    tx = (w - text_size[0]) // 2
    ty = (h + text_size[1]) // 2
    cv2.putText(img, text, (tx, ty), font, font_scale, 255, thickness, cv2.LINE_AA)

    # Threshold to strict binary {0, 255}
    _, binary_img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    cv2.imwrite(str(path_obj), binary_img)
    return binary_img


def load_watermark(path: Path | str, size: Tuple[int, int] = (32, 32)) -> np.ndarray:
    """
    Load a watermark image, resize it to `size`, convert to grayscale,
    and threshold to binary values {0, 1}.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        create_default_watermark(path_obj, size=size)

    img = cv2.imread(str(path_obj), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read watermark at: {path_obj}")

    # Resize to target dimension
    resized = cv2.resize(img, size, interpolation=cv2.INTER_AREA)

    # Threshold to binary 0 and 1
    _, binary = cv2.threshold(resized, 127, 1, cv2.THRESH_BINARY)
    return binary.astype(np.uint8)


def watermark_to_bits(watermark_img: np.ndarray) -> np.ndarray:
    """
    Convert a 2D binary watermark image {0, 1} into a 1D bitstream array.
    """
    return watermark_img.flatten().astype(np.uint8)


def bits_to_watermark(bits: np.ndarray, size: Tuple[int, int] = (32, 32)) -> np.ndarray:
    """
    Reshape a 1D bitstream into a 2D binary image with values {0, 255} for saving and display.
    """
    expected_bits = size[0] * size[1]
    if len(bits) < expected_bits:
        raise ValueError(f"Not enough bits ({len(bits)}) for watermark of size {size} ({expected_bits} bits).")

    watermark_2d = bits[:expected_bits].reshape(size)
    return (watermark_2d * 255).astype(np.uint8)
