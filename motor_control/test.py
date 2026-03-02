import time
import serial
import pyautogui
import motor_functions as mf
import msvcrt


def capture_image():
    X_axis=Y_axis=0
    while True:
        while True:
            Y_axis+=mf.STEP_LENGTH
            mf.move_to(X_axis,Y_axis)
            msvcrt.getch()
            if(Y_axis>=mf.Y_MAX):
                break
        
        Y_axis=0

        X_axis+=mf.STEP_LENGTH
        mf.move_to(X_axis,Y_axis)
        msvcrt.getch()
        if(X_axis>mf.X_MAX):
            break
    X_axis=0
    mf.move_to(X_axis,Y_axis)

mf.initialize()
pyautogui.click(672, 17)
capture_image()
mf.ser.close()
print("Serial connection closed")