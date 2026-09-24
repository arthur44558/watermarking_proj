"""
Integration tests for Flask Web API endpoints.
Tests /api/config, /api/capacity, and /api/watermark in embed and extract-only modes.
"""

import io
import sys
from pathlib import Path
import numpy as np
import cv2

# Add src to path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from web.app import create_app


def image_to_bytes(img: np.ndarray, ext: str = ".png") -> io.BytesIO:
    success, enc = cv2.imencode(ext, img)
    if not success:
        raise ValueError("Failed to encode image")
    return io.BytesIO(enc.tobytes())


def test_api_config():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    cfg = data["configuration"]
    assert cfg["bits_per_block"] == 16
    assert cfg["max_payload_bytes"] is None
    print(" [PASS] test_api_config")


def test_api_capacity():
    app = create_app()
    client = app.test_client()

    cover = np.zeros((300, 400, 3), dtype=np.uint8)
    cover_io = image_to_bytes(cover, ".png")

    resp = client.post(
        "/api/capacity",
        data={"cover_image": (cover_io, "cover.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    cap = data["capacity"]
    assert cap["cover_width"] == 400
    assert cap["cover_height"] == 300
    assert cap["usable_y_capacity_bytes"] > 0
    print(" [PASS] test_api_capacity")


def test_api_watermark_embed_and_extract():
    app = create_app()
    client = app.test_client()

    # Create cover and watermark
    cover = np.random.randint(40, 200, (200, 200, 3), dtype=np.uint8)
    wm = np.full((32, 32, 3), (255, 128, 64), dtype=np.uint8)

    cover_io = image_to_bytes(cover, ".png")
    wm_io = image_to_bytes(wm, ".png")

    # Mode A: Embed
    resp = client.post(
        "/api/watermark",
        data={
            "cover_image": (cover_io, "cover.png"),
            "watermark_image": (wm_io, "wm.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200, f"Embed failed: {resp.get_json()}"
    data = resp.get_json()
    assert data["success"] is True
    assert data["mode"] == "embed_and_verify"
    assert "watermarked_image" in data
    assert "extracted_watermark" in data
    assert data["metrics"]["bit_accuracy"] == 100.0
    assert data["metrics"]["normalized_correlation"] == 1.0

    # Retrieve watermarked image bytes from server
    img_resp = client.get(data["watermarked_image"])
    assert img_resp.status_code == 200
    watermarked_bytes = img_resp.data

    # Mode B: Extract Only
    resp_ext = client.post(
        "/api/watermark",
        data={
            "cover_image": (io.BytesIO(watermarked_bytes), "watermarked.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp_ext.status_code == 200, f"Extract failed: {resp_ext.get_json()}"
    ext_data = resp_ext.get_json()
    assert ext_data["success"] is True
    assert ext_data["mode"] == "extract_only"
    assert ext_data["metrics"]["bit_accuracy"] is None
    assert ext_data["metrics"]["normalized_correlation"] is None
    print(" [PASS] test_api_watermark_embed_and_extract")


def test_api_capacity_deficit():
    app = create_app()
    client = app.test_client()

    small_cover = np.zeros((40, 40, 3), dtype=np.uint8)
    large_wm = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)

    cover_io = image_to_bytes(small_cover, ".png")
    wm_io = image_to_bytes(large_wm, ".png")

    resp = client.post(
        "/api/watermark",
        data={
            "cover_image": (cover_io, "cover.png"),
            "watermark_image": (wm_io, "wm.png"),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
    assert "exceeds" in data["error"].lower()
    assert "deficit" in data["error"].lower()
    print(" [PASS] test_api_capacity_deficit")


if __name__ == "__main__":
    print("Running Flask Web API integration tests...")
    test_api_config()
    test_api_capacity()
    test_api_watermark_embed_and_extract()
    test_api_capacity_deficit()
    print("\nAll Web API integration tests passed successfully!")
