"""
Embedding algorithms for JND-guided DCT watermark insertion.
"""

from typing import Tuple, Dict, Any
import numpy as np

from config import (
    BLOCK_SIZE,
    COEFF_A,
    COEFF_B,
    JND_ALPHA,
    JND_BETA,
    JND_SCALE,
)
from dct import apply_dct, apply_idct
from jnd import calculate_jnd
from image_utils import split_into_blocks, reconstruct_from_blocks, pad_image, unpad_image


def embed_bit(
    block: np.ndarray,
    bit: int,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
    alpha: float = JND_ALPHA,
    beta: float = JND_BETA,
    scale: float = JND_SCALE,
) -> np.ndarray:
    """
    Embed a single watermark bit into an 8x8 image block using JND-guided DCT coefficient modification.

    Algorithm:
        1. Calculate 2D DCT of the block: C = DCT(B)
        2. Calculate local perceptual threshold: T = JND_B * scale
        3. If bit == 1: enforce C(coeff_a) - C(coeff_b) >= T
           If bit == 0: enforce C(coeff_b) - C(coeff_a) >= T
        4. Modify coefficients symmetrically if condition is not satisfied.
        5. Apply 2D IDCT to return modified block.

    Args:
        block: 8x8 numpy array of pixel values.
        bit: Binary value to embed (0 or 1).
        coeff_a: First DCT coefficient coordinate (default: (3, 2)).
        coeff_b: Second DCT coefficient coordinate (default: (2, 3)).
        alpha: Baseline JND threshold.
        beta: Texture sensitivity weighting factor.
        scale: Embedding strength multiplier k.

    Returns:
        watermarked_block: 8x8 numpy array of spatial domain values (float32).
    """
    dct_block = apply_dct(block)
    jnd = calculate_jnd(block, alpha=alpha, beta=beta, scale=scale)

    a = dct_block[coeff_a]
    b = dct_block[coeff_b]

    if bit == 1:
        diff = a - b
        if diff < jnd:
            adjustment = (jnd - diff) / 2.0
            dct_block[coeff_a] += adjustment
            dct_block[coeff_b] -= adjustment
    elif bit == 0:
        diff = b - a
        if diff < jnd:
            adjustment = (jnd - diff) / 2.0
            dct_block[coeff_b] += adjustment
            dct_block[coeff_a] -= adjustment
    else:
        raise ValueError(f"Invalid bit value: {bit}. Must be 0 or 1.")

    watermarked_block = apply_idct(dct_block)
    return watermarked_block


def embed_watermark(
    y_channel: np.ndarray,
    bits: np.ndarray,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
    alpha: float = JND_ALPHA,
    beta: float = JND_BETA,
    scale: float = JND_SCALE,
    block_size: int = BLOCK_SIZE,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Embed a bitstream sequentially into the 8x8 blocks of the luminance (Y) channel.

    Args:
        y_channel: 2D numpy array of luminance values.
        bits: 1D numpy array of binary watermark bits {0, 1}.
        coeff_a: First DCT coordinate pair.
        coeff_b: Second DCT coordinate pair.
        alpha, beta: JND model parameters.
        scale: Embedding strength multiplier.
        block_size: Spatial block dimension (default: 8).

    Returns:
        watermarked_y: 2D numpy array of uint8 luminance values.
        stats: Dictionary containing embedding statistics.
    """
    padded_y, orig_shape = pad_image(y_channel, block_size=block_size)
    blocks = split_into_blocks(padded_y, block_size=block_size)
    num_h, num_w, _, _ = blocks.shape
    total_blocks = num_h * num_w
    num_bits = len(bits)

    if num_bits > total_blocks:
        raise ValueError(
            f"Watermark payload ({num_bits} bits) exceeds available block capacity ({total_blocks} blocks)."
        )

    # Flatten block grid for sequential embedding
    flat_blocks = blocks.reshape(-1, block_size, block_size).copy().astype(np.float32)

    modified_count = 0
    jnd_values = []

    for i in range(num_bits):
        bit = int(bits[i])
        orig_block = flat_blocks[i]
        jnd_val = calculate_jnd(orig_block, alpha=alpha, beta=beta, scale=scale)
        jnd_values.append(jnd_val)

        watermarked_block = embed_bit(
            orig_block,
            bit,
            coeff_a=coeff_a,
            coeff_b=coeff_b,
            alpha=alpha,
            beta=beta,
            scale=scale,
        )
        flat_blocks[i] = watermarked_block
        modified_count += 1

    # Reconstruct 4D blocks structure
    reconstructed_blocks = flat_blocks.reshape(num_h, num_w, block_size, block_size)
    reconstructed_padded_y = reconstruct_from_blocks(reconstructed_blocks, block_size=block_size)

    # Unpad to original shape and clip to valid uint8 range [0, 255]
    watermarked_y_float = unpad_image(reconstructed_padded_y, orig_shape)
    watermarked_y = np.clip(np.round(watermarked_y_float), 0, 255).astype(np.uint8)

    stats = {
        "total_blocks": total_blocks,
        "embedded_bits": num_bits,
        "average_jnd": float(np.mean(jnd_values)) if jnd_values else 0.0,
        "min_jnd": float(np.min(jnd_values)) if jnd_values else 0.0,
        "max_jnd": float(np.max(jnd_values)) if jnd_values else 0.0,
    }

    return watermarked_y, stats
