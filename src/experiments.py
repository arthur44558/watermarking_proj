"""
Execution module for the 4 core experiments specified in Section 27:
1. Embedding strength scaling (k = 1.0, 1.25, 1.5, 2.0)
2. Smooth vs textured block activity & JND comparison
3. Visual inspection and zoomed crop analysis
4. Watermark payload capacity scaling (16x16, 32x32, 64x64)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import cv2
import numpy as np

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    INPUT_IMAGE_PATH,
    WATERMARK_PATH,
    OUTPUT_DIR,
    COEFF_A,
    COEFF_B,
    JND_ALPHA,
    JND_BETA,
    BLOCK_SIZE,
)
from image_utils import (
    load_image,
    save_image,
    bgr_to_ycrcb,
    ycrcb_to_bgr,
    split_into_blocks,
    pad_image,
)
from jnd import calculate_jnd
from watermark import (
    load_watermark,
    watermark_to_bits,
    bits_to_watermark,
)
from embedding import embed_watermark
from extraction import extract_watermark
from metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_bit_accuracy,
    calculate_nc,
    create_difference_image,
)


def run_experiment_1_embedding_strength(
    scales: List[float] = [1.0, 1.25, 1.5, 2.0]
) -> List[Dict[str, Any]]:
    """
    Experiment 1 — Embedding Strength Tradeoff:
    Evaluates PSNR, SSIM, Bit Accuracy, and NC across different JND multipliers k.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: EMBEDDING STRENGTH SCALING (k in [1.0, 1.25, 1.5, 2.0])")
    print("=" * 70)

    cover_bgr = load_image(INPUT_IMAGE_PATH)
    y_orig, cr_orig, cb_orig = bgr_to_ycrcb(cover_bgr)
    watermark_binary = load_watermark(WATERMARK_PATH, size=(32, 32))
    bits = watermark_to_bits(watermark_binary)

    results = []
    print(f"{'Scale (k)':<10} | {'PSNR (dB)':<12} | {'SSIM':<10} | {'Bit Acc (%)':<14} | {'NC':<10}")
    print("-" * 65)

    for k in scales:
        watermarked_y, _ = embed_watermark(
            y_orig,
            bits,
            coeff_a=COEFF_A,
            coeff_b=COEFF_B,
            alpha=JND_ALPHA,
            beta=JND_BETA,
            scale=k,
        )
        watermarked_bgr = ycrcb_to_bgr(watermarked_y, cr_orig, cb_orig)
        y_wm, _, _ = bgr_to_ycrcb(watermarked_bgr)

        extracted_bits = extract_watermark(y_wm, len(bits), coeff_a=COEFF_A, coeff_b=COEFF_B)
        extracted_wm_img = bits_to_watermark(extracted_bits, size=(32, 32))

        psnr_val = calculate_psnr(cover_bgr, watermarked_bgr)
        ssim_val = calculate_ssim(cover_bgr, watermarked_bgr)
        acc_val = calculate_bit_accuracy(bits, extracted_bits)
        nc_val = calculate_nc(watermark_binary, (extracted_wm_img > 127).astype(np.uint8))

        row = {
            "scale": k,
            "psnr": psnr_val,
            "ssim": ssim_val,
            "bit_accuracy": acc_val,
            "nc": nc_val,
        }
        results.append(row)
        print(f"{k:<10.2f} | {psnr_val:<12.2f} | {ssim_val:<10.4f} | {acc_val:<14.2f} | {nc_val:<10.4f}")

    return results


