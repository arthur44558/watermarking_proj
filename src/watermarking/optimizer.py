import cv2
import numpy as np
import zlib
import copy
import logging

from .config import (
    CODEC_RAW_ZLIB,
    CODEC_WEBP,
    CODEC_JPEG,
    MIN_WATERMARK_QUALITY,
    MIN_WATERMARK_DIM,
    MAX_PAYLOAD_BYTES,
)
from .payload import serialize_watermark, deserialize_watermark

logger = logging.getLogger(__name__)

def is_near_monochrome(img, tolerance=5):
    """
    Checks if an RGB/BGR image is nearly monochrome (grayscale).
    Returns True if max difference between any two channels <= tolerance.
    """
    if len(img.shape) < 3 or img.shape[2] == 1:
        return True # already grayscale
        
    b, g, r = cv2.split(img)
    diff_bg = cv2.absdiff(b, g)
    diff_gr = cv2.absdiff(g, r)
    diff_rb = cv2.absdiff(r, b)
    
    max_diff = max(np.max(diff_bg), np.max(diff_gr), np.max(diff_rb))
    return bool(max_diff <= tolerance)

def optimize_watermark(wm_img, available_capacity_bytes, min_quality=MIN_WATERMARK_QUALITY, max_quality=95, min_dim=MIN_WATERMARK_DIM):
    """
    Optimizes a watermark image to fit within available capacity.
    
    Stages:
    0. Lossless check (RAW_ZLIB)
    1. Color complexity check (convert to grayscale if near monochrome)
    2. Binary search on WebP quality [min_quality, max_quality] at full scale
    3. Progressive downscaling (0.9, 0.8... down to min_dim) + binary search
    4. Raise ValueError if cannot fit at minimum scale and quality
    
    Returns:
    dict containing optimization metadata and the optimized image representation.
    """
    orig_height, orig_width = wm_img.shape[:2]
    orig_size_bytes = wm_img.nbytes
    
    current_img = copy.deepcopy(wm_img)
    
    # Stage 1: Color Complexity Check
    if is_near_monochrome(current_img, tolerance=5):
        if len(current_img.shape) == 3 and current_img.shape[2] == 3:
            current_img = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            
    # Stage 0: Lossless RAW_ZLIB check
    try:
        payload = serialize_watermark(
            current_img,
            codec=CODEC_RAW_ZLIB,
            quality=100,
            orig_width=orig_width,
            orig_height=orig_height,
            enforce_limit=False,
        )
        if len(payload) <= available_capacity_bytes:
            return _build_result(
                current_img, CODEC_RAW_ZLIB, 100, 1.0, orig_width, orig_height, 
                orig_size_bytes, len(payload), False, "No compression needed"
            )
    except Exception:
        pass
        
    # We will use WEBP for compression
    codec = CODEC_WEBP
    
    # Stage 2: Binary Search over WebP quality at full resolution
    q_star = _binary_search_quality(current_img, available_capacity_bytes, codec, min_quality, max_quality, orig_width, orig_height)
    if q_star is not None:
        best_payload = serialize_watermark(
            current_img,
            codec=codec,
            quality=q_star,
            orig_width=orig_width,
            orig_height=orig_height,
            enforce_limit=False,
        )
        opt_decoded, _ = deserialize_watermark(best_payload)
        return _build_result(
            opt_decoded, codec, q_star, 1.0, orig_width, orig_height,
            orig_size_bytes, len(best_payload), True, "Automatically optimized to fit"
        )
        
    # Stage 3: Progressive aspect-ratio-preserving downscaling
    # Compute the absolute minimum scale such that neither dimension drops below 4 pixels
    abs_min_scale = max(4.0 / max(1, orig_width), 4.0 / max(1, orig_height))
    abs_min_scale = min(1.0, abs_min_scale)

    # Compute target scale for the configured nominal min_dim
    nominal_min = max(4, min(min_dim, min(orig_width, orig_height)))
    nominal_min_scale = max(nominal_min / max(1, orig_width), nominal_min / max(1, orig_height))
    nominal_min_scale = min(1.0, nominal_min_scale)

    candidate_scales = [
        0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5,
        0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01
    ]
    scale_set = {s for s in candidate_scales if s >= abs_min_scale}
    if nominal_min_scale >= abs_min_scale and nominal_min_scale < 1.0:
        scale_set.add(round(nominal_min_scale, 4))
    if abs_min_scale < 1.0:
        scale_set.add(round(abs_min_scale, 4))
    scale_factors = sorted(list(scale_set), reverse=True)

    for scale in scale_factors:
        new_width = max(1, int(round(orig_width * scale)))
        new_height = max(1, int(round(orig_height * scale)))

        if new_width < 4 or new_height < 4:
            continue

        scaled_img = cv2.resize(current_img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        q_star = _binary_search_quality(scaled_img, available_capacity_bytes, codec, min_quality, max_quality, orig_width, orig_height)
        if q_star is not None:
            best_payload = serialize_watermark(
                scaled_img,
                codec=codec,
                quality=q_star,
                orig_width=orig_width,
                orig_height=orig_height,
                enforce_limit=False,
            )
            opt_decoded, _ = deserialize_watermark(best_payload)
            return _build_result(
                opt_decoded, codec, q_star, scale, orig_width, orig_height,
                orig_size_bytes, len(best_payload), True, "Automatically optimized to fit"
            )

    # Stage 4: Still too large
    # Test with minimum possible settings to get the deficit
    new_width = max(4, int(round(orig_width * abs_min_scale)))
    new_height = max(4, int(round(orig_height * abs_min_scale)))
    min_img = cv2.resize(current_img, (new_width, new_height), interpolation=cv2.INTER_AREA) if abs_min_scale < 1.0 else current_img
    try:
        min_payload = serialize_watermark(
            min_img,
            codec=codec,
            quality=min_quality,
            orig_width=orig_width,
            orig_height=orig_height,
            enforce_limit=False,
        )
        min_bytes = len(min_payload)
    except Exception:
        min_bytes = MAX_PAYLOAD_BYTES

    deficit = min_bytes - available_capacity_bytes
    raise ValueError(f"Watermark payload exceeds carrier capacity even at minimum quality and scale. Required: {min_bytes} bytes, Available: {available_capacity_bytes} bytes. Deficit: {deficit} bytes.")

def _binary_search_quality(img, capacity, codec, min_q, max_q, orig_width, orig_height):
    """
    Performs binary search to find the maximum quality Q in [min_q, max_q]
    where serialize_watermark payload size <= capacity.
    Returns the best Q, or None if even min_q exceeds capacity.
    """
    best_q = None
    low = min_q
    high = max_q
    
    while low <= high:
        mid = (low + high) // 2
        try:
            payload = serialize_watermark(
                img,
                codec=codec,
                quality=mid,
                orig_width=orig_width,
                orig_height=orig_height,
                enforce_limit=False,
            )
            payload_len = len(payload)
        except Exception:
            payload_len = float('inf')

        if payload_len <= capacity:
            best_q = mid
            low = mid + 1
        else:
            high = mid - 1
            
    return best_q
    
def _build_result(opt_img, codec, quality, scale, orig_w, orig_h, orig_bytes, opt_bytes, applied, status):
    scale_percent = int(scale * 100)
    
    codec_name = "RAW_ZLIB"
    if codec == CODEC_WEBP:
        codec_name = "WebP"
    elif codec == CODEC_JPEG:
        codec_name = "JPEG"
        
    color_desc = "RGB" if len(opt_img.shape) == 3 and opt_img.shape[2] == 3 else "Grayscale"
    
    opt_w = opt_img.shape[1]
    opt_h = opt_img.shape[0]
    
    summary = f"Original: {orig_w}x{orig_h} ({orig_bytes/1024:.1f} KB) -> Embedding: {opt_w}x{opt_h} {color_desc}, {codec_name} Q{quality} ({opt_bytes/1024:.1f} KB)"
    
    return {
        "optimized_img": opt_img,
        "codec": codec_name,
        "codec_id": codec,
        "quality": quality,
        "scale_percent": scale_percent,
        "original_width": orig_w,
        "original_height": orig_h,
        "optimized_width": opt_w,
        "optimized_height": opt_h,
        "original_size_bytes": orig_bytes,
        "optimized_size_bytes": opt_bytes,
        "status": status,
        "applied": applied,
        "summary_text": summary
    }
