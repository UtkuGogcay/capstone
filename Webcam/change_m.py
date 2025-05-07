import cv2

# Open the webcam (on Mac, usually index 0)
cap = cv2.VideoCapture(0)


# Brightness: typically 0.0 to 1.0 or camera-specific range
cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)

# Contrast: typically 0.0 to 1.0
cap.set(cv2.CAP_PROP_CONTRAST, 0.5)

# Saturation
cap.set(cv2.CAP_PROP_SATURATION, 0.5)

# Exposure: this can be tricky — sometimes negative values work (manual exposure)
cap.set(cv2.CAP_PROP_EXPOSURE, -4)

# You can print current settings to see if they were applied
print("Brightness:", cap.get(cv2.CAP_PROP_BRIGHTNESS))
print("Contrast:", cap.get(cv2.CAP_PROP_CONTRAST))
print("Saturation:", cap.get(cv2.CAP_PROP_SATURATION))
print("Exposure:", cap.get(cv2.CAP_PROP_EXPOSURE))

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow('Mac Webcam (C920)', frame)

    key = cv2.waitKey(1)
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
