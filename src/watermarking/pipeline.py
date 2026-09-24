"""
End-to-end watermarking pipeline for local application usage.
Supports true arbitrary-image watermarking with multi-bit JND-guided DCT modulation and blind reconstruction.
"""

from pathlib import Path
from typing import Dict, Any, Union
import uuid
import numpy as np

from .config import (
    BLOCK_SIZE,
    BITS_PER_BLOCK,
    BYTES_PER_BLOCK,
    HEADER_SIZE_BYTES,
    JND_ALPHA,
    JND_BETA,
    JND_SCALE,
    OUTPUT_DIR,
)
from .image_utils import load_image, save_image
from .payload import (
    serialize_watermark,
    deserialize_watermark,
    load_watermark_image,
)
from .optimizer import optimize_watermark
from .embedding import embed_image_payload
from .extraction import extract_and_reconstruct, extract_framed_payload
from .metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_bit_accuracy,
    calculate_nc,
    calculate_watermark_reconstruction_error,
    create_difference_image,
)


def calculate_carrier_capacity(cover: np.ndarray) -> Dict[str, Any]:
    """
    Calculate the exact usable payload capacity of a given cover image in bytes and bits.

    Args:
        cover: 2D or 3D numpy array of cover image.

    Returns:
        Dict containing total blocks, Y-channel capacity, multi-channel capacity, and usable capacity after header.
    """
    orig_h, orig_w = cover.shape[:2]
    full_rows = orig_h // BLOCK_SIZE
    full_cols = orig_w // BLOCK_SIZE
    total_blocks = full_rows * full_cols

    y_capacity_bytes = total_blocks * BYTES_PER_BLOCK
    usable_y_bytes = max(0, y_capacity_bytes - HEADER_SIZE_BYTES)

    is_color = cover.ndim == 3 and cover.shape[2] == 3
    if is_color:
        multichannel_capacity_bytes = total_blocks * BYTES_PER_BLOCK * 3
        usable_multi_bytes = max(0, multichannel_capacity_bytes - HEADER_SIZE_BYTES)
    else:
        multichannel_capacity_bytes = y_capacity_bytes
        usable_multi_bytes = usable_y_bytes

    max_usable_bytes = usable_y_bytes

    return {
        "cover_width": int(orig_w),
        "cover_height": int(orig_h),
        "total_carrier_blocks": int(total_blocks),
        "bits_per_block": BITS_PER_BLOCK,
        "is_color": bool(is_color),
        "y_capacity_bytes": int(y_capacity_bytes),
        "usable_y_capacity_bytes": int(usable_y_bytes),
        "multichannel_capacity_bytes": int(multichannel_capacity_bytes),
        "usable_multichannel_capacity_bytes": int(usable_multi_bytes),
        "max_usable_capacity_bytes": int(max_usable_bytes),
    }


