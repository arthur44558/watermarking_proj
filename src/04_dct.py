import cv2
import numpy as np

image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

# Convert BGR → YCrCb
ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)

# Extract luminance
y, cr, cb = cv2.split(ycrcb)

# Take the same 8×8 block
block = y[0:8, 0:8].astype(np.float32)

# Apply 2-D DCT
dct = cv2.dct(block)

np.set_printoptions(precision=2, suppress=True)

print("Original 8×8 block:")
print(block)

print("\nDCT coefficients:")
print(dct)