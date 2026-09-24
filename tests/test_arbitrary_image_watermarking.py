"""
Comprehensive test suite for arbitrary-image watermarking with multi-bit JND DCT modulation.
Verifies lossless reconstruction, color modes, odd dimensions, capacity enforcement, and extraction-only mode.
"""

import sys
from pathlib import Path
import numpy as np
import cv2

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from watermarking.pipeline import watermark_image, extract_only, calculate_carrier_capacity
from watermarking.payload import (
    serialize_watermark,
    deserialize_watermark,
    load_watermark_image,
)
from watermarking.metrics import calculate_psnr, calculate_ssim, calculate_nc, calculate_watermark_reconstruction_error


def test_serialization_roundtrip_grayscale():
    """Verify lossless serialization and deserialization of a grayscale image."""
    img = np.random.randint(0, 256, (100, 150), dtype=np.uint8)
    payload = serialize_watermark(img, channels_used=1)
    reconstructed, meta = deserialize_watermark(payload)

    assert meta["color_mode"] == "Grayscale"
    assert meta["width"] == 150
    assert meta["height"] == 100
    assert np.array_equal(img, reconstructed), "Grayscale image serialization was not lossless!"


def test_serialization_roundtrip_rgb():
    """Verify lossless serialization and deserialization of an RGB color image."""
    img = np.random.randint(0, 256, (80, 120, 3), dtype=np.uint8)
    payload = serialize_watermark(img, channels_used=1)
    reconstructed, meta = deserialize_watermark(payload)

    assert meta["color_mode"] == "RGB"
    assert meta["width"] == 120
    assert meta["height"] == 80
    assert np.array_equal(img, reconstructed), "RGB image serialization was not lossless!"


def test_carrier_capacity_calculation():
    """Verify carrier capacity formulas for odd and standard resolutions."""
    # 800x600 image: 100 cols x 75 rows = 7,500 blocks
    cover = np.zeros((600, 800, 3), dtype=np.uint8)
    cap = calculate_carrier_capacity(cover)

    assert cap["total_carrier_blocks"] == 7500
    assert cap["y_capacity_bytes"] == 7500 * 2
    assert cap["usable_y_capacity_bytes"] == 7500 * 2 - 32
    assert cap["multichannel_capacity_bytes"] == 7500 * 6
    assert cap["usable_multichannel_capacity_bytes"] == 7500 * 6 - 32


def test_full_roundtrip_grayscale_watermark():
    """Test full pipeline with a grayscale logo embedded in a color cover image."""
    cover = cv2.imread(str(PROJECT_ROOT / "input" / "test_image.jpeg"))
    assert cover is not None

    # Create synthetic grayscale watermark: 100x60
    wm = np.full((60, 100), 230, dtype=np.uint8)
    cv2.rectangle(wm, (5, 5), (94, 54), 30, 2)
    cv2.putText(wm, "JND-TEST", (12, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 10, 1)

    result = watermark_image(cover, wm)

    assert result["success"] is True
    assert result["mode"] == "embed_and_verify"
    assert result["metrics"]["bit_accuracy"] == 100.0
    assert result["metrics"]["normalized_correlation"] == 1.0
    assert result["metrics"]["watermark_rmse"] == 0.0
    assert result["metrics"]["watermark_mae"] == 0.0
    assert result["metrics"]["psnr"] > 38.0
    assert result["metrics"]["ssim"] > 0.95
    assert result["metadata"]["watermark_color_mode"] == "Grayscale"
    assert result["metadata"]["watermark_width"] == 100
    assert result["metadata"]["watermark_height"] == 60


def test_full_roundtrip_rgb_color_watermark():
    """Test full pipeline with an RGB color watermark embedded in a color cover image."""
    cover = cv2.imread(str(PROJECT_ROOT / "input" / "test_image.jpeg"))
    assert cover is not None

    # Create synthetic RGB watermark: 120x80 with distinct colors
    wm = np.zeros((80, 120, 3), dtype=np.uint8)
    wm[:, :] = (240, 230, 220)
    cv2.circle(wm, (40, 40), 25, (0, 0, 255), -1)      # Red circle
    cv2.rectangle(wm, (75, 15), (105, 65), (255, 0, 0), -1)  # Blue rectangle
    cv2.putText(wm, "COLOR", (15, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 128, 0), 1)

    result = watermark_image(cover, wm)

    assert result["success"] is True
    assert result["metrics"]["bit_accuracy"] == 100.0
    assert result["metrics"]["normalized_correlation"] == 1.0
    assert result["metrics"]["watermark_rmse"] == 0.0
    assert result["metadata"]["watermark_color_mode"] == "RGB"
    assert result["metadata"]["watermark_width"] == 120
    assert result["metadata"]["watermark_height"] == 80


def test_odd_resolution_cover_preservation():
    """Verify that cover image with odd dimensions (non-multiple-of-8) retains exact shape on output."""
    orig_w, orig_h = 713, 489
    cover = np.random.randint(40, 220, (orig_h, orig_w, 3), dtype=np.uint8)

    wm = np.full((40, 60), 200, dtype=np.uint8)
    cv2.putText(wm, "ODD", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 20, 1)

    result = watermark_image(cover, wm)

    # Load watermarked output from disk
    output_file = PROJECT_ROOT / result["watermarked_image"].lstrip("/")
    saved_watermarked = cv2.imread(str(output_file))

    assert saved_watermarked.shape == (orig_h, orig_w, 3), "Cover image dimensions were not preserved!"
    assert result["metrics"]["bit_accuracy"] == 100.0
    assert result["metrics"]["watermark_rmse"] == 0.0


def test_extraction_only_mode():
    """Verify Mode B (Extraction Only) extracts and reconstructs without original watermark, and metrics are None."""
    cover = cv2.imread(str(PROJECT_ROOT / "input" / "test_image.jpeg"))

    wm = np.zeros((50, 70, 3), dtype=np.uint8)
    wm[:, :] = (180, 200, 220)
    cv2.putText(wm, "EXTRACT", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 180), 1)

    # First embed
    embed_res = watermark_image(cover, wm)
    watermarked_path = PROJECT_ROOT / embed_res["watermarked_image"].lstrip("/")

    # Now extract using ONLY the saved watermarked image
    extract_res = extract_only(watermarked_path)

    assert extract_res["success"] is True
    assert extract_res["mode"] == "extract_only"
    # Metrics must NOT be fabricated
    assert extract_res["metrics"]["psnr"] is None
    assert extract_res["metrics"]["ssim"] is None
    assert extract_res["metrics"]["bit_accuracy"] is None
    assert extract_res["metrics"]["normalized_correlation"] is None
    assert extract_res["metrics"]["watermark_rmse"] is None

    # Extracted metadata must match original watermark
    assert extract_res["metadata"]["watermark_width"] == 70
    assert extract_res["metadata"]["watermark_height"] == 50
    assert extract_res["metadata"]["watermark_color_mode"] == "RGB"

    # Verify reconstructed image matches original
    extracted_wm_path = PROJECT_ROOT / extract_res["extracted_watermark"].lstrip("/")
    extracted_wm_img = cv2.imread(str(extracted_wm_path))
    assert np.array_equal(wm, extracted_wm_img), "Extracted watermark does not match ground truth!"


