import time
import pyautogui
import threading
import queue
import capture_functions as cf
import motor_functions as mf

import json
import os
from tkinter import messagebox

def thread_task(variables, input_folder):
    for coords, value in variables.items():
        if value == 1:
            wafer_x, wafer_y = coords
            mf.move_to(wafer_x*cf.scale, wafer_y*cf.scale)
            time.sleep(10)
            cf.capture_image(input_folder, wafer_x, wafer_y)

def Main(probability, target_folder, input_folder, output_folder, variables):
    pyautogui.click(672, 17)
    time.sleep(1)
    try:
        #print("Starting capture")
        capture_thread = threading.Thread(target=thread_task, args=(variables, input_folder))
        capture_thread.start()

        time.sleep(10)

        #print("Starting detect")
        detect_thread = threading.Thread(target=cf.detect, args=(output_folder,probability))
        detect_thread.start()

        # Wait for threads to complete
        capture_thread.join()
        detect_thread.join()

        # Use detected_flakes_list somewhere else as needed
        print("Detected flakes list:", cf.detected_flakes_list)
        detected_json_path = os.path.join(target_folder, f"detected_flakes_list.json")
        with open(detected_json_path, 'w') as f:
            json.dump(cf.detected_flakes_list, f)

        captured_json_path = os.path.join(target_folder, f"captured_images_list.json")
        with open(captured_json_path, 'w') as f:
            json.dump(cf.captured_images_list, f)
            
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Stopping threads...")

    finally:
        # Perform cleanup
        image_queue=queue.Queue()
        image_queue.join()
        messagebox.showwarning("FINISHED", "Capturing and Detecting Flakes Has Finished")


