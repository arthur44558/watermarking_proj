"""
Watermark extraction algorithms for JND-guided DCT watermarking.
"""

from typing import Tuple
import numpy as np

from config import BLOCK_SIZE, COEFF_A, COEFF_B
from dct import apply_dct
from image_utils import split_into_blocks, pad_image


def extract_bit(
    block: np.ndarray,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
) -> int:
    """
    Extract a single watermark bit from an 8x8 image block by comparing DCT coefficients.

    Rule:
        If C(coeff_a) > C(coeff_b) => bit 1
        Otherwise                  => bit 0

    Args:
        block: 8x8 numpy array of pixel values.
        coeff_a: First DCT coefficient coordinate.
        coeff_b: Second DCT coefficient coordinate.

    Returns:
        int: Extracted bit (0 or 1).
    """
    dct_block = apply_dct(block)
    a = dct_block[coeff_a]
    b = dct_block[coeff_b]

    return 1 if a > b else 0


def extract_watermark(
    y_channel: np.ndarray,
    num_bits: int,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
    block_size: int = BLOCK_SIZE,
) -> np.ndarray:
    """
    Extract a sequence of watermark bits from the luminance (Y) channel blocks.

    Args:
        y_channel: 2D numpy array of luminance values.
        num_bits: Number of bits to extract.
        coeff_a: First DCT coordinate.
        coeff_b: Second DCT coordinate.
        block_size: Spatial block size (default: 8).

    Returns:
        extracted_bits: 1D numpy array of binary values {0, 1}.
    """
    padded_y, _ = pad_image(y_channel, block_size=block_size)
    blocks = split_into_blocks(padded_y, block_size=block_size)
    flat_blocks = blocks.reshape(-1, block_size, block_size)

    total_blocks = len(flat_blocks)
    if num_bits > total_blocks:
        raise ValueError(
            f"Requested {num_bits} bits, but image only has {total_blocks} blocks."
        )

    extracted = np.zeros(num_bits, dtype=np.uint8)
    for i in range(num_bits):
        extracted[i] = extract_bit(flat_blocks[i], coeff_a=coeff_a, coeff_b=coeff_b)

    return extracted
