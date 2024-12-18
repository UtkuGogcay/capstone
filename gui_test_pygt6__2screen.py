import cv2
import sys
import numpy as np
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QImage, QPixmap, QGuiApplication
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget


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

class AnotherWindow(QMainWindow):
    width_s=0
    height_s=0
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Feed")

        screen_geometry = QGuiApplication.primaryScreen().geometry()
        self.width_s = int(screen_geometry.width()*0.9)
        self.height_s = int(screen_geometry.height()*0.9)
        self.label = QLabel(self)

        self.label.resize(self.width_s, self.height_s)
        self.setGeometry(0,0,self.width_s,self.height_s)
        self.print_button = QPushButton('Confirm', self)
        self.print_button.clicked.connect(self.confirm_pressed)

        # Create a QVBoxLayout and set it to the central widget
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.print_button)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Open the webcam (camera index 0)
        self.capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Start the timer to update the camera feed
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30 milliseconds

        # Variables for the draggable points
        self.points = [QPoint(100, 100), QPoint(300, 100), QPoint(300, 300), QPoint(100, 300)]  # Initial positions
        self.dragging = None  # None means no point is being dragged

        self.last_pos = QPoint()  # To track the last position of the mouse

        # Event handlers for mouse drag
        self.label.setMouseTracking(True)
        self.label.mousePressEvent = self.mousePressEvent
        self.label.mouseMoveEvent = self.mouseMoveEvent
        self.label.mouseReleaseEvent = self.mouseReleaseEvent


    def update_frame(self):
        ret, frame = self.capture.read()
        if ret:
            # Convert the frame from BGR to RGB (for display in PyQt)
            frame_rgb = cv2.cvtColor(cv2.resize(frame, (self.width_s, self.height_s)), cv2.COLOR_BGR2RGB)

            # Draw the draggable points on the frame with transparency
            overlay = frame_rgb.copy()
            for point in self.points:
                cv2.circle(overlay, (point.x(), point.y()), 10, (0, 255, 0, 127), -1)  # Green circle with alpha 127

            # Blend the overlay with the original frame
            frame_rgb = cv2.addWeighted(overlay, 0.5, frame_rgb, 0.5, 0)

            # Draw the polygon connecting the points
            points_np = np.array([[(point.x(), point.y()) for point in self.points]], np.int32)
            frame_rgb = cv2.polylines(frame_rgb, points_np, isClosed=True, color=(0, 0, 255), thickness=2)

            # Convert the frame to QImage
            height, width, channels = frame_rgb.shape
            bytes_per_line = channels * width
            qimg = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

            # Set the QImage to the label
            self.label.setPixmap(QPixmap.fromImage(qimg))

    def mousePressEvent(self, event):
        # Check if the mouse press is inside any of the circles (points)
        for i, point in enumerate(self.points):
            if (event.position().toPoint() - point).manhattanLength() <= 10:  # 10 is the radius of the circle
                self.dragging = i  # Start dragging this point
                self.last_pos = event.position().toPoint()
                break

    def mouseMoveEvent(self, event):
        if self.dragging is not None:
            # Move the selected point with the mouse
            delta = event.position().toPoint() - self.last_pos
            new_x = self.points[self.dragging].x() + delta.x()
            new_y = self.points[self.dragging].y() + delta.y()

            # Limit the points to within the bounds of the video feed
            new_x = max(0, min(self.width_s, new_x))
            new_y = max(0, min(self.height_s, new_y))

            # Update the point position with the limited coordinates
            self.points[self.dragging] = QPoint(new_x, new_y)

            self.last_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        self.dragging = None  # Stop dragging

    def confirm_pressed(self):
        #TODO - map coordinates from screen to video feed
        #TODO - implement signal sending to main window
        self.close()

    def closeEvent(self, event):
        # Release the camera when closing the application
        self.capture.release()
        event.accept()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.button = QPushButton("Calibrate")
        self.button.clicked.connect(self.show_new_window)
        self.setCentralWidget(self.button)

    def show_new_window(self, checked):
        self.w = AnotherWindow()
        self.w.showMaximized()
        print()


app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.exec()