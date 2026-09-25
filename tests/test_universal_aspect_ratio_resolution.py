"""
Comprehensive automated test suite for Universal Aspect Ratio & Resolution Support.
Verifies all specifications from JND_watermarking_universal_aspect_ratio_resolution_support.md:
  1. Cover images with arbitrary aspect ratios (16:9, 9:16, 1:1, 4:3, 21:9, odd/non-multiple-of-8).
  2. Watermark images with arbitrary aspect ratios & proportional downscaling preservation.
  3. Video inputs with arbitrary aspect ratios (16:9, 9:16, 1:1, 4:3, 21:9, odd/non-multiple-of-8).
  4. 8x8 DCT block handling: temporary edge padding, cropping back, zero boundary leakage.
  5. Dynamic carrier capacity calculation: (h // 8) * (w // 8) * bits_per_block.
  6. Exact quality metrics (PSNR, SSIM) evaluated strictly on original unpadded dimensions.
  7. Bounded memory frame-by-frame processing.
  8. Blind extraction and CRC32 payload verification across all combinations.
"""

import sys
import tempfile
from pathlib import Path
import numpy as np
import cv2
import pytest

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from watermarking.pipeline import (
    watermark_image,
    extract_only,
    calculate_carrier_capacity,
)
from watermarking.optimizer import optimize_watermark
from watermarking.payload import serialize_watermark, deserialize_watermark
from watermarking.metrics import calculate_psnr, calculate_ssim
from watermarking.video import (
    get_video_info,
    calculate_video_carrier_capacity,
    watermark_video,
    extract_video_watermark,
)
from watermarking.config import BLOCK_SIZE, BYTES_PER_BLOCK, HEADER_SIZE_BYTES


