import cv2
import serial
import threading
import time
import numpy as np
import logging
import queue  # Import the queue module

# ==============================
# Configuration
# ==============================
# Moved configuration to main function
# EXTERNAL_APP_PATH = "path/to/your/application.exe"
# SERIAL_PORT = "COM3"
# BAUDRATE = 9600
CAMERA_INDEX = 0
IR_LASER_COLOR_RANGE = ([100, 100, 240], [140, 140, 255])
MIN_LASER_PIXEL_SIZE = 5
GUN_A_SIGNAL = "ir laser fired from gun a"
GUN_B_SIGNAL = "ir laser fired from gun b"
NMS_THRESHOLD = 3
MAX_GUN_SIGNAL_AGE = 100  # milliseconds

# ==============================
# Global Variables
# ==============================
serial_connection = None
camera = None
laser_detected = False
projector_screen_corners = []
screen_homography_matrix = None
gun_signal_queue = queue.Queue()

# ==============================
# Logging Configuration
# ==============================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("ir_laser_detection.log"),
    ],
)
logger = logging.getLogger(__name__)

# ==============================
# Helper Functions
# ==============================
def calculate_area(contour):
    """Calculates the area of a contour."""
    return cv2.contourArea(contour)


def find_largest_contour(contours):
    """Finds the largest contour based on area."""
    if not contours:
        return None
    return max(contours, key=calculate_area)


def get_centroid(contour):
    """Calculates the centroid of a contour."""
    M = cv2.moments(contour)
    if M["m00"] != 0:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        return (cX, cY)
    else:
        return None


def is_within_screen(point, screen_corners):
    """
    Checks if a point is within the quadrilateral defined by the screen corners.
    This uses the point-in-polygon test.
    """
    if not screen_corners or len(screen_corners) != 4:
        return True  # Consider it inside if corners are not defined yet.

    x, y = point
    inside = False
    p1x, p1y = screen_corners[0]
    for i in range(4):
        p2x, p2y = screen_corners[(i + 1) % 4]
        if ((p1y > y) != (p2y > y)) and (x < (p2x - p1x) * (y - p1y) / (p2y - p1y) + p1x):
            inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def find_projector_screen(frame):
    """
    Detects the projector screen in the frame.
    Now, this function only uses the pre-defined corners.
    """
    global projector_screen_corners
    if len(projector_screen_corners) == 4:
        return np.array(projector_screen_corners, dtype=np.float32)
    else:
        return None


def calculate_homography(src_points, dst_points):
    """
    Calculates the homography matrix to transform from source points to
    destination points.
    """
    if len(src_points) >= 4 and len(dst_points) >= 4:
        H, _ = cv2.findHomography(src_points, dst_points)
        return H
    return None


def transform_point(point, H):
    """
    Transforms a point using the homography matrix.
    """
    if H is None:
        return point  # Return original point if no homography matrix

    x, y = point
    homogeneous_point = [x, y, 1]
    transformed_point = H.dot(homogeneous_point)
    transformed_x = transformed_point[0] / transformed_point[2]
    transformed_y = transformed_point[1] / transformed_point[2]
    return (int(transformed_x), int(transformed_y))


def non_max_suppression(detections, threshold):
    """
    Applies non-maximum suppression to a list of detections.
    Args:
        detections: A list of tuples, where each tuple is (center_x, center_y, area).
        threshold: The distance threshold for merging detections.
    Returns:
        A list of filtered detections.
    """
    filtered_detections = []
    while detections:
        best_detection = detections.pop(0)
        x1, y1, _ = best_detection
        filtered_detections.append(best_detection)
        detections = [
            d for d in detections if (d[0] - x1) ** 2 + (d[1] - y1) ** 2 > threshold ** 2
        ]
    return filtered_detections


def handle_old_gun_signals(old_signals):
    """
    Handles gun signals that are older than MAX_GUN_SIGNAL_AGE.
    This function is currently empty, but you can add your logic here.

    Args:
        old_signals: A list of tuples, where each tuple is (signal, timestamp).
    """
    if old_signals:
        logger.warning(f"Handling {len(old_signals)} old gun signals.")
        for signal, timestamp in old_signals:
            logger.debug(f"Old signal: {signal} at {timestamp}")
            # Add your logic here to handle old gun signals.
            pass


# ==============================
# Thread Functions
# ==============================
def read_serial():
    """Reads data from the serial port and sets the global variable."""
    global serial_connection, gun_signal_queue
    try:
        while serial_connection and serial_connection.is_open:
            if serial_connection.in_waiting > 0:
                data = serial_connection.readline().decode("utf-8").strip().lower()
                logger.debug(f"Received from serial: {data}")
                if GUN_A_SIGNAL in data:
                    gun_signal = "A"
                    logger.info("Gun A fired signal received")
                elif GUN_B_SIGNAL in data:
                    gun_signal = "B"
                    logger.info("Gun B fired signal received")
                elif "ready" in data:
                    gun_signal = "ready"
                    logger.info("Serial port is ready")
                else:
                    gun_signal = None  # important: clear other signals
                if gun_signal:
                    gun_signal_queue.put((gun_signal, time.time() * 1000))  # Add to the queue
    except serial.SerialException as e:
        logger.error(f"Serial error: {e}")
        if serial_connection:
            serial_connection.close()
        serial_connection = None
    except Exception as e:
        logger.error(f"Error reading from serial port: {e}")
        if serial_connection:
            serial_connection.close()
        serial_connection = None


