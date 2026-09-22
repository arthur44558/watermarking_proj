"""
Activity-based Just Noticeable Difference (JND) approximation for 8x8 image blocks.
"""

import numpy as np


def calculate_jnd(
    block: np.ndarray,
    alpha: float = 2.0,
    beta: float = 0.1,
    scale: float = 1.0,
) -> float:
    """
    Calculate an activity-based JND approximation for an 8x8 image block.

    Model:
        sigma = sqrt( (1/64) * sum((x_i - mu)^2) )
        JND = (alpha + beta * sigma) * scale

    Args:
        block: 8x8 spatial domain image block (numpy array).
        alpha: Baseline visibility threshold (default: 2.0).
        beta: Texture sensitivity weighting factor (default: 0.1).
        scale: Embedding strength multiplier k (default: 1.0).

    Returns:
        float: Computed perceptual threshold for the block.
    """
    std = float(np.std(block))
    jnd = (alpha + beta * std) * scale
    return jnd
