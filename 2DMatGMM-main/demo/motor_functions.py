import serial
import sys

try:
    import config
except ImportError:
    class config:
        SERIAL_PORT = "COM3"
        SERIAL_BAUDRATE = 115200
        STEP_LENGTH = 3

# Initialize serial connection with error handling
try:
    ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUDRATE, timeout=1)
except serial.SerialException as e:
    print(f"Error: Could not open serial port {config.SERIAL_PORT}: {e}")
    print("Motor control will not be available.")
    ser = None

def initialize():
    """Initialize the motor controller."""
    if ser is None:
        print("Error: Serial connection not available")
        return -1

    try:
        ser.flushInput()
        ser.flushOutput()
        incoming_data = ser.readline().decode('utf-8').rstrip()
        incoming_data = ser.readline().decode('utf-8').rstrip()
        incoming_data = ser.readline().decode('utf-8').rstrip()
        print(f"{incoming_data}")
        incoming_data = ser.readline().decode('utf-8').rstrip()
        print(f"{incoming_data}")
        ser.write(b"$X\n")
        incoming_data = ser.readline().decode('utf-8').rstrip()
        print(f"{incoming_data}")
        return 0
    except Exception as e:
        print(f"Error initializing motor: {e}")
        return -1

def move_to(a, b):
    """Move to specified coordinates."""
    if ser is None:
        return -1

    try:
        gcode = f"G0 X{a} Y{b}"
        ser.write(gcode.encode('utf-8') + b'\n')
        return 0
    except Exception as e:
        print(f"Error moving to ({a}, {b}): {e}")
        return -1

def receive_data():
    """Receive data from motor controller."""
    if ser is None:
        return

    try:
        incoming_data = ser.readline().decode('utf-8').rstrip()
        print(f"{incoming_data}")
    except Exception as e:
        print(f"Error receiving data: {e}")

def cleanup():
    """Clean up and close serial connection."""
    if ser is None:
        return

    try:
        move_to(0, 0)
        ser.flushInput()
        ser.flushOutput()
        ser.close()
        print("Serial disconnected!")
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Motor movement parameters
STEP_LENGTH = config.STEP_LENGTH
