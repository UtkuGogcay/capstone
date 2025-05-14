import sys
import cv2
import numpy as np
import serial.tools.list_ports
import serial
import logging

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QWidget,
    QVBoxLayout, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QGraphicsLineItem, QHBoxLayout, QSizePolicy, QComboBox, QMessageBox
)
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QSize
from PyQt6.QtWidgets import QGraphicsPixmapItem
from cv2_enumerate_cameras import enumerate_cameras
from detect import LaserDetectionSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gui")

CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

class Communicator(QObject):
    coordinates_confirmed = pyqtSignal(list)

class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, x, y, radius=8):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.setPos(x, y)
        self.setBrush(QBrush(Qt.GlobalColor.transparent))
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
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.frame_size = None
        self.pixmap_size = None

    def showEvent(self, event):
        self.showMaximized()

    def show_camera_error(self):
        logger.error(f"Could not open camera with index {self.camera_index}.")
        error_msg = QMessageBox(self)
        error_msg.setIcon(QMessageBox.Icon.Critical)
        error_msg.setWindowTitle("Camera Error")
        error_msg.setText("Could not access the camera.")
        error_msg.setInformativeText("Please ensure the camera is properly connected.")
        error_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_msg.exec()
        self.close()  # Close the calibration window
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.show_camera_error()
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

        self.projector_corners = coords
        
        self.cap.release()
        self.timer.stop()
        self.communicator.coordinates_confirmed.emit(coords)
        self.close()

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        self.timer.stop()
        event.accept()