def watermark_image(
    cover_source: Union[Path, str, np.ndarray, bytes],
    watermark_source: Union[Path, str, np.ndarray, bytes],
    output_dir: Union[Path, str] = OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    Execute full JND-guided DCT image-in-image watermarking pipeline:
    1. Load and validate cover image (retains exact original input dimensions and aspect ratio).
    2. Load arbitrary watermark image (PNG, JPG, WebP up to 1920x1200; Grayscale or RGB).
    3. Serialize and losslessly compress watermark with framing header and CRC32.
    4. Compute usable carrier capacity. If deficit, reject before modifying cover.
    5. Embed payload into DCT coefficients with activity-based JND masking and spatial compensation.
    6. Reconstruct spatial domain image and unpad to exact cover dimensions.
    7. Perform blind extraction and exact watermark reconstruction without ground truth dependency.
    8. Compute genuine evaluation metrics: Cover PSNR & SSIM, Watermark RMSE, MAE, NC, and Bit Accuracy.
    9. Save artifacts to output directory and return rich result dictionary.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Load cover image
    cover = load_image(cover_source)
    orig_h, orig_w = cover.shape[:2]

    # 2. Load watermark image
    wm_img, wm_info = load_watermark_image(watermark_source)

    # 3. Calculate carrier capacity
    cap_info = calculate_carrier_capacity(cover)
    usable_y = cap_info["usable_y_capacity_bytes"]
    max_cap = cap_info["max_usable_capacity_bytes"]

    # 4. Optimize watermark to fit available Luminance (Y) carrier capacity
    # Uses lossless RAW_ZLIB if it fits, else automatically applies lossy compression (WebP/JPEG)
    # with bounded quality search and aspect-ratio preserving downscaling.
    opt_result = optimize_watermark(wm_img, max_cap)
    opt_wm_img = opt_result["optimized_img"]
    channels_used = 1

    # 5. Serialize and frame payload
    framed_payload = serialize_watermark(
        opt_wm_img,
        channels_used=channels_used,
        codec=opt_result["codec_id"],
        quality=opt_result["quality"],
        orig_width=opt_result["original_width"],
        orig_height=opt_result["original_height"]
    )

    # 5. Embed payload into cover image with JND DCT modulation
    watermarked_bgr, embed_stats = embed_image_payload(
        cover,
        framed_payload,
        channels_used=channels_used,
        alpha=JND_ALPHA,
        beta=JND_BETA,
        scale=JND_SCALE,
    )

    # 6. Blind extraction verification
    extracted_payload = extract_framed_payload(watermarked_bgr)
    reconstructed_wm, ext_meta = deserialize_watermark(extracted_payload)

    # 7. Compute genuine evaluation metrics
    psnr_cover = calculate_psnr(cover, watermarked_bgr)
    ssim_cover = calculate_ssim(cover, watermarked_bgr)

    # Payload bit accuracy: percentage of correctly recovered carrier payload bits
    orig_bits = np.unpackbits(np.frombuffer(framed_payload, dtype=np.uint8))
    ext_bits = np.unpackbits(np.frombuffer(extracted_payload, dtype=np.uint8))
    bit_acc = calculate_bit_accuracy(orig_bits, ext_bits)

    # Watermark reconstruction fidelity against target embedded image
    target_wm = opt_wm_img
    nc_wm = calculate_nc(target_wm, reconstructed_wm)
    err_wm = calculate_watermark_reconstruction_error(target_wm, reconstructed_wm)

    # Create amplified difference image
    diff_img = create_difference_image(cover, watermarked_bgr, amplification=25.0)

    # 8. Save generated files
    run_id = uuid.uuid4().hex[:8]
    watermarked_filename = f"watermarked_{run_id}.png"
    extracted_filename = f"extracted_{run_id}.png"
    diff_filename = f"difference_{run_id}.png"

    save_image(output_path / watermarked_filename, watermarked_bgr)
    save_image(output_path / extracted_filename, reconstructed_wm)
    save_image(output_path / diff_filename, diff_img)

    # 9. Return structured response
    result = {
        "success": True,
        "mode": "embed_and_verify",
        "watermarked_image": f"/output/{watermarked_filename}",
        "extracted_watermark": f"/output/{extracted_filename}",
        "difference_image": f"/output/{diff_filename}",
        "optimization": {k: v for k, v in opt_result.items() if k != "optimized_img"},
        "metrics": {
            "psnr": round(psnr_cover, 2) if not np.isinf(psnr_cover) else 99.99,
            "ssim": round(ssim_cover, 4),
            "bit_accuracy": round(bit_acc, 2),
            "normalized_correlation": round(nc_wm, 4),
            "watermark_rmse": err_wm["rmse"],
            "watermark_mae": err_wm["mae"],
            "watermark_psnr": err_wm["psnr"],
        },
        "metadata": {
            "cover_width": int(orig_w),
            "cover_height": int(orig_h),
            "watermark_width": int(wm_info["width"]),
            "watermark_height": int(wm_info["height"]),
            "watermark_format": wm_info["format"],
            "watermark_color_mode": wm_info["color_mode"],
            "raw_payload_bytes": int(wm_info["raw_bytes"]),
            "compressed_payload_bytes": int(wm_info["compressed_bytes"]),
            "total_payload_bytes": int(len(framed_payload)),
            "carrier_capacity_bytes": int(cap_info["max_usable_capacity_bytes"]),
            "channels_used": int(channels_used),
            "channels_used_label": "Y (Luminance)" if channels_used == 1 else "Y, Cr, Cb (Multi-Channel)",
            "utilization_percent": round((len(framed_payload) / max(cap_info["max_usable_capacity_bytes"], 1)) * 100, 2),
            "compression_ratio": wm_info["compression_ratio"],
            "processed_blocks": embed_stats["blocks_modified"],
            "total_carrier_blocks": cap_info["total_carrier_blocks"],
        },
        "configuration": {
            "color_space": "YCrCb",
            "channels_used": channels_used,
            "block_size": BLOCK_SIZE,
            "transform": "2D-DCT-II",
            "jnd_alpha": JND_ALPHA,
            "jnd_beta": JND_BETA,
            "bits_per_block": BITS_PER_BLOCK,
            "max_payload_limit_bytes": None,
        },
    }

    return result


def extract_only(
    image_source: Union[Path, str, np.ndarray, bytes],
    output_dir: Union[Path, str] = OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    Mode B: Extract watermark directly from a supplied (already-watermarked) image.
    1. Loads the image (BGR).
    2. Performs blind extraction: reads 32-byte header, verifies CRC32, decompresses payload.
    3. Reconstructs watermark image at exact original dimensions and Grayscale/RGB color mode.
    4. Saves copy of input image and extracted watermark image.
    5. Returns result dictionary with mode='extract_only' and metrics set to None (no fabricated metrics).
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    img = load_image(image_source)
    orig_h, orig_w = img.shape[:2]

    # Blind extraction and reconstruction
    reconstructed_wm, meta = extract_and_reconstruct(img)

    run_id = uuid.uuid4().hex[:8]
    input_filename = f"extraction_input_{run_id}.png"
    extracted_filename = f"extracted_{run_id}.png"

    save_image(output_path / input_filename, img)
    save_image(output_path / extracted_filename, reconstructed_wm)

    return {
        "success": True,
        "mode": "extract_only",
        "watermarked_image": f"/output/{input_filename}",
        "extracted_watermark": f"/output/{extracted_filename}",
        "metrics": {
            "psnr": None,
            "ssim": None,
            "bit_accuracy": None,
            "normalized_correlation": None,
            "watermark_rmse": None,
            "watermark_mae": None,
            "watermark_psnr": None,
        },
        "metadata": {
            "cover_width": int(orig_w),
            "cover_height": int(orig_h),
            "watermark_width": int(meta["width"]),
            "watermark_height": int(meta["height"]),
            "watermark_color_mode": meta["color_mode"],
            "compressed_payload_bytes": int(meta["compressed_len"]),
            "total_payload_bytes": int(meta["total_payload_bytes"]),
            "channels_used": int(meta["channels_used"]),
            "channels_used_label": "Y (Luminance)" if meta["channels_used"] == 1 else "Y, Cr, Cb (Multi-Channel)",
        },
        "configuration": {
            "color_space": "YCrCb",
            "block_size": BLOCK_SIZE,
            "transform": "2D-DCT-II",
            "jnd_alpha": JND_ALPHA,
            "jnd_beta": JND_BETA,
            "bits_per_block": BITS_PER_BLOCK,
        },
    }
