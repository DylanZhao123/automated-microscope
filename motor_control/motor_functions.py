import time
import serial

ser=serial.Serial('COM3', 115200, timeout=1)

def initialize():
    incoming_data=ser.readline().decode('utf-8').rstrip()
    incoming_data=ser.readline().decode('utf-8').rstrip()
    incoming_data=ser.readline().decode('utf-8').rstrip()
    print(f"{incoming_data}")
    incoming_data=ser.readline().decode('utf-8').rstrip()
    print(f"{incoming_data}")
    ser.write(b"$X\n")
    incoming_data=ser.readline().decode('utf-8').rstrip()
    print(f"{incoming_data}")
    return 0

def move_to(a,b):
    gcode=f"G0 X{a} Y{b}"
    print(gcode)
    ser.write(gcode.encode('utf-8')+b'\n')
    return 0

def get_axis_values():
    input_str=input()
    parts=input_str.split()
    if len(parts)>=1:
        try:
            X_axis=int(parts[0])
            if len(parts)==2:
                Y_axis=int(parts[1])
            else:
                Y_axis=0
        except ValueError:
            print("Oops!")
            return 0,0
        return X_axis,Y_axis
    else:
        print("Oops!")
        return 0,0

def receive_data():
    incoming_data=ser.readline().decode('utf-8').rstrip()
    print(f"{incoming_data}")

X_LENGTH=11.6
Y_LENGTH=11.6
X_MAX=X_LENGTH*3.707
Y_MAX=Y_LENGTH*3.707
#X_MAX=15
#Y_MAX=15
STEP_LENGTH=3
