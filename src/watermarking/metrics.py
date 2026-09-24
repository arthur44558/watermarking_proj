"""
Evaluation metrics and visualization utilities for image watermarking.
Computes PSNR, SSIM, Bit/Payload Accuracy, Normalized Correlation, and Reconstruction Error.
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
    Calculate percentage bit accuracy between original and extracted payload bits.
    Accuracy = (correct_bits / total_bits) * 100%
    """
    if len(orig_bits) != len(extracted_bits):
        min_len = min(len(orig_bits), len(extracted_bits))
        if min_len == 0:
            return 0.0
        orig_bits = orig_bits[:min_len]
        extracted_bits = extracted_bits[:min_len]

    matches = np.sum(orig_bits == extracted_bits)
    return float((matches / len(orig_bits)) * 100.0)


def calculate_nc(orig_watermark: np.ndarray, extracted_watermark: np.ndarray) -> float:
    """
    Calculate Normalized Correlation (NC) between original and reconstructed watermark images.
    Supports both grayscale and 3-channel color images.
    Formula:
        NC = sum(W_i * W'_i) / sqrt(sum(W_i^2) * sum(W'_i^2))
    """
    if orig_watermark.shape != extracted_watermark.shape:
        return 0.0

    w = orig_watermark.flatten().astype(np.float64)
    w_prime = extracted_watermark.flatten().astype(np.float64)

    numerator = np.sum(w * w_prime)
    denominator = np.sqrt(np.sum(w ** 2)) * np.sqrt(np.sum(w_prime ** 2))

    if denominator == 0.0:
        return 1.0 if np.array_equal(w, w_prime) else 0.0

    return float(numerator / denominator)


def calculate_watermark_reconstruction_error(
    orig_watermark: np.ndarray,
    extracted_watermark: np.ndarray,
) -> Dict[str, float]:
    """
    Calculate exact pixel-level reconstruction error between original and extracted watermarks.
    Returns RMSE, MAE, and Watermark PSNR.
    """
    if orig_watermark.shape != extracted_watermark.shape:
        return {"rmse": -1.0, "mae": -1.0, "psnr": 0.0}

    orig_f = orig_watermark.astype(np.float64)
    ext_f = extracted_watermark.astype(np.float64)

    diff = np.abs(orig_f - ext_f)
    mae = float(np.mean(diff))
    mse = float(np.mean(diff ** 2))
    rmse = float(np.sqrt(mse))

    psnr = 99.99 if mse == 0.0 else float(10.0 * np.log10((255.0 ** 2) / mse))

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "psnr": round(psnr, 2),
    }


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
