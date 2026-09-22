"""
Discrete Cosine Transform (DCT) and Inverse DCT (IDCT) functions for 8x8 blocks.
"""

import cv2
import numpy as np


def apply_dct(block: np.ndarray) -> np.ndarray:
    """
    Apply 2-D Discrete Cosine Transform (orthonormal) to an 8x8 block.
    Args:
        block: 2D numpy array (8x8), will be cast to float32.
    Returns:
        2D numpy array of DCT coefficients (float32).
    """
    block_f32 = block.astype(np.float32)
    return cv2.dct(block_f32)


def apply_idct(dct_block: np.ndarray) -> np.ndarray:
    """
    Apply 2-D Inverse Discrete Cosine Transform to an 8x8 DCT coefficient block.
    Args:
        dct_block: 2D numpy array (8x8) of DCT coefficients (float32).
    Returns:
        2D numpy array of spatial domain pixel values (float32).
    """
    dct_f32 = dct_block.astype(np.float32)
    return cv2.idct(dct_f32)