def process_frame(frame):
    """
    Processes a single frame from the camera for IR laser detection.
    """
    global laser_detected, projector_screen_corners, screen_homography_matrix, gun_signal_queue

    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_bound, upper_bound = IR_LASER_COLOR_RANGE
    mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for contour in contours:
        area = calculate_area(contour)
        if area > MIN_LASER_PIXEL_SIZE:
            center = get_centroid(contour)
            if center:
                detections.append((center[0], center[1], area))

    filtered_detections = non_max_suppression(detections, NMS_THRESHOLD)

    laser_detected = False
    if filtered_detections:
        best_detection = filtered_detections[0]
        center_x, center_y, _ = best_detection
        center = (center_x, center_y)
        if projector_screen_corners:
            center = transform_point(center, screen_homography_matrix)
        if is_within_screen(center, projector_screen_corners):
            laser_detected = True
            logger.info(f"IR Laser Detected at: {center}")
            gun_signal = None
            # Check for gun signals in the queue
            old_signals = []
            while not gun_signal_queue.empty():
                signal, timestamp = gun_signal_queue.get()
                if time.time() * 1000 - timestamp > MAX_GUN_SIGNAL_AGE:
                    old_signals.append((signal, timestamp))
                else:
                    gun_signal = signal # get the latest valid signal
                    break
            handle_old_gun_signals(old_signals)

            if gun_signal:
                logger.info(f"Gun Fired: Gun {gun_signal}")
            cv2.circle(frame, center, 5, (0, 255, 0), -1)

    # Attempt to find the projector screen. Now it uses the global variable.
    if not projector_screen_corners:
        projector_screen_corners_local = find_projector_screen(frame)
        if projector_screen_corners_local is not None:
            projector_screen_corners = projector_screen_local
            logger.info("Projector screen found")
            frame_width = frame.shape[1]
            frame_height = frame.shape[0]
            dst_points = np.array(
                [[0, 0], [frame_width - 1, 0], [frame_width - 1, frame_height - 1], [0, frame_height - 1]],
                dtype=np.float32,
            )
            screen_homography_matrix = calculate_homography(
                projector_screen_corners.astype(np.float32), dst_points
            )

    # draw the screen
    if projector_screen_corners:
        cv2.polylines(frame, [projector_screen_corners.astype(np.int32)], True, (0, 255, 255), 2)
    return frame


def camera_feed():
    """
    Opens the camera, reads frames, and processes them.
    """
    global camera
    try:
        camera = cv2.VideoCapture(CAMERA_INDEX)
        if not camera.isOpened():
            error_message = "Error: Could not open camera."
            logger.error(error_message)
            print(error_message)
            return

        while True:
            ret, frame = camera.read()
            if not ret:
                error_message = "Error: Could not read frame."
                logger.error(error_message)
                print(error_message)
                break

            processed_frame = process_frame(frame)

            cv2.imshow("Camera Feed", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except Exception as e:
        logger.error(f"Camera error: {e}")
        print(f"Camera error: {e}")
    finally:
        if camera:
            camera.release()
        cv2.destroyAllWindows()


# ==============================
# Main Function
# ==============================
def main(
    external_app_path,
    serial_port,
    baudrate,
    projector_corners,
):
    """
    Main function to start the external app, initialize serial communication,
    and start the camera feed and serial reading threads.
    """
    global serial_connection, projector_screen_corners

    # 0. Set the projector screen corners.
    projector_screen_corners = np.array(projector_corners, dtype=np.float32)

    # 1. Start the external application
    try:
        subprocess.Popen(external_app_path)
        logger.info(f"Started external application: {external_app_path}")
    except Exception as e:
        logger.error(f"Error starting external application: {e}")
        print(f"Error starting external application: {e}")  # Keep print

    # 2. Initialize serial communication
    try:
        serial_connection = serial.Serial(serial_port, baudrate, timeout=1)
        logger.info(f"Connected to serial port: {serial_port} at {baudrate} baud")
        time.sleep(2)
    except serial.SerialException as e:
        logger.error(f"Error connecting to serial port: {e}")
        print(f"Error connecting to serial port: {e}")  # Keep print
        serial_connection = None

    # 4. Start camera feed and serial reading in separate threads
    camera_thread = threading.Thread(target=camera_feed)
    camera_thread.daemon = True
    camera_thread.start()

    if serial_connection:
        serial_thread = threading.Thread(target=read_serial)
        serial_thread.daemon = True
        serial_thread.start()

    # Keep the main thread alive to handle exceptions and prevent immediate exit.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        logger.info("Exiting...")
    finally:
        if serial_connection:
            serial_connection.close()
        logger.info("Closed serial connection.")
        print("Closed serial connection.")


if __name__ == "__main__":
    # Example usage:
    external_app_path = "path/to/your/application.exe"  # Replace
    serial_port = "COM3"  # Replace
    baudrate = 9600  # Replace
    projector_corners = [
        (100, 200),
        (600, 200),
        (600, 400),
        (100, 400),
    ]  # Example corners

    main(external_app_path, serial_port, baudrate, projector_corners)

