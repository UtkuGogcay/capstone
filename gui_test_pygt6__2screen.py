from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
import cv2
import sys

from matplotlib.image import imread


class AnotherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibrate")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)  # Fullscreen mode

        # Layout for the fullscreen window
        layout = QVBoxLayout()

        # Create a label to hold a pixmap (an image)
        self.pixmap_label = QLabel(self)
        self.pixmap_label.setPixmap(QPixmap("captured_image.jpg"))  # Replace 'example.png' with the path to your image
        self.pixmap_label.setScaledContents(True)  # Make sure the image scales properly

        # Create a back button
        self.back_button = QPushButton("Back", self)
        self.back_button.clicked.connect(self.back_button_clicked)  # Close the window when the button is pressed

        # Add the label and button to the layout
        layout.addWidget(self.pixmap_label)
        layout.addWidget(self.back_button)

        # Set the layout for the window
        self.setLayout(layout)
        print(self.size())
    def back_button_clicked(self):
        self.close()

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.button = QPushButton("Push for Window")
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