import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QWidget,
    QVBoxLayout, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsLineItem, QHBoxLayout, QSizePolicy, QComboBox
)
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
from PyQt6.QtWidgets import QGraphicsPixmapItem
from cv2_enumerate_cameras import enumerate_cameras

class Communicator(QObject):
    coordinates_confirmed = pyqtSignal(list)

class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, x, y, radius=8):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.setPos(x, y)
        # Transparent fill
        self.setBrush(QBrush(Qt.GlobalColor.transparent))
        # Red border
        self.setPen(QPen(QColor("red"), 2))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setZValue(1)

    def get_center(self):
        return self.scenePos()


class CalibrationWindow(QWidget):
    def __init__(self, communicator, camera_index):
        super().__init__()
        self.setWindowTitle("Calibration")
        self.communicator = communicator
        self.camera_index = camera_index

        layout = QVBoxLayout(self)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.view)

        self.camera_item = QGraphicsPixmapItem()
        self.scene.addItem(self.camera_item)

        self.points = [
            DraggablePoint(100, 100),
            DraggablePoint(300, 100),
            DraggablePoint(300, 300),
            DraggablePoint(100, 300),
        ]
        for point in self.points:
            self.scene.addItem(point)

        self.lines = [QGraphicsLineItem() for _ in range(4)]
        pen = QPen(QColor("green"), 2)
        for line in self.lines:
            line.setPen(pen)
            self.scene.addItem(line)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.confirm_coordinates)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.frame_size = None
        self.pixmap_size = None

    def showEvent(self, event):
        self.showMaximized()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        if self.frame_size is None:
            self.frame_size = (frame.shape[1], frame.shape[0])

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        view_size = self.view.viewport().size()
        pixmap = QPixmap.fromImage(qt_image).scaled(
            view_size.width(), view_size.height(), Qt.AspectRatioMode.IgnoreAspectRatio
        )
        self.camera_item.setPixmap(pixmap)
        self.pixmap_size = (pixmap.width(), pixmap.height())

        self.update_lines()

    def update_lines(self):
        centers = [p.get_center() for p in self.points]
        for i in range(4):
            start = centers[i]
            end = centers[(i + 1) % 4]
            self.lines[i].setLine(start.x(), start.y(), end.x(), end.y())

    def confirm_coordinates(self):
        coords = []
        if self.frame_size and self.pixmap_size:
            scale_x = self.frame_size[0] / self.pixmap_size[0]
            scale_y = self.frame_size[1] / self.pixmap_size[1]

            for p in self.points:
                pos = p.get_center()
                cam_x = int(pos.x() * scale_x)
                cam_y = int(pos.y() * scale_y)
                coords.append((cam_x, cam_y))

        self.cap.release()
        self.timer.stop()
        self.communicator.coordinates_confirmed.emit(coords)
        self.close()

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        self.timer.stop()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 600, 450)  # Increased height to accommodate dropdown

        self.communicator = Communicator()
        self.communicator.coordinates_confirmed.connect(self.update_coordinates)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # Dropdown for camera selection
        self.camera_label = QLabel("Select Camera:")
        self.main_layout.addWidget(self.camera_label)
        self.camera_combo = QComboBox()
        self.populate_camera_dropdown()
        self.main_layout.addWidget(self.camera_combo)
        self.current_camera_index = 0  # Default camera index
        self.camera_combo.currentIndexChanged.connect(self.update_camera_index)

        self.status_label = QLabel("Calibration not performed.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self.open_calibration_window)
        self.main_layout.addWidget(self.calibrate_button)

        self.processed_image_label = QLabel("Selected screen :")
        self.processed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.processed_image_label)

        self.image_view = QLabel()
        self.image_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.image_view)

        self.capture_button = QPushButton("Capture the screen")
        self.capture_button.clicked.connect(self.capture_and_transform)
        self.capture_button.setEnabled(False)  # Disabled initially
        self.main_layout.addWidget(self.capture_button)

        self.calibrated_coordinates = None
        self.cap = None  # Initialize camera capture

    def populate_camera_dropdown(self):
        self.camera_combo.clear()
        available_cameras = list(enumerate_cameras(cv2.CAP_DSHOW))
        if available_cameras:
            for camera_info in available_cameras:
                self.camera_combo.addItem(f"{camera_info.name} (Index: {camera_info.index})", camera_info.index)
            self.current_camera_index = self.camera_combo.itemData(self.camera_combo.currentIndex())
        else:
            self.camera_combo.addItem("No cameras found", -1)
            self.calibrate_button.setEnabled(False)

    def update_camera_index(self, index):
        self.current_camera_index = self.camera_combo.itemData(index)
        print(f"Selected camera index: {self.current_camera_index}")
        # Optionally, you could release the current camera and prepare for a new one here
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
        self.calibrate_button.setEnabled(self.current_camera_index != -1)
        self.status_label.setText("Calibration not performed.")
        self.calibrated_coordinates = None
        self.capture_button.setEnabled(False)
        self.image_view.clear()

    def open_calibration_window(self):
        if self.current_camera_index != -1:
            self.calibration_window = CalibrationWindow(self.communicator, self.current_camera_index)
            self.calibration_window.show()
        else:
            self.status_label.setText("No camera selected.")

    def update_coordinates(self, coords):
        labels = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
        text = "Calibration complete (camera coordinates):\n"
        for label, coord in zip(labels, coords):
            text += f"{label}: {coord}\n"
        self.status_label.setText(text)
        self.calibrated_coordinates = coords
        self.capture_button.setEnabled(True)  # Enable capture button after calibration
        print(f"Saved coordinates for camera {self.current_camera_index}: {self.calibrated_coordinates}")

    def capture_and_transform(self):
        if self.calibrated_coordinates is None:
            self.status_label.setText("Calibration not performed yet.")
            return

        self.cap = cv2.VideoCapture(self.current_camera_index)
        if not self.cap.isOpened():
            self.status_label.setText(f"Error: Could not open camera with index {self.current_camera_index}.")
            return
        WIDTH = 1280
        HEIGHT = 720
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        ret, frame = self.cap.read()
        self.cap.release()  # Close the camera immediately after capturing

        if not ret:
            self.status_label.setText("Error: Could not capture frame.")
            return

        # Perform perspective transform
        corner_coords = sorted(self.calibrated_coordinates, key=lambda x: (x[1], x[0]))  # Sort by y first, then x
        top_left, top_right = sorted(corner_coords[:2], key=lambda x: x[0])
        bottom_left, bottom_right = sorted(corner_coords[2:], key=lambda x: x[0])
        ordered_coords = np.array([top_left, top_right, bottom_right, bottom_left], dtype='float32')
        src_points = np.float32(ordered_coords)

        dst_points = np.array([
            [0, 0],  # Top-left
            [WIDTH, 0],  # Top-right
            [WIDTH, HEIGHT],  # Bottom-right
            [0, HEIGHT]  # Bottom-left
        ], dtype='float32')

        try:
            matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            transformed_frame = cv2.warpPerspective(frame, matrix, (WIDTH, HEIGHT))

            # Convert the transformed frame to QImage and display
            rgb_image = cv2.cvtColor(transformed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.image_view.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.image_view.setPixmap(scaled_pixmap)
            self.image_view.adjustSize()

        except cv2.error as e:
            self.status_label.setText(f"Error during perspective transform: {e}")

    def resizeEvent(self, event):
        if self.image_view.pixmap():
            scaled_pixmap = self.image_view.pixmap().scaled(self.image_view.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.image_view.setPixmap(scaled_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())