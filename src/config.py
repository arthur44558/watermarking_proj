"""
Configuration parameters for JND-guided frequency-domain image watermarking.
"""

from pathlib import Path

# Block & Frequency Configuration
BLOCK_SIZE = 8

# Mid-frequency DCT coefficient pair for embedding
COEFF_A = (3, 2)
COEFF_B = (2, 3)

# Activity-based JND approximation parameters: JND = alpha + beta * sigma
JND_ALPHA = 2.0
JND_BETA = 0.1

# Embedding strength / safety margin factor (T = JND_SCALE * JND)
# Note: k=1.0 is the theoretical threshold. Under 8-bit integer quantization
# (float32 to uint8 spatial rounding), k >= 1.5 ensures 100% watermark recovery (NC=1.0).
JND_SCALE = 1.5

# Watermark specifications
WATERMARK_SIZE = (32, 32)  # 32x32 = 1024 bits

# Default File Paths
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_IMAGE_PATH = INPUT_DIR / "test_image.jpeg"
WATERMARK_PATH = INPUT_DIR / "watermark.png"

WATERMARKED_IMAGE_PATH = OUTPUT_DIR / "watermarked.png"
EXTRACTED_WATERMARK_PATH = OUTPUT_DIR / "extracted_watermark.png"
DIFFERENCE_IMAGE_PATH = OUTPUT_DIR / "difference.png"
COMPARISON_IMAGE_PATH = OUTPUT_DIR / "comparison.png"

# Visualization parameters
DIFF_AMPLIFICATION = 25.0
