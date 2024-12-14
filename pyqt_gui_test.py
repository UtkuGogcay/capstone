import sys
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QTransform
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsItem, \
    QGraphicsLineItem


class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, x, y, radius=10):
        super().__init__(x - radius, y - radius, 2 * radius, 2 * radius)
        self.setBrush(QColor(255, 0, 0))  # Red color for the point
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)  # Make the point draggable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)  # To track position changes

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)  # Allow the item to be moved with the mouse
        self.update()  # Update the item position


class MainWindow(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Set up the view size and transformation to flip Y-axis
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setSceneRect(100, 100, 640, 360)  # Adjust scene dimensions (max_x, max_y)



        # Add two draggable points to the scene
        self.point1 = DraggablePoint(100, 100)  # First point at (100, 300)
        elf.point2 = DraggablePoint(500, 100)  # Second point at (500, 100)
        self.scene.addItem(self.point1)
        self.scene.addItem(self.point2)

        # Add a line connecting point1 and point2
        self.line = QGraphicsLineItem(self.point1.x() + self.point1.boundingRect().width() / 2,
                                      self.point1.y() + self.point1.boundingRect().height() / 2,
                                      self.point2.x() + self.point2.boundingRect().width() / 2,
                                      self.point2.y() + self.point2.boundingRect().height() / 2)
        self.line.setPen(QPen(QColor(0, 0, 255), 2))  # Blue line
        self.scene.addItem(self.line)

        # Update the line initially
        self.updateLine()

        self.setWindowTitle("Draggable Points with Dynamic Line in PyQt6")
        self.setGeometry(100, 100, 800, 600)

    def drawBackground(self, painter, rect):
        # No background grid is drawn, so just clear this method or leave it empty
        pass

    def updateLine(self):
        # Update the line to connect point1 and point2
        p1 = self.point1.scenePos() + QPointF(self.point1.boundingRect().width() / 2,
                                              self.point1.boundingRect().height() / 2)
        p2 = self.point2.scenePos() + QPointF(self.point2.boundingRect().width() / 2,
                                              self.point2.boundingRect().height() / 2)
        self.line.setLine(p1.x(), p1.y(), p2.x(), p2.y())

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # Update the line position whenever any point is dragged
        self.updateLine()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
