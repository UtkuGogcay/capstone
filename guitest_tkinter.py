import math
from types import new_class

import cv2
import tkinter as tk
from tkinter import Label, Canvas, Button
from PIL import Image, ImageTk

WIDTH = 1280
HEIGHT = 720
NEW_HEIGHT=360
NEW_WIDTH=math.floor(NEW_HEIGHT * WIDTH / HEIGHT)
class CameraApp:
    def __init__(self, root):
        #Initializes the GUI and camera feed.
        self.root = root
        self.root.title("Camera Feed")
        # Start capturing video from the default camera (index 0)
        self.cap = cv2.VideoCapture(0,cv2.CAP_DSHOW)
        # Check if the camera opened successfully
        if not self.cap.isOpened():
            print("Error: Could not open video stream.")
            return

        # Create a canvas to display the camera feed
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        self.canvas = Canvas(root, width=WIDTH, height=HEIGHT)

        #self.canvas = Canvas(root, width=640, height=640*self.frame_width/self.frame_height)
        self.canvas.pack()

        # Add a button to print the current coordinates of the interactive points
        self.print_button = Button(root, text="Print", command=self.print_coordinates)
        self.print_button.pack()


        # Points for the interactive rectangle
        self.points = [(100, 100), (540, 100), (540, 380),
                       (100, 380)]  # Initial corner positions (top-left, top-right, bottom-right, bottom-left)
        self.point_radius = 8
        self.dragging_point = None

        # Bind mouse events to handle point dragging
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        # Start updating the frame
        self.update_frame()

        # Close the camera feed when the window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_frame(self):
        #Grabs the latest frame from the camera and updates the canvas widget.
        ret, frame = self.cap.read()  # Read the frame from the camera
        if ret:
            # Convert the frame from BGR (used by OpenCV) to RGB (used by PIL/Tkinter)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert the frame to an image that Tkinter can use
            img = Image.fromarray(frame)

            new_img = Image.fromarray(cv2.resize(frame, (NEW_WIDTH, NEW_HEIGHT)))
            imgtk = ImageTk.PhotoImage(image=new_img)

            # Draw the frame on the canvas
            self.canvas.create_image(0, 0, anchor="nw", image=imgtk)
            self.canvas.imgtk = imgtk  # Keep a reference to avoid garbage collection

            # Draw interactive points and rectangle **after** the frame is drawn
            self.draw_interactive_points()

        # Call this method again after a short delay (33ms = ~30fps)
        self.root.after(33, self.update_frame)

    def draw_interactive_points(self):
        #Draws the points and rectangle connecting them on the canvas.
        self.canvas.delete("point")  # Clear previous points and rectangle

        # Draw the rectangle connecting the points as a transparent outline (only the border, no fill)
        self.canvas.create_polygon(
            *[coord for point in self.points for coord in point],
            outline="red", width=2, fill="", tags="point"
        )

        # Draw draggable points
        for x, y in self.points:
            self.canvas.create_oval(
                x - self.point_radius, y - self.point_radius,
                x + self.point_radius, y + self.point_radius,
                fill="blue", outline="black", tags="point"
            )

    def on_click(self, event):
        #Handles mouse click to detect if a point is being clicked.
        for i, (x, y) in enumerate(self.points):
            if abs(event.x - x) <= self.point_radius and abs(event.y - y) <= self.point_radius:
                self.dragging_point = i  # Select the point to be dragged
                break

    def on_drag(self, event):
        #Handles mouse dragging to move a selected point.
        if self.dragging_point is not None:
            # Ensure the dragged point stays within the bounds of the canvas
            x = min(max(event.x, 0), NEW_WIDTH)  # Limit x
            y = min(max(event.y, 0),NEW_HEIGHT )  # Limit y

            # Update the position of the dragged point
            self.points[self.dragging_point] = (x, y)
            self.draw_interactive_points()

    def on_close(self):
        #Releases the camera and destroys the GUI window.
        print("Closing application...")
        self.cap.release()  # Release the camera
        self.root.destroy()  # Destroy the GUI window

    def print_coordinates(self):
        #Prints the coordinates of the four interactive points relative to the video feed.
        # Get the current resolution of the video feed
        ret, frame = self.cap.read()
        if ret:
            frame_height, frame_width = frame.shape[:2]

            # Map the canvas points (relative to 640x480) to the camera's resolution
            scaled_points = [
                (int(x * frame_width / WIDTH), int(y * frame_height /HEIGHT))
                for x, y in self.points
            ]
            print("Corner Points (relative to video feed):", scaled_points)


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
