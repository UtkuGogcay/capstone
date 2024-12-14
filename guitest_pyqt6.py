import sys
import cv2
import numpy as np
from PyQt6.QtCore import QTimer, Qt, QPoint
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton


class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Feed")
        self.setGeometry(100, 100, 640, 360)

        # Create a label to display the video feed
        self.label = QLabel(self)
        self.label.resize(640, 360)

        # Create a button to print point locations
        self.print_button = QPushButton('Print Point Locations', self)
        self.print_button.clicked.connect(self.print_point_locations)

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
            frame_rgb = cv2.cvtColor(cv2.resize(frame, (640, 360)), cv2.COLOR_BGR2RGB)

            # Draw the draggable points on the frame with transparency
            overlay = frame_rgb.copy()
            for point in self.points:
                cv2.circle(overlay, (point.x(), point.y()), 10, (0, 255, 0, 127), -1)  # Green circle with alpha 127

            # Blend the overlay with the original frame
            frame_rgb = cv2.addWeighted(overlay, 0.5, frame_rgb, 0.5, 0)

            # Draw the polygon connecting the points
            points_np = np.array([[(point.x(), point.y()) for point in self.points]], np.int32)
            frame_rgb = cv2.polylines(frame_rgb, points_np, isClosed=True, color=(0, 0, 255),
                                      thickness=2)  # Red polygon

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

            # Limit the points to within the bounds of the video feed (640x360)
            new_x = max(0, min(640, new_x))
            new_y = max(0, min(360, new_y))

            # Update the point position with the limited coordinates
            self.points[self.dragging] = QPoint(new_x, new_y)

            self.last_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        self.dragging = None  # Stop dragging

    def print_point_locations(self):
        # Print the current locations of the points
        print("Current Point Locations:")
        for i, point in enumerate(self.points):
            print(f"Point {i + 1}: ({point.x()}, {point.y()})")

    def closeEvent(self, event):
        # Release the camera when closing the application
        self.capture.release()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec())
