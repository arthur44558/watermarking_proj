"""
API routes for watermarking operations.
Handles arbitrary-image and arbitrary-video watermarking, capacity calculation, and configuration queries.
"""

from pathlib import Path
import uuid
import os
from flask import Blueprint, request, jsonify

from watermarking.pipeline import (
    watermark_image,
    extract_only,
    calculate_carrier_capacity,
)
from watermarking.video import (
    watermark_video,
    extract_video_watermark,
    calculate_video_carrier_capacity,
)
from watermarking.image_utils import load_image
from watermarking.config import (
    BLOCK_SIZE,
    BITS_PER_BLOCK,
    BYTES_PER_BLOCK,
    HEADER_SIZE_BYTES,
    MAX_WATERMARK_WIDTH,
    MAX_WATERMARK_HEIGHT,
    JND_ALPHA,
    JND_BETA,
    UPLOADS_DIR,
    OUTPUT_DIR,
    SUPPORTED_VIDEO_FORMATS,
    DEFAULT_VIDEO_FPS,
    MAX_THREAD_WORKERS,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Ensure runtime directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_video_file(filename: str, content_type: str = "") -> bool:
    """Check if the provided file is a video by extension or MIME type."""
    ext = Path(filename).suffix.lower()
    if ext in SUPPORTED_VIDEO_FORMATS:
        return True
    if content_type and content_type.startswith("video/"):
        return True
    return False


@api_bp.route("/watermark", methods=["POST"])
def run_watermarking():
    """
    Handle multipart/form-data upload with:
    - cover_image: Image or Video file (Required)
    - watermark_image: Image file (Optional for extraction-only mode)
    - mode: Optional "sequential" or "threaded" for video (Default: "threaded")
    """
    file_key = "cover_image" if "cover_image" in request.files else ("cover_video" if "cover_video" in request.files else None)
    if not file_key:
        return jsonify({"success": False, "error": "Cover media (image or video) is required."}), 400

    cover_file = request.files[file_key]
    if not cover_file.filename or cover_file.filename == "":
        return jsonify({"success": False, "error": "Cover filename cannot be empty."}), 400

    filename = cover_file.filename
    content_type = cover_file.content_type or ""
    is_video = is_video_file(filename, content_type)

    # Check for watermark file
    has_watermark = False
    wm_bytes = None
    if "watermark_image" in request.files:
        wm_file = request.files["watermark_image"]
        if wm_file and wm_file.filename and wm_file.filename != "":
            wm_bytes = wm_file.read()
            if len(wm_bytes) > 0:
                has_watermark = True

    try:
        if is_video:
            # === Video Watermarking Branch ===
            run_id = uuid.uuid4().hex[:8]
            ext = Path(filename).suffix.lower()
            safe_ext = ext if ext in SUPPORTED_VIDEO_FORMATS else ".mp4"
            temp_video_path = UPLOADS_DIR / f"upload_{run_id}{safe_ext}"
            cover_file.save(str(temp_video_path))

            video_mode = request.form.get("mode", "threaded")

            try:
                if has_watermark:
                    # Mode A: Embed and Verify
                    result = watermark_video(
                        temp_video_path,
                        wm_bytes,
                        output_dir=OUTPUT_DIR,
                        mode=video_mode,
                    )
                else:
                    # Mode B: Extract Existing Watermark from Video
                    ext_result = extract_video_watermark(
                        temp_video_path,
                        output_dir=OUTPUT_DIR,
                    )
                    # Copy input video to output so it can be referenced in UI
                    input_copy_path = OUTPUT_DIR / f"input_video_{run_id}{safe_ext}"
                    try:
                        import shutil
                        shutil.copy2(str(temp_video_path), str(input_copy_path))
                        video_url = f"/output/{input_copy_path.name}"
                    except Exception:
                        video_url = None

                    result = {
                        "success": True,
                        "mode": "extract_only",
                        "media_type": "video",
                        "watermarked_video": video_url,
                        "watermarked_image": None,
                        "extracted_watermark": ext_result["extracted_watermark"],
                        "extraction": {
                            "status": ext_result["extraction_status"],
                            "crc_status": ext_result["crc_status"],
                            "valid_sampled_frames": ext_result["valid_sampled_frames"],
                            "total_sampled_frames": ext_result["total_sampled_frames"],
                            "payload_consistent": ext_result["payload_consistent"],
                            "first_valid_frame": ext_result["first_valid_frame"],
                        },
                        "video_info": ext_result["video_info"],
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
                            "cover_width": ext_result["video_info"]["width"],
                            "cover_height": ext_result["video_info"]["height"],
                            "watermark_width": ext_result["watermark_metadata"]["width"],
                            "watermark_height": ext_result["watermark_metadata"]["height"],
                            "watermark_color_mode": ext_result["watermark_metadata"]["color_mode"],
                            "compressed_payload_bytes": ext_result["watermark_metadata"]["compressed_payload_bytes"],
                            "total_payload_bytes": ext_result["watermark_metadata"]["total_payload_bytes"],
                            "channels_used": ext_result["watermark_metadata"]["channels_used"],
                            "channels_used_label": "Y (Luminance)",
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
                return jsonify(result), 200

            finally:
                # Always clean up uploaded temporary video from uploads/ directory
                if temp_video_path.exists():
                    try:
                        temp_video_path.unlink()
                    except Exception:
                        pass

        else:
            # === Image Watermarking Branch (Preserves existing behavior) ===
            cover_bytes = cover_file.read()
            if len(cover_bytes) == 0:
                return jsonify({"success": False, "error": "Cover image file is empty."}), 400

            if has_watermark:
                # Mode A: Embed and Verify
                result = watermark_image(cover_bytes, wm_bytes)
                result["media_type"] = "image"
            else:
                # Mode B: Extract Existing Watermark
                result = extract_only(cover_bytes)
                result["media_type"] = "image"

            return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal processing error: {str(e)}"}), 500


@api_bp.route("/capacity", methods=["POST"])
def check_capacity():
    """
    Calculate the exact payload capacity for an uploaded cover image or video.
    """
    file_key = "cover_image" if "cover_image" in request.files else ("cover_video" if "cover_video" in request.files else None)
    if not file_key:
        return jsonify({"success": False, "error": "Cover media is required."}), 400

    cover_file = request.files[file_key]
    filename = cover_file.filename or ""
    content_type = cover_file.content_type or ""
    is_video = is_video_file(filename, content_type)

    try:
        if is_video:
            run_id = uuid.uuid4().hex[:8]
            ext = Path(filename).suffix.lower()
            safe_ext = ext if ext in SUPPORTED_VIDEO_FORMATS else ".mp4"
            temp_path = UPLOADS_DIR / f"cap_temp_{run_id}{safe_ext}"
            try:
                cover_file.save(str(temp_path))
                cap = calculate_video_carrier_capacity(temp_path)
                return jsonify({"success": True, "capacity": cap}), 200
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
        else:
            cover_bytes = cover_file.read()
            cover_img = load_image(cover_bytes)
            cap = calculate_carrier_capacity(cover_img)
            cap["is_video"] = False
            return jsonify({"success": True, "capacity": cap}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@api_bp.route("/config", methods=["GET"])
def get_config():
    """
    Return technical configuration parameters to keep frontend display in sync.
    """
    return jsonify({
        "success": True,
        "configuration": {
            "color_space": "YCrCb",
            "block_size": BLOCK_SIZE,
            "transform": "2D-DCT-II",
            "jnd_alpha": JND_ALPHA,
            "jnd_beta": JND_BETA,
            "bits_per_block": BITS_PER_BLOCK,
            "bytes_per_block": BYTES_PER_BLOCK,
            "header_size_bytes": HEADER_SIZE_BYTES,
            "max_payload_bytes": None,
            "max_watermark_width": MAX_WATERMARK_WIDTH,
            "max_watermark_height": MAX_WATERMARK_HEIGHT,
            "supported_video_formats": list(SUPPORTED_VIDEO_FORMATS),
            "default_video_fps": DEFAULT_VIDEO_FPS,
            "max_thread_workers": MAX_THREAD_WORKERS,
        }
    }), 200
