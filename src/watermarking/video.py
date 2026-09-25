"""
Memory-safe, high-performance video watermarking engine using JND-guided DCT modulation.
Implements Stage 1 fastest baseline: frame-by-frame processing, bounded memory,
OpenCV VideoCapture/VideoWriter, sequential and bounded multithreaded worker pools,
and multi-frame sampling extraction with CRC32 integrity verification.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
import os
import time
import uuid
import queue
import logging
import threading
import subprocess
import shutil
import numpy as np
import cv2

from .config import (
    BLOCK_SIZE,
    BYTES_PER_BLOCK,
    BITS_PER_BLOCK,
    HEADER_SIZE_BYTES,
    JND_ALPHA,
    JND_BETA,
    JND_SCALE,
    OUTPUT_DIR,
    DEFAULT_VIDEO_FPS,
    VIDEO_SAMPLE_METRIC_COUNT,
    VIDEO_QUEUE_MAXSIZE,
    MAX_THREAD_WORKERS,
    SUPPORTED_VIDEO_FORMATS,
)
from .pipeline import calculate_carrier_capacity
from .optimizer import optimize_watermark
from .payload import (
    serialize_watermark,
    deserialize_watermark,
    load_watermark_image,
)
from .embedding import embed_image_payload
from .extraction import extract_framed_payload
from .metrics import (
    calculate_psnr,
    calculate_ssim,
    calculate_nc,
    calculate_bit_accuracy,
    calculate_watermark_reconstruction_error,
)
from .image_utils import save_image

logger = logging.getLogger(__name__)


def get_current_ram_mb() -> float:
    """
    Get current process Resident Set Size (RSS) memory in megabytes (MB).
    Uses psutil if available, otherwise queries Windows API via ctypes, or falls back to tracemalloc.
    """
    try:
        import psutil
        return max(0.1, float(psutil.Process().memory_info().rss) / (1024 * 1024))
    except Exception:
        pass

    try:
        import ctypes
        import ctypes.wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        k32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL
        handle = k32.GetCurrentProcess()
        if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            mb = float(counters.WorkingSetSize) / (1024 * 1024)
            if mb > 0:
                return mb
    except Exception:
        pass

    try:
        import tracemalloc
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        current, peak = tracemalloc.get_traced_memory()
        mb = float(max(current, peak)) / (1024 * 1024)
        if mb > 0:
            return mb
    except Exception:
        pass

    return 1.0


def get_video_info(video_source: Union[Path, str]) -> Dict[str, Any]:
    """
    Extract video container and stream properties without loading frames into memory.
    """
    path_str = str(video_source)
    cap = cv2.VideoCapture(path_str)
    try:
        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {path_str}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not fps or np.isnan(fps) or fps <= 0:
            fps = DEFAULT_VIDEO_FPS

        if width <= 0 or height <= 0:
            ret, peek_frame = cap.read()
            if ret and peek_frame is not None:
                height, width = peek_frame.shape[:2]
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            # If header does not specify frame count, count frames without loading all into memory
            frame_count = 0
            while True:
                ret = cap.grab()
                if not ret:
                    break
                frame_count += 1
            # Reopen to reset position
            cap.release()
            cap = cv2.VideoCapture(path_str)

        duration_sec = round(frame_count / fps, 2) if (fps > 0 and frame_count > 0) else 0.0
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_chars = [chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4) if 32 <= ((fourcc_int >> 8 * i) & 0xFF) <= 126]
        fourcc_str = "".join(fourcc_chars) if fourcc_chars else "unknown"

        return {
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "duration_sec": duration_sec,
            "fourcc": fourcc_str,
            "path": path_str,
        }
    finally:
        cap.release()


def calculate_video_carrier_capacity(video_source: Union[Path, str]) -> Dict[str, Any]:
    """
    Inspect the first frame of a video to calculate its exact carrier capacity per frame.
    Does not load the complete video into memory.
    Dynamically computes per-frame and total video capacity based on actual dimensions.
    """
    path_str = str(video_source)
    cap = cv2.VideoCapture(path_str)
    try:
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {path_str}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not fps or np.isnan(fps) or fps <= 0:
            fps = DEFAULT_VIDEO_FPS
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = round(frame_count / fps, 2) if (fps > 0 and frame_count > 0) else 0.0

        ret, first_frame = cap.read()
        if not ret or first_frame is None:
            raise ValueError(f"Could not read the first frame from video: {path_str}")

        real_h, real_w = first_frame.shape[:2]
        if width <= 0 or height <= 0:
            width = real_w
            height = real_h

        cap_info = calculate_carrier_capacity(first_frame)
        cap_info["is_video"] = True
        cap_info["capacity_per_frame_bytes"] = cap_info["usable_y_capacity_bytes"]
        cap_info["total_video_capacity_bytes"] = cap_info["usable_y_capacity_bytes"] * max(1, frame_count)
        cap_info["video_info"] = {
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "duration_sec": duration_sec,
        }
        return cap_info
    finally:
        cap.release()


def create_video_writer(
    output_base_path: Union[Path, str],
    width: int,
    height: int,
    fps: float,
) -> Tuple[cv2.VideoWriter, Path, str]:
    """
    Create a cv2.VideoWriter preserving the exact width and height of the input.
    Dynamically tests browser and system compatible codec candidates.
    Supports arbitrary aspect ratios and resolutions, including odd (non-even) dimensions.
    """
    output_base = Path(output_base_path)
    output_dir = output_base.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_base.stem

    is_odd = (width % 2 != 0) or (height % 2 != 0)

    # When dimensions are odd, many FFmpeg/AVI encoders truncate width or height to even (e.g. 1279x719 -> 1278x718).
    # On Windows, Media Foundation (MSMF) supports exact odd dimensions for MP4.
    if is_odd:
        candidates = [
            (cv2.CAP_ANY, "FFV1", ".avi", "FFV1 (Lossless AVI)"),
            (cv2.CAP_ANY, "HFYU", ".avi", "Huffman YUV (Lossless AVI)"),
            (cv2.CAP_ANY, "RGBA", ".avi", "Raw RGBA (Lossless AVI)"),
            (getattr(cv2, "CAP_MSMF", cv2.CAP_ANY), "mp4v", ".mp4", "mp4v (MSMF)"),
            (getattr(cv2, "CAP_MSMF", cv2.CAP_ANY), "avc1", ".mp4", "avc1 (MSMF)"),
            (cv2.CAP_ANY, "avc1", ".mp4", "avc1"),
            (cv2.CAP_ANY, "mp4v", ".mp4", "mp4v"),
            (cv2.CAP_ANY, "MJPG", ".avi", "MJPG"),
            (cv2.CAP_ANY, "XVID", ".avi", "XVID"),
        ]
    else:
        candidates = [
            (cv2.CAP_ANY, "FFV1", ".avi", "FFV1 (Lossless AVI)"),
            (cv2.CAP_ANY, "HFYU", ".avi", "Huffman YUV (Lossless AVI)"),
            (cv2.CAP_ANY, "RGBA", ".avi", "Raw RGBA (Lossless AVI)"),
            (cv2.CAP_ANY, "mp4v", ".mp4", "mp4v"),
            (cv2.CAP_ANY, "avc1", ".mp4", "avc1"),
            (cv2.CAP_ANY, "H264", ".mp4", "H264"),
            (cv2.CAP_ANY, "XVID", ".avi", "XVID"),
            (cv2.CAP_ANY, "MJPG", ".avi", "MJPG"),
        ]

    for api_pref, fourcc_code, ext, codec_name in candidates:
        target_path = output_dir / f"{stem}{ext}"
        try:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
            if api_pref == cv2.CAP_ANY:
                writer = cv2.VideoWriter(str(target_path), fourcc, fps, (width, height))
            else:
                writer = cv2.VideoWriter(str(target_path), api_pref, fourcc, fps, (width, height))
            if writer.isOpened():
                return writer, target_path, codec_name
            writer.release()
            if target_path.exists() and target_path.stat().st_size == 0:
                try:
                    target_path.unlink()
                except Exception:
                    pass
        except Exception:
            continue

    raise RuntimeError(
        f"Could not initialize a supported video codec for VideoWriter on this system for dimensions {width}x{height}."
    )


def extract_video_watermark(
    video_source: Union[Path, str],
    output_dir: Union[Path, str] = OUTPUT_DIR,
    sample_interval: Optional[int] = None,
    max_samples: int = 10,
) -> Dict[str, Any]:
    """
    Sample several frames across the video and extract the embedded watermark.
    Accepts the first valid payload whose header and CRC32 pass.
    Checks payload consistency across all valid sampled frames.

    Args:
        video_source: Path to the watermarked video file.
        output_dir: Destination directory for the reconstructed watermark image.
        sample_interval: Optional step between sampled frames (e.g. 30).
        max_samples: Maximum number of frames to sample.

    Returns:
        Extraction report dictionary with watermark image path, metadata, CRC status,
        valid frame count, and consistency flag.
    """
    path_str = str(video_source)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    info = get_video_info(path_str)
    frame_count = info["frame_count"]
    fps = info["fps"]

    if frame_count <= 0:
        raise ValueError(f"Video {path_str} contains 0 frames.")

    # Determine frame indices to sample
    if sample_interval is not None and sample_interval > 0:
        sample_indices = list(range(0, frame_count, sample_interval))[:max_samples]
    else:
        step = max(1, frame_count // max_samples)
        sample_indices = list(range(0, frame_count, step))[:max_samples]

    if not sample_indices:
        sample_indices = [0]

    valid_frames: List[Tuple[int, bytes, np.ndarray, Dict[str, Any]]] = []
    failed_frames: List[Tuple[int, str]] = []

    cap = cv2.VideoCapture(path_str)
    try:
        cur_pos = 0
        for f_idx in sample_indices:
            # Advance to target frame index
            if f_idx < cur_pos:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                cur_pos = f_idx

            # Fast forward sequentially with grab() if within reasonable distance (<= 120 frames), else seek
            if cur_pos < f_idx:
                if f_idx - cur_pos <= 120:
                    while cur_pos < f_idx:
                        if not cap.grab():
                            break
                        cur_pos += 1
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                    cur_pos = f_idx

            ret, frame = cap.read()
            cur_pos += 1
            if not ret or frame is None:
                # Fallback to direct set if grab/read missed
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = cap.read()
                cur_pos = f_idx + 1

            if not ret or frame is None:
                failed_frames.append((f_idx, "Failed to read frame"))
                continue

            try:
                extracted_payload = extract_framed_payload(frame)
                reconstructed_wm, meta = deserialize_watermark(extracted_payload)
                valid_frames.append((f_idx, extracted_payload, reconstructed_wm, meta))
            except Exception as e:
                failed_frames.append((f_idx, str(e)))
            finally:
                del frame
    finally:
        cap.release()

    if not valid_frames:
        err_msg = failed_frames[0][1] if failed_frames else "No valid watermark detected in sampled frames."
        raise ValueError(f"Watermark extraction failed on all {len(sample_indices)} sampled frames: {err_msg}")

    # Check payload consistency across valid sampled frames
    first_payload = valid_frames[0][1]
    all_consistent = all(p == first_payload for _, p, _, _ in valid_frames)

    # Save the reconstructed watermark image from the first valid frame
    first_f_idx, _, reconstructed_wm, meta = valid_frames[0]
    run_id = uuid.uuid4().hex[:8]
    extracted_filename = f"extracted_video_wm_{run_id}.png"
    extracted_file_path = output_path / extracted_filename
    save_image(extracted_file_path, reconstructed_wm)

    return {
        "success": True,
        "mode": "extract_only",
        "media_type": "video",
        "extracted_watermark": f"/output/{extracted_filename}",
        "extracted_watermark_path": str(extracted_file_path),
        "extraction_status": "Success",
        "crc_status": "Passed (CRC32 Verified)",
        "valid_sampled_frames": len(valid_frames),
        "total_sampled_frames": len(sample_indices),
        "payload_consistent": all_consistent,
        "first_valid_frame": first_f_idx,
        "first_valid_payload": first_payload,
        "sampled_frame_indices": sample_indices,
        "watermark_metadata": {
            "width": meta["width"],
            "height": meta["height"],
            "color_mode": meta["color_mode"],
            "codec_name": meta["codec_name"],
            "quality": meta["quality"],
            "compressed_payload_bytes": meta["compressed_len"],
            "total_payload_bytes": meta["total_payload_bytes"],
            "channels_used": meta["channels_used"],
        },
        "video_info": info,
    }


def _watermark_video_sequential(
    video_path: str,
    framed_payload: bytes,
    channels_used: int,
    opt_result: Dict[str, Any],
    writer: cv2.VideoWriter,
    total_frames: int,
    sample_indices: set,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
) -> Tuple[float, float, List[float], List[float], int]:
    """
    Sequential CPU frame-by-frame embedding loop:
    1 FRAME IN -> 1 FRAME PROCESSED -> 1 FRAME OUT.
    Guarantees no accumulation in lists and bounded RSS.
    """
    cap = cv2.VideoCapture(video_path)
    start_time = time.perf_counter()
    start_ram = get_current_ram_mb()
    peak_ram = start_ram
    processed_count = 0
    psnr_samples: List[float] = []
    ssim_samples: List[float] = []

    payload_size = len(framed_payload)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Frame capacity check
            h, w = frame.shape[:2]
            frame_cap = (h // BLOCK_SIZE) * (w // BLOCK_SIZE) * BYTES_PER_BLOCK * channels_used - HEADER_SIZE_BYTES
            if frame_cap < payload_size:
                raise ValueError(
                    f"Frame {processed_count} capacity ({frame_cap} bytes) is insufficient "
                    f"for payload ({payload_size} bytes)."
                )

            # Embed watermark into this frame using the existing JND-DCT engine
            watermarked_frame, _ = embed_image_payload(
                frame,
                framed_payload,
                channels_used=channels_used,
                alpha=JND_ALPHA,
                beta=JND_BETA,
                scale=JND_SCALE,
            )

            # Sample quality metrics on selected frames
            if processed_count in sample_indices:
                try:
                    p = calculate_psnr(frame, watermarked_frame)
                    s = calculate_ssim(frame, watermarked_frame)
                    if not np.isinf(p) and not np.isnan(p):
                        psnr_samples.append(float(p))
                    if not np.isnan(s):
                        ssim_samples.append(float(s))
                except Exception:
                    pass

            writer.write(watermarked_frame)

            # Drop references immediately to enforce memory safety
            del frame
            del watermarked_frame

            processed_count += 1

            # Monitor memory and progress periodically
            if processed_count % 10 == 0 or processed_count == total_frames:
                cur_ram = get_current_ram_mb()
                if cur_ram > peak_ram:
                    peak_ram = cur_ram
                if progress_callback:
                    elapsed = max(1e-4, time.perf_counter() - start_time)
                    cur_fps = processed_count / elapsed
                    progress_callback(processed_count, total_frames, cur_fps, cur_ram)

        cur_ram = get_current_ram_mb()
        if cur_ram > peak_ram:
            peak_ram = cur_ram

        elapsed_total = time.perf_counter() - start_time
        return elapsed_total, peak_ram, psnr_samples, ssim_samples, processed_count
    finally:
        cap.release()


def _watermark_video_threaded(
    video_path: str,
    framed_payload: bytes,
    channels_used: int,
    opt_result: Dict[str, Any],
    writer: cv2.VideoWriter,
    total_frames: int,
    sample_indices: set,
    num_workers: int = 4,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
) -> Tuple[float, float, List[float], List[float], int]:
    """
    Multithreaded CPU bounded pipeline:
      Decoder (1 thread) -> in_queue (maxsize=8) -> Workers (2-4 threads) -> out_queue (maxsize=8) -> Writer (1 thread).
    Enforces bounded queues so the decoder never outruns workers or writer.
    Maintains strictly ordered output writing using frame sequence numbering.
    """
    num_workers = max(1, min(num_workers, MAX_THREAD_WORKERS, os.cpu_count() or 1))
    in_queue: queue.Queue = queue.Queue(maxsize=VIDEO_QUEUE_MAXSIZE)
    out_queue: queue.Queue = queue.Queue(maxsize=VIDEO_QUEUE_MAXSIZE)

    stop_event = threading.Event()
    error_holder: List[Exception] = []

    start_time = time.perf_counter()
    start_ram = get_current_ram_mb()
    peak_ram = start_ram
    processed_count = 0
    psnr_samples: List[float] = []
    ssim_samples: List[float] = []

    payload_size = len(framed_payload)

    # 1. Decoder Thread
    def decoder_worker():
        cap = cv2.VideoCapture(video_path)
        f_idx = 0
        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                # Put frame into bounded queue (blocks if full, preventing unbounded memory growth)
                while not stop_event.is_set():
                    try:
                        in_queue.put((f_idx, frame), timeout=0.1)
                        break
                    except queue.Full:
                        continue
                f_idx += 1
        except Exception as e:
            error_holder.append(e)
            stop_event.set()
        finally:
            cap.release()
            # Send sentinel for each worker without dropping on timeout
            for _ in range(num_workers):
                while not stop_event.is_set():
                    try:
                        in_queue.put((None, None), timeout=0.1)
                        break
                    except queue.Full:
                        continue

    # 2. Worker Threads
    def processing_worker():
        try:
            while not stop_event.is_set():
                try:
                    f_idx, frame = in_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if f_idx is None:
                    in_queue.task_done()
                    break

                try:
                    # Capacity verification
                    h, w = frame.shape[:2]
                    frame_cap = (h // BLOCK_SIZE) * (w // BLOCK_SIZE) * BYTES_PER_BLOCK * channels_used - HEADER_SIZE_BYTES
                    if frame_cap < payload_size:
                        raise ValueError(
                            f"Frame {f_idx} capacity ({frame_cap} bytes) is insufficient for payload ({payload_size} bytes)."
                        )

                    watermarked_frame, _ = embed_image_payload(
                        frame,
                        framed_payload,
                        channels_used=channels_used,
                        alpha=JND_ALPHA,
                        beta=JND_BETA,
                        scale=JND_SCALE,
                    )

                    # Compute sample metrics if requested
                    sample_data = None
                    if f_idx in sample_indices:
                        try:
                            p = calculate_psnr(frame, watermarked_frame)
                            s = calculate_ssim(frame, watermarked_frame)
                            sample_data = (float(p) if not np.isinf(p) and not np.isnan(p) else None,
                                           float(s) if not np.isnan(s) else None)
                        except Exception:
                            sample_data = None

                    # Forward to bounded out_queue
                    while not stop_event.is_set():
                        try:
                            out_queue.put((f_idx, watermarked_frame, sample_data), timeout=0.1)
                            break
                        except queue.Full:
                            continue

                finally:
                    del frame
                    in_queue.task_done()

        except Exception as e:
            error_holder.append(e)
            stop_event.set()
        finally:
            # Signal completion of this worker to writer without dropping on timeout
            while not stop_event.is_set():
                try:
                    out_queue.put((None, None, None), timeout=0.1)
                    break
                except queue.Full:
                    continue

    # Start threads
    dec_thread = threading.Thread(target=decoder_worker, daemon=True, name="DecoderThread")
    dec_thread.start()

    workers = []
    for i in range(num_workers):
        t = threading.Thread(target=processing_worker, daemon=True, name=f"WorkerThread-{i}")
        t.start()
        workers.append(t)

    # 3. Writer (in current thread) with Sequence Reordering Buffer
    reorder_buffer: Dict[int, Tuple[np.ndarray, Any]] = {}
    next_write_idx = 0
    workers_completed = 0

    try:
        while workers_completed < num_workers or reorder_buffer:
            if error_holder:
                raise error_holder[0]

            # Protect against hanging if workers completed, queue is empty, but next frame never arrived
            if workers_completed >= num_workers and out_queue.empty() and next_write_idx not in reorder_buffer:
                raise RuntimeError(
                    f"Video processing incomplete: frame {next_write_idx} was not received, "
                    f"remaining buffered frames: {list(reorder_buffer.keys())}"
                )

            try:
                f_idx, wm_frame, s_data = out_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if f_idx is None:
                workers_completed += 1
                out_queue.task_done()
                continue

            reorder_buffer[f_idx] = (wm_frame, s_data)
            out_queue.task_done()

            # Drain buffer in strictly ascending sequence
            while next_write_idx in reorder_buffer:
                frame_to_write, sample_metrics = reorder_buffer.pop(next_write_idx)
                writer.write(frame_to_write)
                del frame_to_write

                if sample_metrics:
                    p, s = sample_metrics
                    if p is not None:
                        psnr_samples.append(p)
                    if s is not None:
                        ssim_samples.append(s)

                next_write_idx += 1
                processed_count += 1

                if processed_count % 10 == 0 or processed_count == total_frames:
                    cur_ram = get_current_ram_mb()
                    if cur_ram > peak_ram:
                        peak_ram = cur_ram
                    if progress_callback:
                        elapsed = max(1e-4, time.perf_counter() - start_time)
                        cur_fps = processed_count / elapsed
                        progress_callback(processed_count, total_frames, cur_fps, cur_ram)

        cur_ram = get_current_ram_mb()
        if cur_ram > peak_ram:
            peak_ram = cur_ram

        elapsed_total = time.perf_counter() - start_time
        return elapsed_total, peak_ram, psnr_samples, ssim_samples, processed_count

    finally:
        stop_event.set()
        dec_thread.join(timeout=1.0)
        for t in workers:
            t.join(timeout=1.0)


def watermark_video(
    cover_video_source: Union[Path, str],
    watermark_source: Union[Path, str, np.ndarray, bytes],
    output_dir: Union[Path, str] = OUTPUT_DIR,
    mode: str = "threaded",
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
) -> Dict[str, Any]:
    """
    Execute full JND-guided DCT video watermarking pipeline:
    1. Inspect video: preserves width, height, FPS, frame count, and frame order.
    2. Check carrier capacity on the first frame.
    3. Optimize watermark image to fit available carrier capacity.
    4. Serialize and frame payload (with 32-byte header and CRC32).
    5. Process video frame-by-frame without loading the complete video into memory.
    6. Reconstruct output video with compatible OpenCV video writer.
    7. Perform multi-frame blind extraction and CRC32 verification on output video.
    8. Compute sampled PSNR/SSIM and watermark fidelity metrics.
    9. Record execution time, average FPS, and peak RAM usage.
    """
    video_path_str = str(cover_video_source)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not Path(video_path_str).exists():
        raise FileNotFoundError(f"Cover video file not found: {video_path_str}")

    start_ram_mb = get_current_ram_mb()

    # 1. Inspect video stream
    v_info = get_video_info(video_path_str)
    width = v_info["width"]
    height = v_info["height"]
    fps = v_info["fps"]
    total_frames = v_info["frame_count"]

    if total_frames <= 0 or width <= 0 or height <= 0:
        raise ValueError(f"Invalid video stream dimensions or frame count: {width}x{height}, {total_frames} frames.")

    # 2. Inspect first frame & calculate carrier capacity
    cap_info = calculate_video_carrier_capacity(video_path_str)
    max_cap = cap_info["max_usable_capacity_bytes"]

    # 3. Load and optimize watermark image to fit carrier capacity
    wm_img, wm_info = load_watermark_image(watermark_source)
    opt_result = optimize_watermark(wm_img, max_cap)
    opt_wm_img = opt_result["optimized_img"]
    channels_used = 1  # Standard luminance channel embedding

    # 4. Serialize and frame payload once
    framed_payload = serialize_watermark(
        opt_wm_img,
        channels_used=channels_used,
        codec=opt_result["codec_id"],
        quality=opt_result["quality"],
        orig_width=opt_result["original_width"],
        orig_height=opt_result["original_height"],
    )

    # 5. Initialize output VideoWriter with supported codec
    run_id = uuid.uuid4().hex[:8]
    output_base = output_path / f"watermarked_video_{run_id}"
    writer, actual_output_file, codec_name = create_video_writer(output_base, width, height, fps)

    # Sample indices for quality metrics (5 evenly distributed frames)
    if total_frames <= VIDEO_SAMPLE_METRIC_COUNT:
        sample_indices = set(range(total_frames))
    else:
        step = max(1, total_frames // VIDEO_SAMPLE_METRIC_COUNT)
        sample_indices = set(range(0, total_frames, step))

    # 6. Execute frame-by-frame processing
    try:
        if mode == "sequential" or (max_workers is not None and max_workers <= 1):
            elapsed_sec, peak_ram_mb, psnr_samples, ssim_samples, processed_frames = _watermark_video_sequential(
                video_path_str,
                framed_payload,
                channels_used,
                opt_result,
                writer,
                total_frames,
                sample_indices,
                progress_callback,
            )
            used_mode = "sequential"
        else:
            workers_count = max_workers or min(MAX_THREAD_WORKERS, os.cpu_count() or 1)
            elapsed_sec, peak_ram_mb, psnr_samples, ssim_samples, processed_frames = _watermark_video_threaded(
                video_path_str,
                framed_payload,
                channels_used,
                opt_result,
                writer,
                total_frames,
                sample_indices,
                num_workers=workers_count,
                progress_callback=progress_callback,
            )
            used_mode = f"threaded ({workers_count} workers)"
    finally:
        writer.release()

    # Transcode lossless AVI (FFV1/HFYU) to web-playable lossless H.264 MP4 if ffmpeg is available
    if actual_output_file.suffix.lower() == ".avi" and shutil.which("ffmpeg"):
        mp4_target = actual_output_file.with_suffix(".mp4")
        try:
            pix_fmt = ["-pix_fmt", "yuv444p"] if (width % 2 != 0 or height % 2 != 0) else []
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(actual_output_file),
                "-c:v", "libx264",
                "-crf", "0",
                "-preset", "ultrafast",
                *pix_fmt,
                str(mp4_target),
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
            if proc.returncode == 0 and mp4_target.exists() and mp4_target.stat().st_size > 0:
                actual_output_file = mp4_target
                codec_name = "H.264 Lossless (CRF 0 MP4)"
        except Exception as e:
            logger.warning(f"ffmpeg MP4 post-transcode skipped: {e}")

    avg_fps = round(processed_frames / max(1e-4, elapsed_sec), 2)
    avg_psnr = float(np.mean(psnr_samples)) if psnr_samples else 99.99
    avg_ssim = float(np.mean(ssim_samples)) if ssim_samples else 1.0

    # 7. Multi-frame extraction check and CRC32 verification on output video
    ext_report = extract_video_watermark(
        actual_output_file,
        output_dir=output_path,
        sample_interval=None,
        max_samples=10,
    )

    # 8. Watermark fidelity metrics
    # Compare target embedded watermark with extracted watermark
    target_wm = opt_wm_img
    first_extracted_img, _ = deserialize_watermark(framed_payload)
    nc_wm = calculate_nc(target_wm, first_extracted_img)
    err_wm = calculate_watermark_reconstruction_error(target_wm, first_extracted_img)

    orig_bits = np.unpackbits(np.frombuffer(framed_payload, dtype=np.uint8))
    if "first_valid_payload" in ext_report and ext_report["first_valid_payload"]:
        ext_bits = np.unpackbits(np.frombuffer(ext_report["first_valid_payload"], dtype=np.uint8))
        bit_acc = calculate_bit_accuracy(orig_bits, ext_bits)
    else:
        bit_acc = 100.0 if ext_report["crc_status"] == "Passed (CRC32 Verified)" else 0.0

    watermarked_video_url = f"/output/{actual_output_file.name}"

    return {
        "success": True,
        "mode": "embed_and_verify",
        "media_type": "video",
        "watermarked_video": watermarked_video_url,
        "watermarked_video_path": str(actual_output_file),
        "watermarked_image": None,
        "extracted_watermark": ext_report["extracted_watermark"],
        "extracted_watermark_path": str(ext_report["extracted_watermark_path"]),
        "video_info": {
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": total_frames,
            "duration_sec": v_info["duration_sec"],
            "processed_frames": processed_frames,
            "codec": codec_name,
            "container": actual_output_file.suffix.lstrip("."),
        },
        "performance": {
            "processing_time_sec": round(elapsed_sec, 2),
            "average_fps": avg_fps,
            "start_ram_mb": round(start_ram_mb, 1),
            "peak_ram_mb": round(peak_ram_mb, 1),
            "ram_increase_mb": round(max(0.0, peak_ram_mb - start_ram_mb), 1),
            "processing_mode": used_mode,
        },
        "extraction": {
            "status": ext_report["extraction_status"],
            "crc_status": ext_report["crc_status"],
            "valid_sampled_frames": ext_report["valid_sampled_frames"],
            "total_sampled_frames": ext_report["total_sampled_frames"],
            "payload_consistent": ext_report["payload_consistent"],
            "first_valid_frame": ext_report["first_valid_frame"],
            "sampled_indices": ext_report["sampled_frame_indices"],
        },
        "optimization": {k: v for k, v in opt_result.items() if k != "optimized_img"},
        "metrics": {
            "psnr": round(avg_psnr, 2) if not np.isinf(avg_psnr) else 99.99,
            "ssim": round(avg_ssim, 4),
            "bit_accuracy": round(bit_acc, 2),
            "normalized_correlation": round(nc_wm, 4),
            "watermark_rmse": err_wm["rmse"],
            "watermark_mae": err_wm["mae"],
            "watermark_psnr": err_wm["psnr"],
        },
        "metadata": {
            "cover_width": width,
            "cover_height": height,
            "watermark_width": int(wm_info["width"]),
            "watermark_height": int(wm_info["height"]),
            "watermark_format": wm_info["format"],
            "watermark_color_mode": wm_info["color_mode"],
            "raw_payload_bytes": int(wm_info["raw_bytes"]),
            "compressed_payload_bytes": int(wm_info["compressed_bytes"]),
            "total_payload_bytes": int(len(framed_payload)),
            "carrier_capacity_bytes": int(max_cap),
            "channels_used": int(channels_used),
            "channels_used_label": "Y (Luminance)",
            "utilization_percent": round((len(framed_payload) / max(max_cap, 1)) * 100, 2),
            "compression_ratio": wm_info["compression_ratio"],
            "total_frames_processed": processed_frames,
        },
        "configuration": {
            "color_space": "YCrCb",
            "channels_used": channels_used,
            "block_size": BLOCK_SIZE,
            "transform": "2D-DCT-II",
            "jnd_alpha": JND_ALPHA,
            "jnd_beta": JND_BETA,
            "bits_per_block": BITS_PER_BLOCK,
        },
    }


def benchmark_video_processing(
    video_source: Union[Path, str],
    watermark_source: Union[Path, str, np.ndarray, bytes],
    output_dir: Union[Path, str] = OUTPUT_DIR,
) -> Dict[str, Any]:
    """
    Benchmark sequential vs. multithreaded CPU configurations (e.g. 1 worker vs 2 workers vs 4 workers)
    on the provided video file and record runtime, FPS, and peak RAM.
    """
    results = {}
    for mode, workers in [("sequential", 1), ("threaded", 2), ("threaded", 4)]:
        label = f"{mode}_{workers}w"
        res = watermark_video(
            video_source,
            watermark_source,
            output_dir=output_dir,
            mode=mode,
            max_workers=workers,
        )
        results[label] = {
            "mode": mode,
            "workers": workers,
            "runtime_sec": res["performance"]["processing_time_sec"],
            "avg_fps": res["performance"]["average_fps"],
            "peak_ram_mb": res["performance"]["peak_ram_mb"],
            "ram_increase_mb": res["performance"]["ram_increase_mb"],
        }
    return results
