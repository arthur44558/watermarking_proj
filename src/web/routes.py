"""
API routes for watermarking operations.
Handles arbitrary-image watermarking, capacity calculation, and configuration queries.
"""

from flask import Blueprint, request, jsonify
from watermarking.pipeline import watermark_image, extract_only, calculate_carrier_capacity
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
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/watermark", methods=["POST"])
def run_watermarking():
    """
    Handle multipart/form-data upload with:
    - cover_image: Image file (Required)
    - watermark_image: Image file (Optional for extraction-only mode)
    """
    if "cover_image" not in request.files:
        return jsonify({"success": False, "error": "Cover image is required."}), 400

    cover_file = request.files["cover_image"]
    if not cover_file.filename or cover_file.filename == "":
        return jsonify({"success": False, "error": "Cover image filename cannot be empty."}), 400

    try:
        cover_bytes = cover_file.read()
        if len(cover_bytes) == 0:
            return jsonify({"success": False, "error": "Cover image file is empty."}), 400

        # Check if watermark image is supplied
        has_watermark = False
        wm_bytes = None
        if "watermark_image" in request.files:
            wm_file = request.files["watermark_image"]
            if wm_file and wm_file.filename and wm_file.filename != "":
                wm_bytes = wm_file.read()
                if len(wm_bytes) > 0:
                    has_watermark = True

        if has_watermark:
            # Mode A: Embed and Verify
            result = watermark_image(cover_bytes, wm_bytes)
        else:
            # Mode B: Extract Existing Watermark
            result = extract_only(cover_bytes)

        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Internal processing error: {str(e)}"}), 500


@api_bp.route("/capacity", methods=["POST"])
def check_capacity():
    """
    Calculate the exact payload capacity for an uploaded cover image.
    """
    if "cover_image" not in request.files:
        return jsonify({"success": False, "error": "Cover image is required."}), 400

    cover_file = request.files["cover_image"]
    try:
        cover_bytes = cover_file.read()
        cover_img = load_image(cover_bytes)
        cap = calculate_carrier_capacity(cover_img)
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
        }
    }), 200
