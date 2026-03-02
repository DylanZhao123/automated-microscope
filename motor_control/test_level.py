import motor_functions as mf

mf.initialize()
mf.move_to(-10,-10)
mf.ser.close()
print("Serial connection closed")