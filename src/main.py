"""
Main entry point for JND-guided frequency-domain image watermarking.
Runs the complete embedding, extraction, metric evaluation, and visualization pipeline.
"""

import sys
from pathlib import Path
import numpy as np

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    INPUT_IMAGE_PATH,
    WATERMARK_PATH,
    WATERMARKED_IMAGE_PATH,
    EXTRACTED_WATERMARK_PATH,
    DIFFERENCE_IMAGE_PATH,
    COMPARISON_IMAGE_PATH,
    WATERMARK_SIZE,
    COEFF_A,
    COEFF_B,
    JND_ALPHA,
    JND_BETA,
    JND_SCALE,
    DIFF_AMPLIFICATION,
)
from image_utils import (
    load_image,
    save_image,
    bgr_to_ycrcb,
    ycrcb_to_bgr,
)
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
    create_comparison_grid,
)


def run_pipeline(
    image_path: Path = INPUT_IMAGE_PATH,
    watermark_path: Path = WATERMARK_PATH,
    jnd_scale: float = JND_SCALE,
    verbose: bool = True,
):
    """
    Execute full watermarking pipeline:
    1. Load cover image & watermark
    2. Convert BGR -> YCrCb and isolate Y (luminance)
    3. Convert watermark to bitstream
    4. Embed bits into 8x8 DCT blocks guided by JND
    5. Reconstruct watermarked BGR image
    6. Extract watermark from watermarked image
    7. Calculate quality and recovery metrics
    8. Generate visual artifacts (difference and comparison grid)
    """
    if verbose:
        print("=" * 70)
        print("  JND-GUIDED FREQUENCY-DOMAIN IMAGE WATERMARKING PIPELINE")
        print("=" * 70)

    # 1. Load cover image
    if verbose:
        print(f"\n[1] Loading cover image: {image_path}")
    cover_bgr = load_image(image_path)
    h, w, c = cover_bgr.shape
    if verbose:
        print(f"    Resolution: {w}x{h} | Channels: {c} | Type: {cover_bgr.dtype}")

    # 2. Extract luminance channel Y
    if verbose:
        print("\n[2] Converting BGR -> YCrCb and isolating Y (luminance) channel...")
    y_orig, cr_orig, cb_orig = bgr_to_ycrcb(cover_bgr)

    # 3. Load & binarize watermark
    if verbose:
        print(f"\n[3] Loading watermark: {watermark_path} (target size: {WATERMARK_SIZE})")
    watermark_binary = load_watermark(watermark_path, size=WATERMARK_SIZE)
    watermark_bits = watermark_to_bits(watermark_binary)
    num_bits = len(watermark_bits)
    if verbose:
        print(f"    Watermark bits to embed: {num_bits} bits")

    # 4. Embed watermark bits into Y channel
    if verbose:
        print(f"\n[4] Embedding watermark with JND scale = {jnd_scale}...")
        print(f"    Coefficient pair: A={COEFF_A}, B={COEFF_B}")
        print(f"    JND model: alpha={JND_ALPHA}, beta={JND_BETA}")

    watermarked_y, embed_stats = embed_watermark(
        y_orig,
        watermark_bits,
        coeff_a=COEFF_A,
        coeff_b=COEFF_B,
        alpha=JND_ALPHA,
        beta=JND_BETA,
        scale=jnd_scale,
    )
    if verbose:
        print(f"    Embedded {embed_stats['embedded_bits']} bits across {embed_stats['total_blocks']} blocks")
        print(f"    Avg JND threshold: {embed_stats['average_jnd']:.4f} (Min: {embed_stats['min_jnd']:.4f}, Max: {embed_stats['max_jnd']:.4f})")

    # 5. Recombine Y' with original Cr, Cb
    watermarked_bgr = ycrcb_to_bgr(watermarked_y, cr_orig, cb_orig)
    save_image(WATERMARKED_IMAGE_PATH, watermarked_bgr)
    if verbose:
        print(f"    Saved watermarked image -> {WATERMARKED_IMAGE_PATH}")

    # 6. Extract watermark from watermarked image
    if verbose:
        print("\n[5] Extracting watermark from watermarked image...")
    y_wm, _, _ = bgr_to_ycrcb(watermarked_bgr)
    extracted_bits = extract_watermark(
        y_wm,
        num_bits=num_bits,
        coeff_a=COEFF_A,
        coeff_b=COEFF_B,
    )
    extracted_watermark_img = bits_to_watermark(extracted_bits, size=WATERMARK_SIZE)
    save_image(EXTRACTED_WATERMARK_PATH, extracted_watermark_img)
    if verbose:
        print(f"    Saved extracted watermark -> {EXTRACTED_WATERMARK_PATH}")

    # 7. Calculate quality & recovery metrics
    if verbose:
        print("\n[6] Computing evaluation metrics...")
    psnr_val = calculate_psnr(cover_bgr, watermarked_bgr)
    ssim_val = calculate_ssim(cover_bgr, watermarked_bgr)
    bit_acc = calculate_bit_accuracy(watermark_bits, extracted_bits)
    nc_val = calculate_nc(watermark_binary, (extracted_watermark_img > 127).astype(np.uint8))

    metrics_results = {
        "psnr": psnr_val,
        "ssim": ssim_val,
        "bit_accuracy": bit_acc,
        "nc": nc_val,
        "jnd_scale": jnd_scale,
    }

    if verbose:
        print("    " + "-" * 45)
        print(f"    PSNR (Imperceptibility) : {psnr_val:.2f} dB")
        print(f"    SSIM                    : {ssim_val:.4f}")
        print(f"    Watermark Bit Accuracy  : {bit_acc:.2f} %")
        print(f"    Normalized Correlation  : {nc_val:.4f}")
        print("    " + "-" * 45)

    # 8. Generate Difference and Comparison visualizations
    if verbose:
        print("\n[7] Generating visual analysis artifacts...")
    diff_img = create_difference_image(cover_bgr, watermarked_bgr, amplification=DIFF_AMPLIFICATION)
    save_image(DIFFERENCE_IMAGE_PATH, diff_img)
    if verbose:
        print(f"    Saved amplified difference image (x{DIFF_AMPLIFICATION:.0f}) -> {DIFFERENCE_IMAGE_PATH}")

    comparison_grid = create_comparison_grid(
        cover_bgr,
        watermarked_bgr,
        diff_img,
        extracted_watermark_img,
        metrics_results,
    )
    save_image(COMPARISON_IMAGE_PATH, comparison_grid)
    if verbose:
        print(f"    Saved 2x2 comparison board -> {COMPARISON_IMAGE_PATH}")
        print("\n[SUCCESS] Pipeline execution completed successfully!")
        print("=" * 70)

    return metrics_results


if __name__ == "__main__":
    run_pipeline()