def test_capacity_deficit_rejection():
    """Verify that an oversized watermark is rejected before cover modification with exact deficit."""
    # Tiny cover image: 64x64 -> 8x8 = 64 blocks
    # Tiny cover image: 40x40 -> 5x5 = 25 blocks (118 bytes usable capacity)
    small_cover = np.random.randint(50, 200, (40, 40, 3), dtype=np.uint8)

    # Watermark with random noise that won't compress below 5 KB
    large_wm = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    raised = False
    try:
        watermark_image(small_cover, large_wm)
    except ValueError as e:
        raised = True
        err_msg = str(e)
        assert "exceeds carrier capacity" in err_msg
        assert "deficit" in err_msg.lower()
    assert raised, "Expected ValueError was not raised for oversized payload!"


def test_unwatermarked_image_error():
    """Verify that supplying an unwatermarked image to extract_only raises an informative error."""
    unwatermarked = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    raised = False
    try:
        extract_only(unwatermarked)
    except ValueError as e:
        raised = True
        assert "No valid JND watermarking header detected" in str(e)
def test_real_files_roundtrip():
    """Verify end-to-end watermarking with real input files if available."""
    cover_path = Path(__file__).resolve().parent.parent / "input" / "test_image.jpeg"
    wm_path = Path(__file__).resolve().parent.parent / "input" / "watermark.png"
    if not cover_path.exists() or not wm_path.exists():
        print(" [SKIP] Sample input files not found")
        return

    result = watermark_image(cover_path, wm_path)
    assert result["success"] is True
    assert result["metrics"]["bit_accuracy"] == 100.0
    assert result["metrics"]["normalized_correlation"] == 1.0
    assert result["metrics"]["psnr"] > 35.0

    # Also test extract_only on the output image
    out_img_path = Path(__file__).resolve().parent.parent / "output" / Path(result["watermarked_image"]).name
    ext_result = extract_only(out_img_path)
    assert ext_result["success"] is True
    assert ext_result["metadata"]["watermark_width"] == result["metadata"]["watermark_width"]
    assert ext_result["metadata"]["watermark_height"] == result["metadata"]["watermark_height"]


if __name__ == "__main__":
    tests = [
        test_serialization_roundtrip_grayscale,
        test_serialization_roundtrip_rgb,
        test_carrier_capacity_calculation,
        test_full_roundtrip_grayscale_watermark,
        test_full_roundtrip_rgb_color_watermark,
        test_odd_resolution_cover_preservation,
        test_extraction_only_mode,
        test_capacity_deficit_rejection,
        test_unwatermarked_image_error,
        test_real_files_roundtrip,
    ]
    passed = 0
    failed = 0
    print(f"Running {len(tests)} test cases for arbitrary-image watermarking...")
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f" [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*50)
    print(f"Test Results: {passed} passed, {failed} failed.")
    print("="*50)
    sys.exit(0 if failed == 0 else 1)