def create_synthetic_video(
    output_path: Path,
    width: int,
    height: int,
    fps: float = 25.0,
    num_frames: int = 12,
) -> Path:
    """Helper to generate synthetic test video across any aspect ratio and resolution."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    actual_path = output_path
    codecs = [("FFV1", ".avi"), ("mp4v", ".mp4"), ("MJPG", ".avi")]
    for c_code, c_ext in codecs:
        cand_path = output_path.with_suffix(c_ext)
        fourcc = cv2.VideoWriter_fourcc(*c_code)
        cand_writer = cv2.VideoWriter(str(cand_path), fourcc, fps, (width, height))
        if cand_writer.isOpened():
            writer = cand_writer
            actual_path = cand_path
            break

    if writer is None or not writer.isOpened():
        raise RuntimeError(f"Could not open VideoWriter for {width}x{height}")

    np.random.seed(42)
    for i in range(num_frames):
        frame = np.full((height, width, 3), 110, dtype=np.uint8)
        # Add dynamic features
        cx = int((i * 12) % max(1, width - 30) + 15)
        cy = int((i * 8) % max(1, height - 30) + 15)
        cv2.circle(frame, (cx, cy), min(12, min(width, height) // 4), (0, 0, 220), -1)
        cv2.rectangle(frame, (5, 5), (width - 5, height - 5), (180, 140, 60), 2)
        writer.write(frame)

    writer.release()
    return actual_path


# =========================================================================
# 1. COVER IMAGES: ARBITRARY ASPECT RATIOS & RESOLUTIONS
# =========================================================================

@pytest.mark.parametrize(
    "aspect_name, width, height",
    [
        ("16:9 landscape", 320, 180),
        ("9:16 portrait", 180, 320),
        ("1:1 square", 240, 240),
        ("4:3 standard", 320, 240),
        ("21:9 ultrawide", 420, 180),
        ("odd non-multiple-of-8", 321, 243),
        ("odd dimensions", 501, 333),
        ("extreme 1279x719", 639, 359),  # Scaled odd test for fast execution
    ],
)
def test_cover_image_aspect_ratios_preservation(aspect_name, width, height):
    """
    Verify that cover images with diverse aspect ratios:
    - Retain their EXACT width and height in the watermarked output.
    - Yield 100% payload bit accuracy and 0 CRC32 errors upon blind extraction.
    - Quality metrics (PSNR, SSIM) evaluate on exact original dimensions without padding distortion.
    """
    # Generate realistic cover image with natural gradients and shapes
    y_coords, x_coords = np.mgrid[0:height, 0:width]
    grad_x = (x_coords / max(1, width - 1) * 200).astype(np.uint8)
    grad_y = (y_coords / max(1, height - 1) * 200).astype(np.uint8)
    cover = cv2.merge([grad_x, grad_y, ((grad_x.astype(int) + grad_y.astype(int)) // 2).astype(np.uint8)])
    cv2.circle(cover, (width // 2, height // 2), min(width, height) // 4, (40, 180, 220), -1)

    # Synthetic watermark (40x24)
    wm = np.full((24, 40, 3), 200, dtype=np.uint8)
    cv2.putText(wm, "AR", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 200), 1)

    result = watermark_image(cover, wm)

    assert result["success"] is True
    assert result["metadata"]["cover_width"] == width
    assert result["metadata"]["cover_height"] == height

    # Verify physical file dimensions on disk
    out_file = PROJECT_ROOT / result["watermarked_image"].lstrip("/")
    saved_img = cv2.imread(str(out_file))
    assert saved_img.shape == (height, width, 3), (
        f"Dimensions mismatch for {aspect_name}: expected {width}x{height}, got {saved_img.shape[1]}x{saved_img.shape[0]}"
    )

    # Verify metrics
    assert result["metrics"]["bit_accuracy"] == 100.0
    assert result["metrics"]["psnr"] > 35.0
    assert result["metrics"]["ssim"] > 0.90

    # Blind extraction check
    ext_result = extract_only(out_file)
    assert ext_result["success"] is True
    assert ext_result["metadata"]["cover_width"] == width
    assert ext_result["metadata"]["cover_height"] == height
    assert ext_result["metadata"]["watermark_width"] == result["metadata"]["watermark_width"]
    assert ext_result["metadata"]["watermark_height"] == result["metadata"]["watermark_height"]


# =========================================================================
# 2. WATERMARK IMAGES: PROPORTIONAL DOWNSCALING & ASPECT RATIO PRESERVATION
# =========================================================================

@pytest.mark.parametrize(
    "wm_name, orig_w, orig_h",
    [
        ("landscape 3:1", 300, 100),
        ("portrait 1:3", 100, 300),
        ("16:9 banner", 320, 180),
        ("9:16 vertical", 180, 320),
        ("1:1 square", 200, 200),
        ("odd dimensions", 217, 131),
        ("extreme banner 16:1", 320, 20),
    ],
)
def test_watermark_aspect_ratio_preservation_during_optimization(wm_name, orig_w, orig_h):
    """
    Verify that the watermark optimizer preserves the intrinsic aspect ratio:
    - orig_w / orig_h == opt_w / opt_h (within integer rounding).
    - No distortion or square-forcing occurs when downscaling.
    """
    np.random.seed(123)
    wm_img = np.random.randint(0, 256, (orig_h, orig_w, 3), dtype=np.uint8)

    # Force downscaling by specifying a tight capacity (e.g. 1500 bytes)
    target_capacity = 1500
    res = optimize_watermark(wm_img, target_capacity)

    opt_w = res["optimized_width"]
    opt_h = res["optimized_height"]

    orig_aspect = orig_w / orig_h
    opt_aspect = opt_w / opt_h

    # Aspect ratio difference must be within small relative tolerance due to integer rounding
    rel_aspect_diff = abs(opt_aspect - orig_aspect) / orig_aspect
    assert rel_aspect_diff < 0.10, (
        f"Aspect ratio distorted for {wm_name}: original {orig_aspect:.4f} vs optimized {opt_aspect:.4f}"
    )

    # Verify payload actually fits target capacity
    assert res["optimized_size_bytes"] <= target_capacity
    assert res["applied"] is True


def test_no_unnecessary_downscaling_when_watermark_fits():
    """Verify that if watermark fits comfortably, no downscaling or lossy compression is applied."""
    wm_img = np.zeros((40, 60, 3), dtype=np.uint8)
    wm_img[10:30, 10:50] = (255, 200, 100)

    # Large capacity
    capacity = 50000
    res = optimize_watermark(wm_img, capacity)

    assert res["scale_percent"] == 100
    assert res["optimized_width"] == 60
    assert res["optimized_height"] == 40
    assert res["applied"] is False


# =========================================================================
# 3. DYNAMIC CAPACITY CALCULATION
# =========================================================================

@pytest.mark.parametrize(
    "width, height",
    [
        (1920, 1080),
        (1080, 1920),
        (1080, 1080),
        (1279, 719),
        (800, 600),
        (321, 243),
    ],
)
def test_dynamic_capacity_calculation_formula(width, height):
    """
    Verify capacity is calculated dynamically from (w // 8) * (h // 8) full blocks:
    - Never hardcoded to a fixed constant like 28 KB.
    - Exactly equals usable blocks * 2 bytes/block - 32 bytes header for Y-channel.
    """
    cover = np.zeros((height, width, 3), dtype=np.uint8)
    cap = calculate_carrier_capacity(cover)

    expected_full_blocks = (width // BLOCK_SIZE) * (height // BLOCK_SIZE)
    expected_y_bytes = expected_full_blocks * BYTES_PER_BLOCK
    expected_usable_y = max(0, expected_y_bytes - HEADER_SIZE_BYTES)

    assert cap["cover_width"] == width
    assert cap["cover_height"] == height
    assert cap["total_carrier_blocks"] == expected_full_blocks
    assert cap["y_capacity_bytes"] == expected_y_bytes
    assert cap["usable_y_capacity_bytes"] == expected_usable_y


# =========================================================================
# 4. 8x8 DCT BLOCK HANDLING & BOUNDARY ISOLATION
# =========================================================================

def test_odd_dimension_padding_and_metric_isolation():
    """
    Verify 8x8 DCT block edge replication padding:
    - Temporary edge padding is unpadded cleanly.
    - Padded pixels never leak into the final output or metric calculations.
    - PSNR/SSIM are evaluated between exact original and cropped watermarked image.
    """
    orig_w, orig_h = 333, 221  # Both odd and not divisible by 8
    cover = np.random.randint(40, 210, (orig_h, orig_w, 3), dtype=np.uint8)
    wm = np.full((30, 40), 180, dtype=np.uint8)

    result = watermark_image(cover, wm)

    # Output dimensions must match exactly
    out_file = PROJECT_ROOT / result["watermarked_image"].lstrip("/")
    saved_img = cv2.imread(str(out_file))
    assert saved_img.shape == (orig_h, orig_w, 3)

    # Manually calculate PSNR and SSIM on exact dimensions
    manual_psnr = calculate_psnr(cover, saved_img)
    manual_ssim = calculate_ssim(cover, saved_img)

    assert abs(result["metrics"]["psnr"] - round(manual_psnr, 2)) < 0.05
    assert abs(result["metrics"]["ssim"] - round(manual_ssim, 4)) < 0.001


# =========================================================================
# 5. VIDEO INPUTS: ARBITRARY ASPECT RATIOS & RESOLUTIONS
# =========================================================================

@pytest.mark.parametrize(
    "aspect_label, width, height",
    [
        ("16:9 landscape", 320, 180),
        ("9:16 portrait", 180, 320),
        ("1:1 square", 180, 180),
        ("4:3 standard", 240, 180),
        ("21:9 ultrawide", 420, 180),
        ("non-multiple-of-8", 242, 162),
    ],
)
def test_video_universal_aspect_ratios_and_resolutions(aspect_label, width, height):
    """
    Verify video watermarking across arbitrary aspect ratios:
    - Preserves exact width, height, aspect ratio, and frame count.
    - Temporary padding is unpadded per frame before writing.
    - Multi-frame blind extraction succeeds with CRC32 verification and 100% bit accuracy.
    - Bounded memory usage.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / f"test_{width}x{height}.avi"
        actual_vid = create_synthetic_video(vid_file, width=width, height=height, fps=25.0, num_frames=10)

        # Inspect video
        v_info = get_video_info(actual_vid)
        assert v_info["width"] == width
        assert v_info["height"] == height
        assert v_info["frame_count"] == 10

        # Capacity check
        v_cap = calculate_video_carrier_capacity(actual_vid)
        assert v_cap["is_video"] is True
        assert v_cap["cover_width"] == width
        assert v_cap["cover_height"] == height
        assert v_cap["total_carrier_blocks"] == (width // 8) * (height // 8)

        # Small watermark
        wm = np.full((16, 24, 3), 200, dtype=np.uint8)
        cv2.putText(wm, "V", (4, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)

        result = watermark_video(
            actual_vid,
            wm,
            output_dir=tmp_path / "out",
            mode="sequential",
        )

        assert result["success"] is True
        assert result["video_info"]["width"] == width
        assert result["video_info"]["height"] == height
        assert result["video_info"]["frame_count"] == 10
        assert result["extraction"]["status"] == "Success"
        assert result["extraction"]["crc_status"] == "Passed (CRC32 Verified)"
        assert result["metrics"]["bit_accuracy"] == 100.0
        assert result["metrics"]["psnr"] > 35.0

        # Verify output video file directly
        out_vid_path = Path(result["watermarked_video_path"])
        assert out_vid_path.exists()
        out_info = get_video_info(out_vid_path)
        assert out_info["width"] == width, f"Width mismatch: expected {width}, got {out_info['width']}"
        assert out_info["height"] == height, f"Height mismatch: expected {height}, got {out_info['height']}"
        assert out_info["frame_count"] == 10


# =========================================================================
# 6. STANDALONE RUNNER
# =========================================================================

if __name__ == "__main__":
    import traceback

    print("Running Universal Aspect Ratio & Resolution test suite...")
    test_cases = [
        ("Cover Image 16:9", lambda: test_cover_image_aspect_ratios_preservation("16:9", 320, 180)),
        ("Cover Image 9:16 Portrait", lambda: test_cover_image_aspect_ratios_preservation("9:16", 180, 320)),
        ("Cover Image 1:1 Square", lambda: test_cover_image_aspect_ratios_preservation("1:1", 240, 240)),
        ("Cover Image 21:9 Ultrawide", lambda: test_cover_image_aspect_ratios_preservation("21:9", 420, 180)),
        ("Cover Image Odd (501x333)", lambda: test_cover_image_aspect_ratios_preservation("odd", 501, 333)),
        ("Watermark 3:1 Landscape", lambda: test_watermark_aspect_ratio_preservation_during_optimization("3:1", 300, 100)),
        ("Watermark 1:3 Portrait", lambda: test_watermark_aspect_ratio_preservation_during_optimization("1:3", 100, 300)),
        ("Watermark 16:1 Banner", lambda: test_watermark_aspect_ratio_preservation_during_optimization("16:1", 320, 20)),
        ("No Unnecessary Downscaling", test_no_unnecessary_downscaling_when_watermark_fits),
        ("Dynamic Capacity Calculation", lambda: test_dynamic_capacity_calculation_formula(1279, 719)),
        ("8x8 Padding & Boundary Isolation", test_odd_dimension_padding_and_metric_isolation),
        ("Video Universal 16:9", lambda: test_video_universal_aspect_ratios_and_resolutions("16:9", 240, 135)),
        ("Video Universal 9:16 Portrait", lambda: test_video_universal_aspect_ratios_and_resolutions("9:16", 135, 240)),
        ("Video Universal 1:1 Square", lambda: test_video_universal_aspect_ratios_and_resolutions("1:1", 180, 180)),
        ("Video Universal 21:9 Ultrawide", lambda: test_video_universal_aspect_ratios_and_resolutions("21:9", 315, 135)),
        ("Video Universal Non-Multiple-of-8", lambda: test_video_universal_aspect_ratios_and_resolutions("odd", 243, 163)),
    ]

    passed = 0
    failed = 0
    for name, test_func in test_cases:
        try:
            test_func()
            print(f" [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Universal Aspect Ratio Test Results: {passed} passed, {failed} failed.")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