def run_experiment_2_smooth_vs_textured() -> Dict[str, Any]:
    """
    Experiment 2 — Smooth vs Textured Blocks:
    Identifies the smoothest and most textured 8x8 blocks in the image,
    calculating their standard deviation sigma and corresponding JND threshold.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: SMOOTH VS TEXTURED BLOCKS ACTIVITY & JND")
    print("=" * 70)

    cover_bgr = load_image(INPUT_IMAGE_PATH)
    y_orig, _, _ = bgr_to_ycrcb(cover_bgr)
    padded_y, _ = pad_image(y_orig, block_size=BLOCK_SIZE)
    blocks = split_into_blocks(padded_y, block_size=BLOCK_SIZE)
    num_h, num_w, _, _ = blocks.shape

    flat_blocks = blocks.reshape(-1, BLOCK_SIZE, BLOCK_SIZE)
    stds = [float(np.std(b)) for b in flat_blocks]

    smooth_idx = int(np.argmin(stds))
    textured_idx = int(np.argmax(stds))

    smooth_block = flat_blocks[smooth_idx]
    textured_block = flat_blocks[textured_idx]

    smooth_std = stds[smooth_idx]
    textured_std = stds[textured_idx]

    smooth_jnd = calculate_jnd(smooth_block, alpha=JND_ALPHA, beta=JND_BETA, scale=1.0)
    textured_jnd = calculate_jnd(textured_block, alpha=JND_ALPHA, beta=JND_BETA, scale=1.0)

    smooth_pos = (smooth_idx // num_w, smooth_idx % num_w)
    textured_pos = (textured_idx // num_w, textured_idx % num_w)

    print(f"Smooth Block [Grid {smooth_pos}]:")
    print(f"  Mean: {np.mean(smooth_block):.2f} | Std Dev (sigma): {smooth_std:.4f} | JND: {smooth_jnd:.4f}")
    print(f"\nTextured Block [Grid {textured_pos}]:")
    print(f"  Mean: {np.mean(textured_block):.2f} | Std Dev (sigma): {textured_std:.4f} | JND: {textured_jnd:.4f}")
    print(f"\nJND Adaptation Ratio (Textured / Smooth): {textured_jnd / smooth_jnd:.2f}x")

    return {
        "smooth": {"pos": smooth_pos, "std": smooth_std, "jnd": smooth_jnd},
        "textured": {"pos": textured_pos, "std": textured_std, "jnd": textured_jnd},
    }


def run_experiment_3_visual_inspection():
    """
    Experiment 3 — Visual Inspection & Zoomed Crops:
    Extracts zoomed-in crops comparing Original, Watermarked, and Difference
    in smooth versus textured areas.
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: VISUAL INSPECTION (ZOOMED CROPS)")
    print("=" * 70)

    cover_bgr = load_image(INPUT_IMAGE_PATH)
    y_orig, cr_orig, cb_orig = bgr_to_ycrcb(cover_bgr)
    watermark_binary = load_watermark(WATERMARK_PATH, size=(32, 32))
    bits = watermark_to_bits(watermark_binary)

    watermarked_y, _ = embed_watermark(y_orig, bits)
    watermarked_bgr = ycrcb_to_bgr(watermarked_y, cr_orig, cb_orig)
    diff = create_difference_image(cover_bgr, watermarked_bgr, amplification=30.0)

    # Crop an embedded region (e.g. top-left 128x128 pixels, covering 16x16 blocks)
    crop_size = 128
    orig_crop = cover_bgr[0:crop_size, 0:crop_size]
    wm_crop = watermarked_bgr[0:crop_size, 0:crop_size]
    diff_crop = diff[0:crop_size, 0:crop_size]

    # Resize for prominent display
    display_size = (384, 384)
    orig_disp = cv2.resize(orig_crop, display_size, interpolation=cv2.INTER_NEAREST)
    wm_disp = cv2.resize(wm_crop, display_size, interpolation=cv2.INTER_NEAREST)
    diff_disp = cv2.resize(diff_crop, display_size, interpolation=cv2.INTER_NEAREST)

    zoom_strip = np.hstack([orig_disp, wm_disp, diff_disp])
    zoom_path = OUTPUT_DIR / "zoom_inspection.png"
    save_image(zoom_path, zoom_strip)
    print(f"Saved zoomed region inspection (Orig | Watermarked | Diff x30) -> {zoom_path}")


def run_experiment_4_payload_scaling(
    sizes: List[int] = [16, 32, 64]
) -> List[Dict[str, Any]]:
    """
    Experiment 4 — Watermark Payload Size Scaling:
    Tests watermarks of size 16x16 (256 bits), 32x32 (1024 bits), and 64x64 (4096 bits).
    """
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: WATERMARK PAYLOAD SIZE SCALING")
    print("=" * 70)

    cover_bgr = load_image(INPUT_IMAGE_PATH)
    y_orig, cr_orig, cb_orig = bgr_to_ycrcb(cover_bgr)

    results = []
    print(f"{'Size':<12} | {'Bits':<8} | {'Blocks Used %':<16} | {'PSNR (dB)':<12} | {'SSIM':<10} | {'Bit Acc %':<10}")
    print("-" * 75)

    total_blocks = (y_orig.shape[0] // BLOCK_SIZE) * (y_orig.shape[1] // BLOCK_SIZE)

    for sz in sizes:
        wm_binary = load_watermark(WATERMARK_PATH, size=(sz, sz))
        bits = watermark_to_bits(wm_binary)
        num_bits = len(bits)
        capacity_pct = (num_bits / total_blocks) * 100.0

        watermarked_y, _ = embed_watermark(y_orig, bits)
        watermarked_bgr = ycrcb_to_bgr(watermarked_y, cr_orig, cb_orig)
        y_wm, _, _ = bgr_to_ycrcb(watermarked_bgr)

        extracted_bits = extract_watermark(y_wm, num_bits)
        psnr_val = calculate_psnr(cover_bgr, watermarked_bgr)
        ssim_val = calculate_ssim(cover_bgr, watermarked_bgr)
        acc_val = calculate_bit_accuracy(bits, extracted_bits)

        row = {
            "size": f"{sz}x{sz}",
            "bits": num_bits,
            "capacity_pct": capacity_pct,
            "psnr": psnr_val,
            "ssim": ssim_val,
            "bit_accuracy": acc_val,
        }
        results.append(row)
        print(f"{f'{sz}x{sz}':<12} | {num_bits:<8} | {capacity_pct:<16.2f} | {psnr_val:<12.2f} | {ssim_val:<10.4f} | {acc_val:<10.2f}")

    return results


def run_all_experiments():
    """Run all four experiments sequentially."""
    print("=" * 70)
    print("  RUNNING ALL SECTION 27 WATERMARKING EXPERIMENTS")
    print("=" * 70)
    run_experiment_1_embedding_strength()
    run_experiment_2_smooth_vs_textured()
    run_experiment_3_visual_inspection()
    run_experiment_4_payload_scaling()
    print("\n[SUCCESS] All experiments finished successfully!")


if __name__ == "__main__":
    run_all_experiments()
