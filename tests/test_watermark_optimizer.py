import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from watermarking.optimizer import optimize_watermark, is_near_monochrome
from watermarking.config import CODEC_RAW_ZLIB, CODEC_WEBP

def test_near_monochrome_rgb_to_grayscale():
    # Create a 50x50 RGB image that is practically monochrome
    img = np.full((50, 50, 3), 100, dtype=np.uint8)
    # Add a slight color difference within tolerance
    img[0, 0, 0] = 104
    
    assert is_near_monochrome(img) is True
    
    # Try optimizing it with a large capacity
    res = optimize_watermark(img, 1000000)
    assert len(res["optimized_img"].shape) == 2 or res["optimized_img"].shape[2] == 1
    assert "Grayscale" in res["summary_text"]

def test_small_watermark_fits_losslessly():
    # Small 10x10 binary image
    img = np.zeros((10, 10), dtype=np.uint8)
    img[2:8, 2:8] = 255
    
    # Needs some space for header and small zlib payload
    capacity = 1024 
    res = optimize_watermark(img, capacity)
    
    assert res["codec_id"] == CODEC_RAW_ZLIB
    assert res["quality"] == 100
    assert res["scale_percent"] == 100
    assert res["status"] == "No compression needed"
    assert res["applied"] is False

def test_moderate_watermark_quality_search():
    # Random noise is hard to compress
    np.random.seed(42)
    img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    # Check RAW_ZLIB size
    from watermarking.payload import serialize_watermark
    raw_payload = serialize_watermark(img, codec=CODEC_RAW_ZLIB, quality=100, orig_width=100, orig_height=100)
    raw_size = len(raw_payload)
    
    # Give it less capacity than raw size, but enough for WebP
    capacity = int(raw_size * 0.7)
    
    res = optimize_watermark(img, capacity)
    
    assert res["codec_id"] == CODEC_WEBP
    assert res["scale_percent"] == 100
    assert res["quality"] < 100
    assert res["applied"] is True

def test_large_watermark_auto_downscaled():
    # Large 500x500 image
    np.random.seed(42)
    img = np.random.randint(0, 256, (500, 500), dtype=np.uint8)
    
    # Tiny capacity
    capacity = 2048
    
    res = optimize_watermark(img, capacity)
    
    assert res["codec_id"] == CODEC_WEBP
    assert res["scale_percent"] < 100
    assert res["applied"] is True
    assert res["optimized_width"] < 500
    assert res["optimized_height"] < 500

def test_rejection_when_carrier_too_small():
    # Create image
    img = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    # Extremely small capacity, not even enough for the 32-byte header
    capacity = 20
    
    with pytest.raises(ValueError, match="Watermark payload exceeds carrier capacity"):
        optimize_watermark(img, capacity)
