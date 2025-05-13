import sys
import cv2
import pyautogui
import serial
import threading
import time
import numpy as np
import logging
import queue
import subprocess



class LaserDetectionSystem:
    def __init__(self, camera_index, serial_port, baudrate, projector_corners,camera_width,camera_height):
        # Config
        self.CAMERA_INDEX = camera_index
        self.CAMERA_WIDTH = camera_width
        self.CAMERA_HEIGHT = camera_height
        self.SCREEN_WIDTH = 1920
        self.SCREEN_HEIGHT = 1080
        self.MAX_GUN_SIGNAL_AGE = 200  # ms

        self.lower_red = np.array([0, 100, 100])
        self.upper_red = np.array([10, 255, 255])

        self.lower_red2 = np.array([170, 100, 100])
        self.upper_red2 = np.array([180, 255, 255])
        # Signals

        # State
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.projector_corners = np.array(projector_corners, dtype=np.float32)

        # Components
        self.serial_connection = None
        self.camera = None
        self.gun_signal_queue = queue.Queue()
        self.stop_event = threading.Event()
        # Homography
        src = np.float32(projector_corners)
        dst = np.float32([[0, 0], [self.SCREEN_WIDTH, 0], [self.SCREEN_WIDTH, self.SCREEN_HEIGHT], [0, self.SCREEN_HEIGHT]])
        self.screen_homography_matrix = cv2.getPerspectiveTransform(src, dst)

        # Logger
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
        self.logger = logging.getLogger("LaserSystem")
        self.cv2_backend=cv2.CAP_ANY
        self.platform=sys.platform
        if self.platform=="win32":
            self.cv2_backend = cv2.CAP_DSHOW
        else:
            self.cv2_backend=cv2.CAP_AVFOUNDATION
        self.button_to_key={"A1":"f","A2":"g","B1":"o","B2":"p"} #TODO Tolga'ya sor
    def map_point_to_projector(self, point):
        x, y = point
        point_homogeneous = np.array([[x, y]], dtype=np.float32).reshape(-1, 1, 2)
        transformed_point = cv2.perspectiveTransform(point_homogeneous, self.screen_homography_matrix)
        projected_x, projected_y = transformed_point[0][0]

        if 0 <= projected_x <= self.SCREEN_WIDTH and 0 <= projected_y <= self.SCREEN_HEIGHT:
            return int(projected_x), int(projected_y)
        else:
            return None

    def handle_old_gun_signals(self, old_signals):
        if old_signals:
            print(old_signals)
            self.logger.warning(f"Handling {len(old_signals)} old gun signals.:{old_signals} ")

    def read_serial(self):
        try:
            while not self.stop_event.is_set():
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.readline().decode("utf-8").strip().lower()
                    self.logger.info(f"Received from serial: {data}")
                    gun_signal = None
                    if data.startswith("a"):
                        gun_signal = "A1"
                    elif data.startswith("b"):
                        gun_signal = "A2"
                    elif data.startswith("c"):
                        gun_signal = "B1"
                    elif data.startswith("d"):
                        gun_signal = "B2"
                    if gun_signal:
                        self.gun_signal_queue.put((gun_signal, time.time() * 1000))

        except serial.SerialException as e:
            self.logger.error(f"Serial error: {e}")
            self.serial_connection = None

    def process_frame(self, frame):
        # Convert the frame to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Create masks for the red color ranges
        mask1 = cv2.inRange(hsv, self.lower_red, self.upper_red)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        potential_spots = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 5 < area < 500:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    potential_spots.append({'center': (cX, cY), 'area': area})

        laser_spot = None
        if potential_spots:
            best_spot = max(potential_spots, key=lambda spot: spot['area'])
            laser_spot = best_spot['center']
            cv2.circle(frame, best_spot['center'], 5, (0, 255, 0), -1)

        if laser_spot:
            self.logger.info(f"IR Laser Detected at: {laser_spot}")
            gun_signal = None
            old_signals = []
            while not self.gun_signal_queue.empty():
                signal, timestamp = self.gun_signal_queue.get()
                if time.time() * 1000 - timestamp > self.MAX_GUN_SIGNAL_AGE:
                    old_signals.append((signal, timestamp))
                else:
                    gun_signal = signal
                    break

            self.handle_old_gun_signals(old_signals)

            if gun_signal:
                if self.map_point_to_projector(laser_spot):
                    print("FIRE!!!!!!")
                    self.logger.info(f"Gun Fired: Gun {gun_signal}, at {laser_spot} which is mapped to {self.map_point_to_projector(laser_spot)}")
                    # TODO: Handle HID output
                    # x,y=self.map_point_to_projector(laser_spot)
                    # key=self.button_to_key.get(gun_signal,None)
                    # if key is not None:
                    #     pyautogui.moveTo(x,y)
                    #     pyautogui.press(key)
                    # else:
                    #     self.logger.error(f"Gun signal {gun_signal} not mapped to any key.")
                    # On Mac go to:
                    # System Settings -> Privacy & Security -> Accessibility
                    # Add your Terminal App to the list and give it permission. Without this PyAutoGUI cant control the mouse or keyboard.
                else:
                    self.logger.info("Gun fired but point is outside projector screen.")

        if len(self.projector_corners) == 4:
            cv2.polylines(frame, [self.projector_corners.astype(np.int32)], True, (0, 255, 255), 2)

        return frame

    def camera_feed(self):
        self.camera = cv2.VideoCapture(self.CAMERA_INDEX, self.cv2_backend)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAMERA_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAMERA_HEIGHT)

        if not self.camera.isOpened():
            self.logger.error("Could not open camera.")
            return

        while not self.stop_event.is_set():
            ret, frame = self.camera.read()
            if not ret:
                self.logger.error("Could not read frame.")
                break

            processed_frame = self.process_frame(frame)
            cv2.imshow("Camera Feed", cv2.resize(processed_frame, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.stop_event.set()
                break

        self.camera.release()
        cv2.destroyAllWindows()

    def start_serial(self):
        try:
            self.serial_connection = serial.Serial(self.serial_port, self.baudrate, timeout=1)
            self.logger.info(f"Connected to serial port: {self.serial_port}")
            time.sleep(2)  # Wait for serial to settle
        except serial.SerialException as e:
            self.logger.error(f"Serial connection failed: {e}")

    def start_external_app(self, app_path):
        # Safely try to start the external application
        if app_path:
            try:
                subprocess.Popen(app_path)
                self.logger.info(f"Started external application: {app_path}")
            except Exception as e:
                self.logger.error(f"Failed to start app: {e}")
        else:
            self.logger.critical("No external app path provided. Skipping launch.")

    def run(self, external_app_path=None):
        try:
            self.start_external_app(external_app_path)
        except Exception as e:
            self.logger.critical(f"Failed to start external application: {e}")
            return
        self.start_serial()
        if self.platform=="win32":
            camera_thread = threading.Thread(target=self.camera_feed)
            camera_thread.start()

        if self.serial_connection:
            serial_thread = threading.Thread(target=self.read_serial)
            serial_thread.start()
        else:
            self.logger.critical("Serial connection failure.")
        if self.platform!="win32":
            self.camera_feed()
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Exiting...")
            self.stop_event.set()

        if self.serial_connection:
            self.serial_connection.close()
            self.logger.info("Closed serial connection.")

def run_detection_app():
    projector_corners = [...]
    system = LaserDetectionSystem(
        camera_index=0,
        serial_port="COM6",
        baudrate=115200,
        projector_corners=projector_corners,
        camera_width=1920,
        camera_height=1080,
    )
    system.run()

# COMMENTED OUT FOR IMPORTING THE LOGIC INSIDE gui.py
""" if __name__ == "__main__":
    external_app_path = "C:\\Users\\Public\\Desktop\\Notepad++.lnk"  # Example
    serial_port = "COM6"
    baudrate = 115200
    projector_corners = [
        (346, 204),
        (905, 185),
        (943, 538),
        (301, 542),
    ]

    system = LaserDetectionSystem(
        camera_index=0,
        serial_port=serial_port,
        baudrate=baudrate,
        projector_corners=projector_corners,
        camera_width=1920,
        camera_height=1080,
    )

    system.run(external_app_path)
 """