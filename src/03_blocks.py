import cv2
import numpy as np

image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

# Convert BGR → YCrCb
ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)

# Extract luminance
y, cr, cb = cv2.split(ycrcb)

# Take the first 8×8 block
block = y[0:8, 0:8]

print("8×8 block:")
print(block)

print("\nShape:", block.shape)
print("Data type:", block.dtype)

print("\nMean:", np.mean(block))
print("Standard deviation:", np.std(block))
print("Variance:", np.var(block))