import cv2
import numpy as np


def map_point_to_projector(point, corners, projector_resolution):
    """
    point: (x, y) coordinates of the point to be mapped
    corners: List of 4 corners in the photo
    projector_resolution : (width, height) of the projector.
    """
    # Unpack inputs
    x, y = point
    (proj_width, proj_height) = projector_resolution

    corner_coords = sorted(corners, key=lambda x: (x[1], x[0]))  # Sort by y first, then x
    top_left, top_right = sorted(corner_coords[:2], key=lambda x: x[0])
    bottom_left, bottom_right = sorted(corner_coords[2:], key=lambda x: x[0])

    src_points = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    dst_points = np.array([[0, 0], [proj_width, 0], [proj_width, proj_height], [0, proj_height]], dtype=np.float32)

    perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)

    # Apply perspective transform to the input point
    point_homogeneous = np.array([[x, y]], dtype=np.float32).reshape(-1, 1, 2)  # Input point as 1x1x2 array
    transformed_point = cv2.perspectiveTransform(point_homogeneous, perspective_matrix)

    # Extract the x, y coordinates of the transformed point
    projected_x, projected_y = transformed_point[0][0]

    # Check if the point lies within the projector's screen boundaries
    if 0 <= projected_x <= proj_width and 0 <= projected_y <= proj_height:
        return (int(projected_x), int(projected_y))
    else:
        return 0


if __name__ == "__main__":
    point = (400, 300)  # The point in the photo
    corners = [(100, 100), (500, 100), (500, 400), (100, 400)]  # Corners of the screen in the photo
    photo_resolution = (800, 600)  # Photo's resolution (width, height)
    projector_resolution = (1920, 1080)  # Projector's resolution (width, height)

    result = map_point_to_projector(point, corners, photo_resolution)
    if result != 0:
        print(f"The point {point} in the photo corresponds to {result} on the projector screen.")
    else:
        print(f"The point {point} is outside the projector screen.")
