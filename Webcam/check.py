import cv2

# Open the webcam
cap = cv2.VideoCapture(0)

# List of common property IDs and their names
properties = {
    cv2.CAP_PROP_FRAME_WIDTH: "Frame Width",
    cv2.CAP_PROP_FRAME_HEIGHT: "Frame Height",
    cv2.CAP_PROP_BRIGHTNESS: "Brightness",
    cv2.CAP_PROP_CONTRAST: "Contrast",
    cv2.CAP_PROP_SATURATION: "Saturation",
    cv2.CAP_PROP_HUE: "Hue",
    cv2.CAP_PROP_GAIN: "Gain",
    cv2.CAP_PROP_EXPOSURE: "Exposure",
    cv2.CAP_PROP_AUTOFOCUS: "AutoFocus",
    cv2.CAP_PROP_FOCUS: "Focus",
}

print("=== Webcam Property Support Check ===")
for prop_id, prop_name in properties.items():
    value = cap.get(prop_id)
    # If value is -1, it usually means "not supported" on Mac
    if value == -1 or value == 0:
        print(f"{prop_name}: Not supported or 0")
    else:
        print(f"{prop_name}: {value}")

cap.release()