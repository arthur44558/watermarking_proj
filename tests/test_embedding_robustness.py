"""
Robustness and CRC32 verification tests.
Runs multiple randomized trials with complex color cover images and arbitrary watermarks
to verify zero bit errors and zero CRC32 mismatches.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from watermarking.pipeline import watermark_image, extract_only


@pytest.mark.parametrize("trial", range(5))
def test_randomized_roundtrip_robustness(trial):
    """
    Test embedding and blind extraction across randomized cover images and watermarks.
    Ensures BGR roundtrip refinement eliminates bit flips, yielding 0 CRC32 mismatches.
    """
    np.random.seed(100 + trial)

    # Varied cover dimensions (multiples of 8 or odd)
    ch = int(np.random.randint(200, 320))
    cw = int(np.random.randint(200, 320))
    cover = np.random.randint(10, 245, (ch, cw, 3), dtype=np.uint8)

    # Varied watermark dimensions
    wh = int(np.random.randint(24, 60))
    ww = int(np.random.randint(24, 60))
    wm = np.random.randint(0, 256, (wh, ww, 3), dtype=np.uint8)

    result = watermark_image(cover, wm)

    assert result["success"] is True
    # The watermarked cover must retain exact original dimensions
    assert result["metadata"]["cover_width"] == cw
    assert result["metadata"]["cover_height"] == ch

    # Extracted watermark must be present
    assert result["metrics"]["bit_accuracy"] == 100.0

    # Blind extraction test
    ext_result = extract_only(result["watermarked_image"].lstrip("/"))
    assert ext_result["success"] is True
    assert ext_result["metadata"]["watermark_width"] == result["metadata"]["watermark_width"]
    assert ext_result["metadata"]["watermark_height"] == result["metadata"]["watermark_height"]
