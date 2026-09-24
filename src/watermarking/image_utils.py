"""
Image utilities for color space conversion, padding, block splitting, and reconstruction.
"""

from pathlib import Path
from typing import Tuple, Union
import cv2
import numpy as np


def load_image(source: Union[Path, str, np.ndarray, bytes]) -> np.ndarray:
    """
    Load an image from disk, bytes buffer, or return numpy array in BGR format.
    Handles transparency by stripping alpha channel to standard 3-channel BGR.
    """
    if isinstance(source, np.ndarray):
        img = source
    elif isinstance(source, (bytes, bytearray)):
        nparr = np.frombuffer(source, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    else:
        path_str = str(source)
        img = cv2.imread(path_str, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(f"Could not load image from: {path_str}")

    if img is None:
        raise ValueError("Invalid image data provided.")

    # Convert grayscale or BGRA to standard 3-channel BGR
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] == 4:
        # Blend over white background
        b, g, r, a = cv2.split(img)
        alpha = a.astype(float) / 255.0
        bgr = cv2.merge([b, g, r]).astype(float)
        white_bg = np.full_like(bgr, 255.0)
        img = (bgr * alpha[:, :, np.newaxis] + white_bg * (1.0 - alpha[:, :, np.newaxis])).astype(np.uint8)
    elif img.ndim == 3 and img.shape[2] == 3:
        pass
    else:
        raise ValueError(f"Unsupported image array shape: {img.shape}")

    return img


def save_image(path: Union[Path, str], image: np.ndarray) -> Path:
    """Save an image to disk, creating parent directories if necessary."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(path_obj), image)
    if not success:
        raise IOError(f"Failed to write image to {path_obj}")
    return path_obj


def bgr_to_ycrcb(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert BGR image to YCrCb and split into Y (luminance), Cr, and Cb channels."""
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    return y, cr, cb


def ycrcb_to_bgr(y: np.ndarray, cr: np.ndarray, cb: np.ndarray) -> np.ndarray:
    """Merge Y, Cr, and Cb channels and convert to BGR image."""
    ycrcb = cv2.merge([y, cr, cb])
    bgr = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    return bgr


def pad_image(channel: np.ndarray, block_size: int = 8) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Pad 2D image channel with edge replication so height and width are divisible by block_size.
    Returns:
        padded_channel: np.ndarray
        original_shape: Tuple[int, int] (height, width)
    """
    h, w = channel.shape[:2]
    pad_h = (block_size - (h % block_size)) % block_size
    pad_w = (block_size - (w % block_size)) % block_size

    if pad_h == 0 and pad_w == 0:
        return channel.copy(), (h, w)

    padded = cv2.copyMakeBorder(channel, 0, pad_h, 0, pad_w, cv2.BORDER_REPLICATE)
    return padded, (h, w)


def unpad_image(channel: np.ndarray, original_shape: Tuple[int, int]) -> np.ndarray:
    """Crop padded 2D image channel back to its original shape."""
    orig_h, orig_w = original_shape
    return channel[:orig_h, :orig_w].copy()


def split_into_blocks(channel: np.ndarray, block_size: int = 8) -> np.ndarray:
    """
    Split a 2D channel into non-overlapping blocks of size block_size x block_size.
    Returns:
        blocks: 4D numpy array of shape (num_h, num_w, block_size, block_size)
    """
    h, w = channel.shape[:2]
    if h % block_size != 0 or w % block_size != 0:
        raise ValueError(f"Channel dimensions ({h}, {w}) must be divisible by {block_size}.")

    num_h = h // block_size
    num_w = w // block_size

    blocks = (
        channel.reshape(num_h, block_size, num_w, block_size)
        .swapaxes(1, 2)
        .copy()
    )
    return blocks


def reconstruct_from_blocks(blocks: np.ndarray, block_size: int = 8) -> np.ndarray:
    """
    Reconstruct 2D channel from 4D blocks array of shape (num_h, num_w, block_size, block_size).
    Returns:
        channel: 2D numpy array of shape (num_h * block_size, num_w * block_size)
    """
    num_h, num_w, bh, bw = blocks.shape
    if bh != block_size or bw != block_size:
        raise ValueError(f"Block dimensions ({bh}, {bw}) do not match block_size {block_size}.")

    channel = (
        blocks.swapaxes(1, 2)
        .reshape(num_h * block_size, num_w * block_size)
        .copy()
    )
    return channel
