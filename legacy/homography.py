import cv2
import numpy as np

# Load the image
image_path = "calibration_image.jpg"
image = cv2.imread(image_path)
if image is None:
    raise FileNotFoundError(f"Could not load image at {image_path}")

# Define calibration points in the camera frame (manually identified or predefined)
camera_points = np.array([
    [100, 100],  # Top-left corner in the camera view
    [500, 100],  # Top-right corner in the camera view
    [500, 400],  # Bottom-right corner in the camera view
    [100, 400]   # Bottom-left corner in the camera view
], dtype="float32")

# Define corresponding points in the game coordinate system (e.g., a 1920x1080 game screen)
game_points = np.array([
    [0, 0],       # Top-left in the game
    [1920, 0],    # Top-right in the game
    [1920, 1080], # Bottom-right in the game
    [0, 1080]     # Bottom-left in the game
], dtype="float32")

# Compute the homography matrix
homography_matrix, status = cv2.findHomography(camera_points, game_points)
print("Homography matrix:")
print(homography_matrix)

# Draw calibration points on the image for visualization
for point in camera_points:
    cv2.circle(image, tuple(point.astype(int)), 10, (0, 255, 0), -1)

# Display the calibration image
cv2.imshow("Calibration Image", image)
cv2.waitKey(0)

# Example: Simulate a detected laser blob position in the camera's coordinate system
laser_blob_camera_coords = np.array([[250, 250]], dtype="float32")  # Example laser blob position
laser_blob_camera_coords = laser_blob_camera_coords.reshape(-1, 1, 2)

# Transform the laser blob position to the game coordinate system
laser_blob_game_coords = cv2.perspectiveTransform(laser_blob_camera_coords, homography_matrix)

# Extract the transformed game coordinates
game_x, game_y = laser_blob_game_coords[0][0]
print(f"Laser blob game coordinates: ({game_x:.2f}, {game_y:.2f})")

# Draw the detected point on the camera image
cv2.circle(image, (250, 250), 10, (0, 0, 255), -1)  # Simulate laser blob detection
cv2.imshow("Laser Blob Detection", image)
cv2.waitKey(0)

# Clean up
cv2.destroyAllWindows()
