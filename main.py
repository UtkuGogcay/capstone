import cv2
import numpy as np
import matplotlib.pyplot as plt

image_path = r'D:\\test\\img.jpg'

# Load the image
image = cv2.imread(image_path)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Apply Gaussian blur to reduce noise
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Apply Canny Edge Detection - min/max values for Hysteresis can be changed for sensitivity
edges = cv2.Canny(blurred, 50, 150)

# Find contours
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

screen_contour = None
max_area = 0

# Loop through the contours to find the largest rectangle
for contour in contours:
    epsilon = 0.02 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)

    if len(approx) == 4:  # Rectangle has 4 corners
        area = cv2.contourArea(approx)
        if area > max_area:
            max_area = area
            screen_contour = approx

# Perspective transformation
if screen_contour is not None:
    # Get corner coordinates of the detected rectangle
    corner_coords = screen_contour.reshape(4, 2)
    test1=[688,69,1848,410,1816,1152,700,1488]
    test2=np.array(test1).reshape(4,2)
    print(test2)
    # Order points: top-left, top-right, bottom-right, bottom-left
    corner_coords = sorted(corner_coords, key=lambda x: (x[1], x[0]))  # Sort by y first, then x
    top_left, top_right = sorted(corner_coords[:2], key=lambda x: x[0])
    bottom_left, bottom_right = sorted(corner_coords[2:], key=lambda x: x[0])
    top_left, top_right, bottom_left, bottom_right = [[688,69],[1848,410],[1816,1152],[700,1488]]
    ordered_coords = np.array([top_left, top_right, bottom_right, bottom_left], dtype='float32')
    ordered_coords=np.array(test2, dtype='float32')
    # Define target points for given resolution
    WIDTH=1920
    HEIGHT=1080
    target_coords = np.array([
        [0, 0],  # Top-left
        [WIDTH, 0],  # Top-right
        [WIDTH, HEIGHT],  # Bottom-right
        [0, HEIGHT]  # Bottom-left
    ], dtype='float32')

    # Compute the perspective transformation matrix
    matrix = cv2.getPerspectiveTransform(ordered_coords, target_coords)

    # Perform the perspective warp
    warped_image = cv2.warpPerspective(image, matrix, (WIDTH, HEIGHT))

    # Display the result
    plt.figure(figsize=(12, 6))
    plt.imshow(cv2.cvtColor(warped_image, cv2.COLOR_BGR2RGB))
    cv2.imwrite(r'D:\\test\\2\\img.jpg',warped_image)
    plt.title(f'Stretched to {WIDTH}x{HEIGHT} pixels')
    plt.axis('off')
    plt.show()

    # Output corner coordinates
    print("Original Corner Coordinates (in image):")
    for i, (x, y) in enumerate(ordered_coords):
        print(f"Corner {i + 1}: ({x}, {y})")
else:
    print("No rectangular screen detected.")
# Display  edges
plt.figure(figsize=(12, 6))
plt.imshow(edges, cmap='gray')
plt.title('Detected Edges')
plt.axis('off')
plt.show()

# Draw contours on the original image
image_with_contours = image.copy()
cv2.drawContours(image_with_contours, [screen_contour], -1, (0, 255, 0), 3)

plt.figure(figsize=(12, 6))
plt.imshow(cv2.cvtColor(image_with_contours, cv2.COLOR_BGR2RGB))
plt.title('Largest Rectangle')
plt.axis('off')
plt.show()
