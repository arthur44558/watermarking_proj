import cv2
import numpy as np


COEFF_A = (3, 2)
COEFF_B = (2, 3)


def calculate_jnd(block, alpha=2.0, beta=0.1):
    std = np.std(block)
    return alpha + beta * std


def embed_bit(block, bit):
    # Convert block to floating point
    block = block.astype(np.float32)

    # Transform into frequency domain
    dct = cv2.dct(block)

    # Calculate JND
    jnd = calculate_jnd(block)

    # Get the two selected coefficients
    a = dct[COEFF_A]
    b = dct[COEFF_B]

    print("Before embedding:")
    print("A =", a)
    print("B =", b)
    print("A - B =", a - b)
    print("JND =", jnd)

    # Embed bit
    if bit == 1:

        if a - b < jnd:
            adjustment = (jnd - (a - b)) / 2

            dct[COEFF_A] += adjustment
            dct[COEFF_B] -= adjustment

    else:

        if b - a < jnd:
            adjustment = (jnd - (b - a)) / 2

            dct[COEFF_B] += adjustment
            dct[COEFF_A] -= adjustment

    # Values after embedding
    a_after = dct[COEFF_A]
    b_after = dct[COEFF_B]

    print("\nAfter embedding:")
    print("A =", a_after)
    print("B =", b_after)
    print("A - B =", a_after - b_after)

    # Convert back to spatial domain
    watermarked_block = cv2.idct(dct)

    return watermarked_block


# --------------------------------------------------
# Main experiment
# --------------------------------------------------

image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)

y, cr, cb = cv2.split(ycrcb)

# Take our same 8×8 block
block = y[0:8, 0:8]

# Embed bit 1
watermarked_block = embed_bit(block, 1)

print("\nOriginal block:")
print(block)

print("\nWatermarked block:")
print(np.round(watermarked_block, 2))

print("\nDifference:")
print(np.round(watermarked_block - block, 2))