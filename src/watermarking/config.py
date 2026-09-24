"""
Configuration settings and algorithm constants for JND-guided DCT watermarking.
Supports arbitrary-image watermarking with multi-bit-per-block payload embedding.
"""

from pathlib import Path

# Spatial block dimensions
BLOCK_SIZE = 8

# Activity-based JND approximation parameters:
# JND_B = (alpha + beta * sigma_B) * scale
JND_ALPHA = 2.0
JND_BETA = 0.1
JND_SCALE = 1.5

# Multi-bit payload embedding configuration:
# 16 disjoint symmetric mid/high-frequency coefficient pairs per 8x8 block (16 bits = 2 bytes per block)
# All pairs are strictly off-diagonal, non-DC, and symmetric: C(u, v) <-> C(v, u)
COEFF_PAIRS_16 = [
    ((3, 2), (2, 3)),
    ((1, 4), (4, 1)),
    ((2, 4), (4, 2)),
    ((3, 4), (4, 3)),
    ((1, 5), (5, 1)),
    ((2, 5), (5, 2)),
    ((3, 5), (5, 3)),
    ((4, 5), (5, 4)),
    ((1, 6), (6, 1)),
    ((2, 6), (6, 2)),
    ((3, 6), (6, 3)),
    ((1, 3), (3, 1)),
    ((4, 6), (6, 4)),
    ((5, 6), (6, 5)),
    ((2, 7), (7, 2)),
    ((3, 7), (7, 3)),
]

BITS_PER_BLOCK = len(COEFF_PAIRS_16)  # 16 bits
BYTES_PER_BLOCK = BITS_PER_BLOCK // 8  # 2 bytes

# Legacy single-pair reference for backward compatibility
COEFF_A = COEFF_PAIRS_16[0][0]
COEFF_B = COEFF_PAIRS_16[0][1]

# Header / Framing specifications
HEADER_MAGIC = b"JNDW"
HEADER_VERSION = 2
HEADER_SIZE_BYTES = 32  # 256 bits
HEADER_BLOCKS = HEADER_SIZE_BYTES // BYTES_PER_BLOCK  # 16 blocks

# Codec identifiers for payload encoding
CODEC_RAW_ZLIB = 0   # Raw pixel bytes + zlib level-9 (lossless)
CODEC_WEBP = 1        # WebP lossy encoding
CODEC_JPEG = 2        # JPEG lossy encoding

# Watermark payload constraints
MAX_PAYLOAD_BYTES = 1048576  # 1 MiB (1,048,576 bytes)
MAX_WATERMARK_WIDTH = 1920
MAX_WATERMARK_HEIGHT = 1200
SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Video processing configuration
DEFAULT_VIDEO_FPS = 30.0
VIDEO_SAMPLE_METRIC_COUNT = 5
VIDEO_QUEUE_MAXSIZE = 8
MAX_THREAD_WORKERS = 4

# Watermark optimization thresholds
MIN_WATERMARK_QUALITY = 25   # Minimum lossy encoding quality (WebP Q scale)
MIN_WATERMARK_DIM = 32       # Minimum width or height after downscaling

# Project path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
