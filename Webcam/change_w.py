import cv2

# Open the C920 webcam (usually index 0)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow backend for better control on Windows

# Disable autofocus (0 = manual, 1 = auto)
cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

# Set manual focus (range depends on camera, often 0 to 255)
cap.set(cv2.CAP_PROP_FOCUS, 30)  # Try different values like 0 (near) to 255 (far)

# Optional: set other properties
cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
cap.set(cv2.CAP_PROP_CONTRAST, 0.5)
cap.set(cv2.CAP_PROP_EXPOSURE, -6)  # Negative = manual exposure

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow('C920 Webcam', frame)

    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
