"""
Evaluation metrics and visualization utilities for image watermarking.
"""

from typing import Dict, Any, Tuple
import cv2
import numpy as np

try:
    from skimage.metrics import structural_similarity as ssim_func
except ImportError:
    ssim_func = None


def calculate_psnr(original: np.ndarray, watermarked: np.ndarray) -> float:
    """
    Calculate Peak Signal-to-Noise Ratio (PSNR) in decibels (dB).
    Formula:
        MSE = (1/N) * sum((original - watermarked)^2)
        PSNR = 10 * log10(255^2 / MSE)
    """
    orig_f = original.astype(np.float64)
    wm_f = watermarked.astype(np.float64)

    mse = np.mean((orig_f - wm_f) ** 2)
    if mse == 0.0:
        return float("inf")

    psnr = 10.0 * np.log10((255.0 ** 2) / mse)
    return float(psnr)


def calculate_ssim(original: np.ndarray, watermarked: np.ndarray) -> float:
    """
    Calculate Structural Similarity Index (SSIM) between original and watermarked images.
    If color, computes on luminance/grayscale.
    """
    if original.ndim == 3:
        orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        wm_gray = cv2.cvtColor(watermarked, cv2.COLOR_BGR2GRAY)
    else:
        orig_gray = original
        wm_gray = watermarked

    if ssim_func is not None:
        score = ssim_func(orig_gray, wm_gray, data_range=255)
        return float(score)

    # Pure NumPy fallback implementation of SSIM (Wang et al. 2004)
    k1, k2 = 0.01, 0.03
    l_val = 255.0
    c1 = (k1 * l_val) ** 2
    c2 = (k2 * l_val) ** 2

    x = orig_gray.astype(np.float64)
    y = wm_gray.astype(np.float64)

    mu_x = cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_y = cv2.GaussianBlur(y, (11, 11), 1.5)

    mu_x_sq = mu_x ** 2
    mu_y_sq = mu_y ** 2
    mu_xy = mu_x * mu_y

    sigma_x_sq = cv2.GaussianBlur(x ** 2, (11, 11), 1.5) - mu_x_sq
    sigma_y_sq = cv2.GaussianBlur(y ** 2, (11, 11), 1.5) - mu_y_sq
    sigma_xy = cv2.GaussianBlur(x * y, (11, 11), 1.5) - mu_xy

    numerator = (2.0 * mu_xy + c1) * (2.0 * sigma_xy + c2)
    denominator = (mu_x_sq + mu_y_sq + c1) * (sigma_x_sq + sigma_y_sq + c2)
    ssim_map = numerator / (denominator + 1e-12)

    return float(np.mean(ssim_map))


def calculate_bit_accuracy(orig_bits: np.ndarray, extracted_bits: np.ndarray) -> float:
    """
    Calculate percentage bit accuracy between original and extracted watermark bits.
    Accuracy = (correct_bits / total_bits) * 100%
    """
    if len(orig_bits) != len(extracted_bits):
        raise ValueError("Bit arrays must be of equal length to compute accuracy.")

    matches = np.sum(orig_bits == extracted_bits)
    return float((matches / len(orig_bits)) * 100.0)


def calculate_nc(orig_watermark: np.ndarray, extracted_watermark: np.ndarray) -> float:
    """
    Calculate Normalized Correlation (NC) between original and recovered watermark.
    Formula:
        NC = sum(W_i * W'_i) / sqrt(sum(W_i^2) * sum(W'_i^2))
    """
    w = orig_watermark.flatten().astype(np.float64)
    w_prime = extracted_watermark.flatten().astype(np.float64)

    numerator = np.sum(w * w_prime)
    denominator = np.sqrt(np.sum(w ** 2)) * np.sqrt(np.sum(w_prime ** 2))

    if denominator == 0.0:
        return 1.0 if np.array_equal(w, w_prime) else 0.0

    return float(numerator / denominator)


def create_difference_image(
    original: np.ndarray,
    watermarked: np.ndarray,
    amplification: float = 25.0,
) -> np.ndarray:
    """
    Generate an amplified difference image: D = |I' - I| * amplification.
    """
    orig_f = original.astype(np.float32)
    wm_f = watermarked.astype(np.float32)

    diff = np.abs(wm_f - orig_f)
    amplified = np.clip(diff * amplification, 0, 255).astype(np.uint8)
    return amplified


def create_comparison_grid(
    original: np.ndarray,
    watermarked: np.ndarray,
    difference: np.ndarray,
    extracted_watermark: np.ndarray,
    metrics: Dict[str, Any],
    cell_size: Tuple[int, int] = (512, 512),
) -> np.ndarray:
    """
    Assemble a 2x2 comparison board showing:
    ┌────────────────────┬────────────────────┐
    │ Original           │ Watermarked        │
    ├────────────────────┼────────────────────┤
    │ Difference (x25)   │ Extracted Watermark│
    └────────────────────┴────────────────────┘
    with metrics annotated at the bottom.
    """
    cw, ch = cell_size

    # Prepare cells
    cell_orig = cv2.resize(original, (cw, ch), interpolation=cv2.INTER_AREA)
    cell_wm = cv2.resize(watermarked, (cw, ch), interpolation=cv2.INTER_AREA)

    if difference.ndim == 2:
        diff_bgr = cv2.cvtColor(difference, cv2.COLOR_GRAY2BGR)
    else:
        diff_bgr = difference
    cell_diff = cv2.resize(diff_bgr, (cw, ch), interpolation=cv2.INTER_AREA)

    # Upscale extracted watermark for clear visibility
    if extracted_watermark.ndim == 2:
        ext_bgr = cv2.cvtColor(extracted_watermark, cv2.COLOR_GRAY2BGR)
    else:
        ext_bgr = extracted_watermark
    cell_ext = cv2.resize(ext_bgr, (cw, ch), interpolation=cv2.INTER_NEAREST)

    # Label overlay function
    def add_label(img: np.ndarray, text: str) -> np.ndarray:
        labeled = img.copy()
        cv2.rectangle(labeled, (0, 0), (cw, 36), (20, 20, 20), -1)
        cv2.putText(
            labeled,
            text,
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return labeled

    labeled_orig = add_label(cell_orig, "Original Image")
    labeled_wm = add_label(cell_wm, "Watermarked Image")
    labeled_diff = add_label(cell_diff, "Difference (|I' - I| x 25)")
    labeled_ext = add_label(cell_ext, "Extracted Watermark")

    # Combine into 2x2 grid
    top_row = np.hstack([labeled_orig, labeled_wm])
    bottom_row = np.hstack([labeled_diff, labeled_ext])
    grid = np.vstack([top_row, bottom_row])

    # Banner for metrics at the bottom
    banner_height = 80
    banner = np.zeros((banner_height, cw * 2, 3), dtype=np.uint8)
    banner[:] = (35, 35, 35)

    metrics_text_1 = (
        f"PSNR: {metrics.get('psnr', 0.0):.2f} dB  |  "
        f"SSIM: {metrics.get('ssim', 0.0):.4f}"
    )
    metrics_text_2 = (
        f"Bit Accuracy: {metrics.get('bit_accuracy', 0.0):.2f}%  |  "
        f"NC: {metrics.get('nc', 0.0):.4f}  |  "
        f"JND Scale: {metrics.get('jnd_scale', 1.0)}"
    )

    cv2.putText(
        banner,
        metrics_text_1,
        (24, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 180),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        banner,
        metrics_text_2,
        (24, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (200, 200, 255),
        2,
        cv2.LINE_AA,
    )

    final_comparison = np.vstack([grid, banner])
    return final_comparison