# Custom QComboBox that refreshes its list when the popup is shown
class RefreshableComboBox(QComboBox):
    def __init__(self, refresh_func, parent=None):
        super().__init__(parent)
        self._refresh_func = refresh_func

    def showPopup(self):
        if self._refresh_func:
            logger.debug("Refreshing list before showing popup...")
            self._refresh_func()
        super().showPopup()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 600, 550) # Adjusted height

        self.communicator = Communicator()
        self.communicator.coordinates_confirmed.connect(self.update_coordinates)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Device Selection Section ---
        device_layout = QVBoxLayout()
        self.main_layout.addLayout(device_layout)

        # Dropdown for camera selection (using the custom combo box)
        self.camera_label = QLabel("Select Camera:")
        device_layout.addWidget(self.camera_label)
        # Pass the populate method to the custom combo box
        self.camera_combo = RefreshableComboBox(self.populate_camera_dropdown)
        device_layout.addWidget(self.camera_combo)
        self.current_camera_index = 0
        self.camera_combo.currentIndexChanged.connect(self.update_camera_index)

        # Dropdown for COM port selection (using the custom combo box)
        self.com_port_label = QLabel("Select COM Port:")
        device_layout.addWidget(self.com_port_label)
        # Pass the populate method to the custom combo box
        self.selected_com_port = None
        self.com_port_combo = RefreshableComboBox(self.populate_com_port_dropdown)
        self.populate_com_port_dropdown() # Populate initially
        device_layout.addWidget(self.com_port_combo)
        self.com_port_combo.currentIndexChanged.connect(self.update_com_port)

        # Removed the manual Refresh button as it's now automatic
        # self.refresh_button = QPushButton("Refresh Devices")
        # self.refresh_button.clicked.connect(self.refresh_devices)
        # device_layout.addWidget(self.refresh_button)
        # --- End Device Selection Section ---


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
        self.capture_button.setEnabled(False)
        self.main_layout.addWidget(self.capture_button)

        self.start_detection_button = QPushButton("Start Detection")
        self.start_detection_button.clicked.connect(self.start_detection)
        self.start_detection_button.setEnabled(False)
        self.main_layout.addWidget(self.start_detection_button)

        self.calibrated_coordinates = None
        self.cap = None
        self.populate_camera_dropdown() # Populate initially

    def start_detection(self):

        self.detection_system = LaserDetectionSystem(
            camera_index=self.current_camera_index,
            serial_port=self.selected_com_port,
            baudrate=115200,
            projector_corners=self.calibrated_coordinates,
            camera_width=CAMERA_WIDTH,
            camera_height=CAMERA_HEIGHT,
        )
        self.detection_system.run()

    def populate_camera_dropdown(self):
        # Store current selection before clearing
        current_data = self.camera_combo.currentData()

        self.camera_combo.blockSignals(True)

        self.camera_combo.clear()
        if sys.platform== "win32":
            available_cameras = list(enumerate_cameras(cv2.CAP_DSHOW))
        else:
            available_cameras = list(enumerate_cameras(cv2.CAP_ANY))
        if available_cameras:
            for camera_info in available_cameras:
                self.camera_combo.addItem(f"{camera_info.name} (Index: {camera_info.index})", camera_info.index)

            # Try to restore previous selection
            index = self.camera_combo.findData(current_data)
            if index != -1:
                 self.camera_combo.setCurrentIndex(index)
                 # The currentIndexChanged signal will handle updating self.current_camera_index
            elif self.camera_combo.count() > 0:
                 # Default to first item if previous is not found and list is not empty
                 self.camera_combo.setCurrentIndex(0)
                 # The currentIndexChanged signal will handle updating self.current_camera_index
            else:
                 # Handle case where list is empty after refresh
                 self.current_camera_index = -1
                 self.calibrate_button.setEnabled(False)


        else:
            self.camera_combo.addItem("No cameras found", -1)
            self.current_camera_index = -1
            self.calibrate_button.setEnabled(False)
            logging.error("No cameras found.")
        self.camera_combo.blockSignals(False)
        self.update_camera_index(self.camera_combo.currentIndex())

    def update_camera_index(self, index):
        # Use itemData() to get the actual index stored
        self.current_camera_index = self.camera_combo.itemData(index)
        if self.current_camera_index is not None and self.current_camera_index != -1:
            logger.info(f"Selected camera index: {self.current_camera_index}")
        # Ensure calibrate button state is correct based on selection
        self.calibrate_button.setEnabled(self.current_camera_index is not None and self.current_camera_index != -1)

        # Reset calibration status and capture button state
        self.status_label.setText("Calibration not performed.")
        self.calibrated_coordinates = None
        self.capture_button.setEnabled(False)
        self.image_view.clear()

        # Release camera if it was open from a previous selection
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None


    def populate_com_port_dropdown(self):
        # Store current selection before clearing
        current_data = self.com_port_combo.currentData()
        self.com_port_combo.blockSignals(True)

        self.com_port_combo.clear()
        all_ports = serial.tools.list_ports.comports()
        if sys.platform!= "win32":
            ports=[port for port in all_ports if port.device.startswith("/dev/tty")]
        else:
            ports=all_ports
        if ports:
            for port in ports:
                display_text = port.description
                # Check if the description already contains the device name in parentheses
                if port.device not in display_text:  # Simple check: device name not in description
                    display_text = f"{port.description} ({port.device})"
                elif display_text.endswith(f" ({port.device})"):  # More robust check: ends with "(COMx)"
                    # Description already ends with (COMx), use description as is
                    pass
                else:  # Description contains device name, but not in the standard (COMx) format
                    # You might decide how you want to format this.
                    # For now, let's stick with the simpler display_text = port.description
                    display_text = port.description

                # Fallback if description is empty or just whitespace
                if not display_text.strip():
                    display_text = port.device

                self.com_port_combo.addItem(display_text, port.device)
            # Try to restore previous selection
            index = self.com_port_combo.findData(current_data)
            if index != -1:
                self.com_port_combo.setCurrentIndex(index)
                # The currentIndexChanged signal will handle updating self.selected_com_port
            elif self.com_port_combo.count() > 0:
                 # Default to first item if previous is not found and list is not empty
                 self.com_port_combo.setCurrentIndex(0)
                 # The currentIndexChanged signal will handle updating self.selected_com_port
            else:
                # Handle case where list is empty after refresh
                self.selected_com_port = None

        else:
            self.com_port_combo.addItem("No COM ports found", None)
            self.selected_com_port = None
            logging.error("No COM ports found.")
        self.com_port_combo.blockSignals(False)
        self.update_com_port(self.com_port_combo.currentIndex())

    def update_com_port(self, index):
        self.selected_com_port = self.com_port_combo.itemData(index)
        if self.selected_com_port:
            logger.info(f"Selected COM port: {self.selected_com_port}")

    def open_calibration_window(self):
        if self.current_camera_index is not None and self.current_camera_index != -1:
            # Ensure camera is released before opening calibration window
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None
            self.calibration_window = CalibrationWindow(self.communicator, self.current_camera_index)
            self.calibration_window.show()
        else:
            self.status_label.setText("No camera selected for calibration.")

    def update_coordinates(self, coords):
        labels = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
        text = "Calibration complete (camera coordinates):\n"
        for label, coord in zip(labels, coords):
            text += f"{label}: {coord}\n"
        self.status_label.setText(text)
        self.calibrated_coordinates = coords
        # Only enable capture if coordinates are valid (not empty list etc.)
        self.capture_button.setEnabled(self.calibrated_coordinates is not None and len(self.calibrated_coordinates) == 4)
        logger.info(f"Saved coordinates for camera {self.current_camera_index}: {self.calibrated_coordinates}")

    def capture_and_transform(self):
        # Check if a camera is selected AND coordinates are calibrated
        if self.current_camera_index is None or self.current_camera_index == -1:
             self.status_label.setText("No camera selected.")
             return
        if self.calibrated_coordinates is None or len(self.calibrated_coordinates) != 4:
            self.status_label.setText("Calibration not performed yet.")
            return

        self.cap = cv2.VideoCapture(self.current_camera_index)
        if not self.cap.isOpened():
            self.status_label.setText(f"Error: Could not open camera with index {self.current_camera_index}.")
            # Disable capture button if camera fails to open
            self.capture_button.setEnabled(False)
            return

        # Set properties only if the camera was successfully opened
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        ret, frame = self.cap.read()
        self.cap.release()

        if not ret:
            self.status_label.setText("Error: Could not capture frame.")
            return

        corner_coords = sorted(self.calibrated_coordinates, key=lambda x: (x[1], x[0]))
        top_left, top_right = sorted(corner_coords[:2], key=lambda x: x[0])
        bottom_left, bottom_right = sorted(corner_coords[2:], key=lambda x: x[0])
        ordered_coords = np.array([top_left, top_right, bottom_right, bottom_left], dtype='float32')
        src_points = np.float32(ordered_coords)

        dst_points = np.array([
            [0, 0],
            [CAMERA_WIDTH, 0],
            [CAMERA_WIDTH, CAMERA_HEIGHT],
            [0, CAMERA_HEIGHT]
        ], dtype='float32')

        try:
            matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            transformed_frame = cv2.warpPerspective(frame, matrix, (CAMERA_WIDTH, CAMERA_HEIGHT))

            rgb_image = cv2.cvtColor(transformed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.image_view.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.image_view.setPixmap(scaled_pixmap)
            # image_view size policy should handle this, adjustSize might be redundant here depending on layout
            # self.image_view.adjustSize()

        except cv2.error as e:
            logger.error(f"Error during perspective transform: {e}")
            self.status_label.setText(f"Error during perspective transform: {e}")
        self.start_detection_button.setEnabled(True)

    def resizeEvent(self, event):
        # Ensure image view scales correctly when window is resized
        if self.image_view.pixmap():
            # Get the original pixmap before scaling
            original_pixmap = QPixmap.fromImage(self.image_view.pixmap().toImage())
            scaled_pixmap = original_pixmap.scaled(self.image_view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_view.setPixmap(scaled_pixmap)
        super().resizeEvent(event) # Call the base class resize event

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())