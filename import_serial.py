import serial
import time

# Replace with your actual port
SERIAL_PORT = "/dev/cu.usbserial-1230"
BAUDRATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    print(f"Connected to {SERIAL_PORT} at {BAUDRATE} baud.\nWaiting for data...\n")

    time.sleep(2)  # Let the microcontroller reset if needed

    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode("utf-8", errors="ignore").strip()
            print(f"Received: {data}")

except serial.SerialException as e:
    print(f"Serial error: {e}")
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial port closed.")
