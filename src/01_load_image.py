import cv2

image = cv2.imread("input/test_image.jpeg")

if image is None:
    raise FileNotFoundError("Could not load image.")

print("Image loaded successfully.")
print("Shape:", image.shape)
print("Data type:", image.dtype)