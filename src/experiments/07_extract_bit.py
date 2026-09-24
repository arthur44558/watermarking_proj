"""
07_extract_bit.py - Step 7 verification: extract embedded bit from an 8x8 block.
"""

import cv2
import numpy as np

COEFF_A = (3, 2)
COEFF_B = (2, 3)


def extract_bit(block):
    block = block.astype(np.float32)
    dct = cv2.dct(block)
    a = dct[COEFF_A]
    b = dct[COEFF_B]
    return 1 if a > b else 0


if __name__ == "__main__":
    from watermarking.pipeline import watermark_image
    result = watermark_image("input/test_image.jpeg", "input/watermark.png")
    print("Pipeline executed successfully!")
    print("Bit Accuracy:", result["metrics"]["bit_accuracy"])
    print("PSNR:", result["metrics"]["psnr"], "dB")
