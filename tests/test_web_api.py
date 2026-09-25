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


def test_frontend_progress_bar_elements_present():
    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Core progress card elements
    assert 'id="processingProgressCard"' in html
    assert 'id="progressBarFill"' in html
    assert 'id="progressPercentBadge"' in html
    assert 'id="progressStageBadge"' in html
    assert 'id="progressTimer"' in html
    assert 'id="progressStepText"' in html
    assert 'id="progressSubDetail"' in html

    # Result overlay mini progress bar elements
    assert 'id="overlayProgressContainer"' in html
    assert 'id="overlayProgressBarFill"' in html
    assert 'id="overlayProgressPercent"' in html

    # CRC enforcement toggle element
    assert 'id="enforceCrcToggle"' in html
    print(" [PASS] test_frontend_progress_bar_elements_present")


def test_api_watermark_crc_toggle():
    """Verify Web API handles enforce_crc toggle on and off properly on CRC mismatch."""
    from watermarking.payload import serialize_watermark
    from watermarking.embedding import embed_image_payload

    app = create_app()
    client = app.test_client()

    cover = np.full((160, 160, 3), 128, dtype=np.uint8)
    wm = np.full((24, 24, 3), (210, 120, 60), dtype=np.uint8)

    payload = serialize_watermark(wm, channels_used=1)
    corrupted_byte = bytes([payload[35] ^ 0xFF])
    bad_payload = payload[:35] + corrupted_byte + payload[36:]

    bad_carrier, _ = embed_image_payload(cover, bad_payload, channels_used=1)

    # 1. POST /api/watermark with enforce_crc=false -> HTTP 200, crc_match=False
    resp = client.post(
        "/api/watermark",
        data={
            "cover_image": (image_to_bytes(bad_carrier, ".png"), "bad_carrier.png"),
            "enforce_crc": "false",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["crc_match"] is False
    assert "mismatch" in data["crc_status"].lower()
    assert data["enforce_crc"] is False
    assert "extracted_watermark" in data

    # 2. POST /api/watermark with enforce_crc=true -> HTTP 400 with error
    resp_fail = client.post(
        "/api/watermark",
        data={
            "cover_image": (image_to_bytes(bad_carrier, ".png"), "bad_carrier.png"),
            "enforce_crc": "true",
        },
        content_type="multipart/form-data",
    )
    assert resp_fail.status_code == 400
    fail_data = resp_fail.get_json()
    assert fail_data["success"] is False
    assert "crc32 mismatch" in fail_data["error"].lower() or "corrupted" in fail_data["error"].lower()
    print(" [PASS] test_api_watermark_crc_toggle")


def test_api_video_crc_toggle():
    """Verify Web API video processing handles enforce_crc toggle on and off properly."""
    import tempfile
    from pathlib import Path
    import io
    from watermarking.payload import serialize_watermark
    from watermarking.embedding import embed_image_payload
    from watermarking.video import create_video_writer

    app = create_app()
    client = app.test_client()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        wm = np.full((16, 16), 180, dtype=np.uint8)
        payload = serialize_watermark(wm, channels_used=1)
        corrupted_byte = bytes([payload[35] ^ 0xFF])
        bad_payload = payload[:35] + corrupted_byte + payload[36:]

        corrupt_vid_base = tmp_path / "corrupt_api_vid"
        writer, corrupt_vid_path, _ = create_video_writer(corrupt_vid_base, 160, 120, 25.0)
        try:
            for _ in range(4):
                frame = np.full((120, 160, 3), 120, dtype=np.uint8)
                bad_frame, _ = embed_image_payload(frame, bad_payload, channels_used=1)
                writer.write(bad_frame)
        finally:
            writer.release()

        with open(corrupt_vid_path, "rb") as f:
            vid_bytes = f.read()

        # 1. With enforce_crc="false" -> HTTP 200, crc_match=False
        resp = client.post(
            "/api/watermark",
            data={
                "cover_image": (io.BytesIO(vid_bytes), "corrupt_vid.mp4"),
                "enforce_crc": "false",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["media_type"] == "video"
        assert data["crc_match"] is False
        assert "mismatch" in data["crc_status"].lower()
        assert data["enforce_crc"] is False
        assert "extracted_watermark" in data

        # 2. With enforce_crc="true" -> HTTP 400
        resp_fail = client.post(
            "/api/watermark",
            data={
                "cover_image": (io.BytesIO(vid_bytes), "corrupt_vid.mp4"),
                "enforce_crc": "true",
            },
            content_type="multipart/form-data",
        )
        assert resp_fail.status_code == 400
        fail_data = resp_fail.get_json()
        assert fail_data["success"] is False
        assert "watermark extraction failed" in fail_data["error"].lower() or "crc32 mismatch" in fail_data["error"].lower()
        print(" [PASS] test_api_video_crc_toggle")


if __name__ == "__main__":
    print("Running Flask Web API integration tests...")
    test_api_config()
    test_api_capacity()
    test_api_watermark_embed_and_extract()
    test_api_capacity_deficit()
    test_frontend_progress_bar_elements_present()
    test_api_watermark_crc_toggle()
    test_api_video_crc_toggle()
    print("\nAll Web API integration tests passed successfully!")

