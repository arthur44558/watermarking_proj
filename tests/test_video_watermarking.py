"""
Comprehensive test suite for Stage 1 fastest video watermarking implementation.
Verifies:
  - Video stream inspection and capacity estimation
  - Frame-by-frame memory-safe sequential CPU processing
  - Threaded CPU bounded pipeline processing
  - Preservation of width, height, FPS, frame count, and frame order
  - Multi-frame blind extraction and CRC32 verification
  - Bounded memory usage (RSS tracking)
  - Video API endpoints (/api/capacity, /api/watermark)
  - Edge cases (capacity deficit, empty files, corrupt streams)
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

from watermarking.video import (
    get_video_info,
    calculate_video_carrier_capacity,
    create_video_writer,
    watermark_video,
    extract_video_watermark,
    benchmark_video_processing,
    get_current_ram_mb,
)
from watermarking.config import BLOCK_SIZE, BYTES_PER_BLOCK, HEADER_SIZE_BYTES
from web.app import create_app


def generate_synthetic_video(
    output_path: Path,
    width: int = 320,
    height: int = 240,
    fps: float = 30.0,
    num_frames: int = 30,
) -> Path:
    """
    Generate a synthetic multi-frame video with moving patterns for reproducible testing.
    Uses candidate codecs (mp4v -> MJPG) supported by the environment.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    actual_path = output_path
    codecs_to_try = [
        ("FFV1", ".avi"),
        ("mp4v", ".mp4"),
        ("MJPG", ".avi"),
        ("XVID", ".avi"),
    ]
    for c_code, c_ext in codecs_to_try:
        cand_path = output_path.with_suffix(c_ext)
        fourcc = cv2.VideoWriter_fourcc(*c_code)
        cand_writer = cv2.VideoWriter(str(cand_path), fourcc, fps, (width, height))
        if cand_writer.isOpened():
            writer = cand_writer
            actual_path = cand_path
            break

    if writer is None or not writer.isOpened():
        raise RuntimeError(f"Could not initialize VideoWriter for synthetic video {width}x{height}")

    np.random.seed(42)
    for i in range(num_frames):
        frame = np.full((height, width, 3), 100, dtype=np.uint8)
        # Add dynamic scene features: moving circle and gradient
        cx = int((i * 8) % (width - 40) + 20)
        cy = int((i * 6) % (height - 40) + 20)
        cv2.circle(frame, (cx, cy), 18, (0, 0, 255), -1)
        cv2.rectangle(frame, (10, 10), (width - 10, height - 10), (200, 150, 50), 2)
        cv2.putText(frame, f"F:{i:03d}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        writer.write(frame)

    writer.release()
    return actual_path


def create_synthetic_watermark(width: int = 40, height: int = 24) -> np.ndarray:
    """Generate a clean synthetic watermark logo for embedding."""
    wm = np.full((height, width, 3), 220, dtype=np.uint8)
    cv2.rectangle(wm, (2, 2), (width - 3, height - 3), (20, 20, 200), -1)
    cv2.putText(wm, "JND", (4, height - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    return wm


def test_video_info_and_capacity():
    """Verify video inspection and capacity calculations on synthetic video."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "test_input.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=320, height=240, fps=25.0, num_frames=20)

        info = get_video_info(actual_vid)
        assert info["width"] == 320
        assert info["height"] == 240
        assert info["fps"] == 25.0
        assert info["frame_count"] == 20
        assert info["duration_sec"] == 0.8

        cap = calculate_video_carrier_capacity(actual_vid)
        assert cap["is_video"] is True
        assert cap["cover_width"] == 320
        assert cap["cover_height"] == 240
        # 320x240 has (320//8) * (240//8) = 40 * 30 = 1200 blocks
        assert cap["total_carrier_blocks"] == 1200
        # 1200 blocks * 2 bytes/block - 32 bytes header = 2368 bytes
        assert cap["usable_y_capacity_bytes"] == 1200 * 2 - 32


def test_sequential_video_watermarking():
    """Verify baseline sequential CPU video watermarking pipeline."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "seq_input.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=320, height=240, fps=30.0, num_frames=15)
        wm = create_synthetic_watermark(width=32, height=20)

        result = watermark_video(
            actual_vid,
            wm,
            output_dir=tmp_path / "out",
            mode="sequential",
        )

        assert result["success"] is True
        assert result["mode"] == "embed_and_verify"
        assert result["media_type"] == "video"
        assert result["performance"]["processing_mode"] == "sequential"
        assert result["performance"]["average_fps"] > 0
        assert result["performance"]["peak_ram_mb"] > 0
        assert result["video_info"]["width"] == 320
        assert result["video_info"]["height"] == 240
        assert result["video_info"]["frame_count"] == 15
        assert result["extraction"]["status"] == "Success"
        assert result["extraction"]["crc_status"] == "Passed (CRC32 Verified)"
        assert result["metrics"]["bit_accuracy"] == 100.0
        assert result["metrics"]["normalized_correlation"] > 0.99
        assert result["metrics"]["psnr"] > 35.0


def test_threaded_video_watermarking():
    """Verify bounded multithreaded CPU video watermarking pipeline."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "threaded_input.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=320, height=240, fps=30.0, num_frames=25)
        wm = create_synthetic_watermark(width=32, height=20)

        result = watermark_video(
            actual_vid,
            wm,
            output_dir=tmp_path / "out",
            mode="threaded",
            max_workers=2,
        )

        assert result["success"] is True
        assert result["media_type"] == "video"
        assert "threaded" in result["performance"]["processing_mode"]
        assert result["video_info"]["processed_frames"] == 25
        assert result["extraction"]["status"] == "Success"
        assert result["extraction"]["crc_status"] == "Passed (CRC32 Verified)"
        assert result["extraction"]["payload_consistent"] is True
        assert result["metrics"]["bit_accuracy"] == 100.0


def test_video_watermark_multi_frame_extraction():
    """Verify multi-frame sampling extraction and payload consistency across frames."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "extract_test.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=320, height=240, fps=25.0, num_frames=20)
        wm = create_synthetic_watermark(width=32, height=20)

        res = watermark_video(actual_vid, wm, output_dir=tmp_path / "out", mode="sequential")
        watermarked_path = Path(res["watermarked_video_path"])
        assert watermarked_path.exists()

        # Run multi-frame extraction directly
        ext = extract_video_watermark(watermarked_path, output_dir=tmp_path / "out", max_samples=5)
        assert ext["extraction_status"] == "Success"
        assert ext["crc_status"] == "Passed (CRC32 Verified)"
        assert ext["valid_sampled_frames"] > 0
        assert ext["payload_consistent"] is True
        assert Path(ext["extracted_watermark_path"]).exists()


def test_video_memory_stability():
    """Verify memory remains bounded across frames (no accumulation in memory)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "mem_test.mp4"
        # 40 frames to check memory stability over time
        actual_vid = generate_synthetic_video(vid_file, width=240, height=160, fps=30.0, num_frames=40)
        wm = create_synthetic_watermark(width=24, height=16)

        ram_readings = []

        def on_progress(cur, total, fps, ram):
            ram_readings.append(ram)

        res = watermark_video(
            actual_vid,
            wm,
            output_dir=tmp_path / "out",
            mode="sequential",
            progress_callback=on_progress,
        )

        assert res["success"] is True
        # Verify RAM increase is bounded (should not grow linearly)
        if len(ram_readings) >= 3:
            # Difference between early reading and late reading should be bounded
            ram_diff = ram_readings[-1] - ram_readings[0]
            assert ram_diff < 150.0  # RSS increase must remain well within sane boundary (<150 MB)


def test_video_capacity_deficit():
    """Verify clean rejection with ValueError when watermark exceeds video frame capacity."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "tiny_input.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=32, height=32, fps=30.0, num_frames=5)
        # Giant watermark with random noise that cannot fit into 32x32 frame (4x4 = 16 blocks = 32 bytes max)
        np.random.seed(99)
        huge_wm = np.random.randint(0, 256, (120, 120, 3), dtype=np.uint8)

        with pytest.raises(ValueError, match="exceeds carrier capacity"):
            watermark_video(actual_vid, huge_wm, output_dir=tmp_path / "out")


