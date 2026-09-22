import cv2

image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

# Convert BGR → YCrCb
ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)

# Separate the three channels
y, cr, cb = cv2.split(ycrcb)

print("Y shape:", y.shape)
print("Y data type:", y.dtype)

# Save the luminance channel
cv2.imwrite("output/luminance.png", y)