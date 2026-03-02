import time
import serial
import motor_functions as mf

mf.initialize()
Y_axis=0
while True:
    Y_axis+=1
    mf.move_to(0,Y_axis)
    time.sleep(1)
    if(Y_axis>=40):
        break
mf.ser.close()
print("byebye!")