def test_benchmark_utility():
    """Verify benchmark utility runs and records sequential vs threaded metrics."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "bench_input.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=200, height=150, fps=25.0, num_frames=10)
        wm = create_synthetic_watermark(width=20, height=16)

        bench = benchmark_video_processing(actual_vid, wm, output_dir=tmp_path / "out")
        assert "sequential_1w" in bench
        assert "threaded_2w" in bench
        assert bench["sequential_1w"]["avg_fps"] > 0
        assert bench["threaded_2w"]["avg_fps"] > 0


def test_flask_api_video_watermarking():
    """Test Flask /api/watermark and /api/capacity integration with uploaded video files."""
    app = create_app()
    client = app.test_client()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "api_test.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=240, height=160, fps=25.0, num_frames=10)
        wm = create_synthetic_watermark(width=24, height=16)

        success, enc_wm = cv2.imencode(".png", wm)
        assert success
        wm_bytes = enc_wm.tobytes()

        # 1. Capacity endpoint with video
        with open(actual_vid, "rb") as vf:
            resp_cap = client.post(
                "/api/capacity",
                data={"cover_image": (vf, "test_video.mp4")},
                content_type="multipart/form-data",
            )
        assert resp_cap.status_code == 200
        cap_data = resp_cap.get_json()
        assert cap_data["success"] is True
        assert cap_data["capacity"]["is_video"] is True
        assert cap_data["capacity"]["cover_width"] == 240
        assert cap_data["capacity"]["cover_height"] == 160

        # 2. Watermark video embed endpoint
        with open(actual_vid, "rb") as vf:
            import io
            resp = client.post(
                "/api/watermark",
                data={
                    "cover_image": (vf, "test_video.mp4"),
                    "watermark_image": (io.BytesIO(wm_bytes), "wm.png"),
                    "mode": "threaded",
                },
                content_type="multipart/form-data",
            )
        assert resp.status_code == 200, f"Video watermarking failed: {resp.get_json()}"
        res_data = resp.get_json()
        assert res_data["success"] is True
        assert res_data["media_type"] == "video"
        assert res_data["watermarked_video"].startswith("/output/")
        assert res_data["extracted_watermark"].startswith("/output/")
        assert res_data["extraction"]["status"] == "Success"
        assert res_data["extraction"]["crc_status"] == "Passed (CRC32 Verified)"

        # 3. Watermarked video can be fetched from /output/
        vid_serve_resp = client.get(res_data["watermarked_video"])
        assert vid_serve_resp.status_code == 200
        assert len(vid_serve_resp.data) > 0

        # 4. Extract-only mode with video
        resp_ext = client.post(
            "/api/watermark",
            data={
                "cover_image": (io.BytesIO(vid_serve_resp.data), "watermarked.mp4"),
            },
            content_type="multipart/form-data",
        )
        assert resp_ext.status_code == 200
        ext_json = resp_ext.get_json()
        assert ext_json["success"] is True
        assert ext_json["mode"] == "extract_only"
        assert ext_json["media_type"] == "video"
        assert ext_json["extraction"]["status"] == "Success"


def test_video_extraction_crc_toggle():
    """Verify video extraction with CRC toggle on (enforce_crc=True) and off (enforce_crc=False)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_file = tmp_path / "crc_toggle_vid.mp4"
        actual_vid = generate_synthetic_video(vid_file, width=320, height=240, fps=25.0, num_frames=10)
        wm = create_synthetic_watermark(width=24, height=16)

        # 1. Standard watermark_video with enforce_crc=False propagated
        res = watermark_video(actual_vid, wm, output_dir=tmp_path / "out", mode="sequential", enforce_crc=False)
        assert res["success"] is True
        assert res["enforce_crc"] is False
        assert res["crc_match"] is True
        assert res["extraction"]["crc_status"] == "Passed (CRC32 Verified)"

        # 2. Build corrupted video frames where CRC mismatches
        from watermarking.payload import serialize_watermark
        from watermarking.embedding import embed_image_payload
        payload = serialize_watermark(wm, channels_used=1)
        corrupted_byte = bytes([payload[35] ^ 0xFF])
        bad_payload = payload[:35] + corrupted_byte + payload[36:]

        corrupt_vid_base = tmp_path / "corrupt_vid"
        writer, corrupt_vid_path, _ = create_video_writer(corrupt_vid_base, 320, 240, 25.0)
        try:
            for _ in range(5):
                frame = np.full((240, 320, 3), 120, dtype=np.uint8)
                bad_frame, _ = embed_image_payload(frame, bad_payload, channels_used=1)
                writer.write(bad_frame)
        finally:
            writer.release()

        # 3. With enforce_crc=True, extract_video_watermark must raise ValueError
        with pytest.raises(ValueError, match="Watermark extraction failed|CRC32 mismatch|corrupted"):
            extract_video_watermark(corrupt_vid_path, output_dir=tmp_path / "out", enforce_crc=True)

        # 4. With enforce_crc=False, extract_video_watermark must succeed and show CRC mismatch
        ext = extract_video_watermark(corrupt_vid_path, output_dir=tmp_path / "out", enforce_crc=False)
        assert ext["extraction_status"] == "Success"
        assert ext["crc_match"] is False
        assert "mismatch" in ext["crc_status"].lower()
        assert ext["enforce_crc"] is False
        assert Path(ext["extracted_watermark_path"]).exists()


if __name__ == "__main__":
    tests = [
        test_video_info_and_capacity,
        test_sequential_video_watermarking,
        test_threaded_video_watermarking,
        test_video_watermark_multi_frame_extraction,
        test_video_memory_stability,
        test_video_capacity_deficit,
        test_benchmark_utility,
        test_flask_api_video_watermarking,
        test_video_extraction_crc_toggle,
    ]
    passed = 0
    failed = 0
    print(f"Running {len(tests)} test cases for Stage 1 video watermarking...")
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

    print("\n" + "=" * 50)
    print(f"Video Test Results: {passed} passed, {failed} failed.")
    print("=" * 50)
    sys.exit(0 if failed == 0 else 1)
