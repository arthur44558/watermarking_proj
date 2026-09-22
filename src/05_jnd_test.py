import cv2
import numpy as np

def calculate_jnd(block, alpha=2.0, beta=0.1):
    std = np.std(block)
    jnd = alpha + beta * std
    return jnd


image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)

y, cr, cb = cv2.split(ycrcb)

block = y[0:8, 0:8].astype(np.float32)

std = np.std(block)
variance = np.var(block)
jnd = calculate_jnd(block)

print("Mean:", np.mean(block))
print("Standard deviation:", std)
print("Variance:", variance)
print("JND:", jnd)