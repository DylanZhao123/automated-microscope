import time
import serial
import pyautogui
import motor_functions as mf


def capture():
    pyautogui.keyDown('1')
    time.sleep(2)
    pyautogui.keyUp('1')
    time.sleep(1.5)

def capture_image():
    X_axis=Y_axis=0
    while True:
        capture()
        while True:
            Y_axis+=mf.STEP_LENGTH
            mf.move_to(X_axis,Y_axis)
            time.sleep(1.5)
            capture()
            if(Y_axis>=mf.Y_MAX):
                break
        
        Y_axis=0

        X_axis+=mf.STEP_LENGTH
        mf.move_to(X_axis,Y_axis)
        time.sleep(4)
        if(X_axis>mf.X_MAX):
            break
    X_axis=0
    mf.move_to(X_axis,Y_axis)
#while True:
#    X_axis,Y_axis=mf.get_axis_values()
#    print(X_axis,Y_axis)
#    if(X_axis==1000):
#        break1
#    mf.move_to(X_axis,Y_axis)
#    mf.receive_data()
mf.initialize()
pyautogui.click(672, 17)
time.sleep(1)
capture_image()
mf.ser.close()
print("Serial connection closed")