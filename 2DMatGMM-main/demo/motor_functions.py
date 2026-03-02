import serial

ser=serial.Serial('COM3', 115200, timeout=1)

def initialize():
    ser.flushInput()
    ser.flushOutput()
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
    #print(gcode)
    ser.write(gcode.encode('utf-8')+b'\n')
    return 0

def receive_data():
    incoming_data=ser.readline().decode('utf-8').rstrip()
    print(f"{incoming_data}")

def cleanup():
    move_to(0,0)
    ser.flushInput()
    ser.flushOutput()
    ser.close()
    print("Serial disconnected!")

#X_LENGTH=11.6
#Y_LENGTH=11.6
#X_MAX=X_LENGTH*3.707
#Y_MAX=Y_LENGTH*3.707
#X_MAX=12
#Y_MAX=12
STEP_LENGTH=3
