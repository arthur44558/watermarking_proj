"""
Watermarking core package.
Exports image and video watermarking pipelines, capacity calculators, and configuration.
"""

from .config import (
    BLOCK_SIZE,
    BITS_PER_BLOCK,
    BYTES_PER_BLOCK,
    HEADER_SIZE_BYTES,
    JND_ALPHA,
    JND_BETA,
    JND_SCALE,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_VIDEO_FORMATS,
)
from .pipeline import (
    watermark_image,
    extract_only,
    calculate_carrier_capacity,
)
from .video import (
    watermark_video,
    extract_video_watermark,
    calculate_video_carrier_capacity,
    get_video_info,
    benchmark_video_processing,
)

__all__ = [
    "BLOCK_SIZE",
    "BITS_PER_BLOCK",
    "BYTES_PER_BLOCK",
    "HEADER_SIZE_BYTES",
    "JND_ALPHA",
    "JND_BETA",
    "JND_SCALE",
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_VIDEO_FORMATS",
    "watermark_image",
    "extract_only",
    "calculate_carrier_capacity",
    "watermark_video",
    "extract_video_watermark",
    "calculate_video_carrier_capacity",
    "get_video_info",
    "benchmark_video_processing",
]
