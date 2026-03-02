import time
import pyautogui
import cv2
import json
import queue
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import motor_functions as mf
import edge_identify as ei
from GMMDetector import MaterialDetector
from demo_functions import visualise_flakes, remove_vignette


image_queue = queue.Queue()
detected_flakes_list = []  # List to store information about detected flakes
captured_images_list = []

scale = 67.9


def detect(output_dir, probability):
    print("Detecting has started")
    contrast_dict = json.load(open("C:/Users/Graph/OneDrive/Desktop/automated microscope/retrain/final_f.json", "r"))
    model = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=1800,
        standard_deviation_threshold=3,
        used_channels="BGR",
    )
    flatfield = cv2.imread(r"C:\Users\Graph\OneDrive\Desktop\automated microscope\2DMatGMM-main\demo\flatfield.JPG")

    while True:
        #print("detecting new image")
        try:
            image_path, X_axis, Y_axis, x_wafer, y_wafer = image_queue.get(timeout=50)
        except queue.Empty:
            break
            
        image = cv2.imread(image_path)
        #print(image_path)
        image = remove_vignette(image, flatfield)
        image = image[94:1969, 614:2489]
        flakes = model.detect_flakes(image)
        flag = False

        flag = any((1 - flake.false_positive_probability) > probability for flake in flakes)

        if flag:
            # Visualize and save annotated image
            annotated_image = visualise_flakes(
                flakes,
                image,
                confidence_threshold=probability,
            )
            
            output_path = os.path.join(output_dir, f"processed_{os.path.basename(image_path)}")
            cv2.imwrite(output_path, annotated_image)
            #print("Detected new flakes and saved annotated image:", output_path)
            
            # Associate detected image with coordinates based on capture count
            for flake in flakes:
                if (1 - flake.false_positive_probability) > probability:
                    detected_flakes_list.append((output_path, X_axis, Y_axis, flake.center, x_wafer, y_wafer))
            print(f"Detected flakes at X_axis={X_axis}, Y_axis={Y_axis}")
            
        else:
            print(f"No flakes detected at X_axis={X_axis}, Y_axis={Y_axis}")

    image_queue.task_done()
    print("task is complete")


def capture(interval):
    pyautogui.keyDown('1')
    time.sleep(interval)
    pyautogui.keyUp('1')
    time.sleep(0.5)


def recapture(X_axis, Y_axis, event_handler, last_file_path):
    mf.move_to(X_axis+mf.STEP_LENGTH, Y_axis-mf.STEP_LENGTH)
    time.sleep(0.8)
    capture(2)
    new_file_path = event_handler.new_file_path
    if new_file_path != last_file_path:
        mf.move_to(X_axis, Y_axis)
        pyautogui.press('p')
        time.sleep(0.5)
        pyautogui.press('1')
    else:
        mf.move_to(X_axis-mf.STEP_LENGTH, Y_axis-mf.STEP_LENGTH)
        time.sleep(0.8)
        capture(2)
        new_file_path = event_handler.new_file_path
        if new_file_path != last_file_path:
            mf.move_to(X_axis, Y_axis)
            time.sleep(0.5)
            pyautogui.press('p')
            time.sleep(0.5)
            pyautogui.press('1')
        else:
            mf.move_to(X_axis-mf.STEP_LENGTH, Y_axis+mf.STEP_LENGTH)
            time.sleep(0.8)
            capture(2)
            new_file_path = event_handler.new_file_path
            if new_file_path != last_file_path:
                mf.move_to(X_axis, Y_axis)
                time.sleep(0.5)
                pyautogui.press('p')
                time.sleep(0.5)
                pyautogui.press('1')
            else:
                mf.move_to(X_axis+mf.STEP_LENGTH, Y_axis+mf.STEP_LENGTH)
                time.sleep(0.8)
                capture(2)
                new_file_path = event_handler.new_file_path
                if new_file_path != last_file_path:
                    mf.move_to(X_axis, Y_axis)
                    time.sleep(0.5)
                    pyautogui.press('p')
                    time.sleep(0.5)
                    pyautogui.press('1')
                else:
                    pyautogui.press('p')
    time.sleep(0.5)
    pyautogui.press('p')
    new_file_path = event_handler.new_file_path
    
    return new_file_path
    


class ImageHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.new_file_path = None

    def on_created(self, event):
        if not event.is_directory:
            self.new_file_path = event.src_path
            #print(f"Detected new file in folder: {self.new_file_path}")

def capture_image(input_folder, x_wafer, y_wafer):
    print("Capturing has started")
    X_axis, Y_axis = 0, 0

    X_LIMIT, Y_LIMIT = 80, 80
    
    folder_to_watch = input_folder
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()
    last_file_path = None

    x_min, y_min = mf.STEP_LENGTH, mf.STEP_LENGTH
    x_max = x_min

    try:
        while X_axis <= X_LIMIT and X_axis <= x_max + mf.STEP_LENGTH:
            y_max = y_min
            while Y_axis <= Y_LIMIT and Y_axis <= y_max + mf.STEP_LENGTH:
                mf.move_to(X_axis + x_wafer*scale, Y_axis + y_wafer*scale)
                time.sleep(0.5)

                capture_attempt = 0
                captured = False

                while capture_attempt < 2 and not captured:
                    capture(capture_attempt+0.01)  # Try capturing image
                    #captured_times += 1
                    new_file_path = event_handler.new_file_path

                    if new_file_path != last_file_path:
                        image_queue.put((new_file_path, X_axis, Y_axis, x_wafer, y_wafer))
                        captured_images_list.append((new_file_path, X_axis, Y_axis, x_wafer, y_wafer))
                        captured = True
                    else:
                        capture_attempt += 1
                        time.sleep(1)  # Adjust as needed for retry interval

                if capture_attempt == 2:
                    new_file_path = recapture(X_axis + x_wafer*scale, Y_axis + y_wafer*scale, event_handler, last_file_path)
                    if new_file_path != last_file_path and new_file_path is not None:
                        image_queue.put((new_file_path, X_axis, Y_axis, x_wafer, y_wafer))
                        captured_images_list.append((new_file_path, X_axis, Y_axis, x_wafer, y_wafer))
                
                #identify the edge
                if ei.is_sample_present(new_file_path):
                    if X_axis > x_max and X_axis > x_min:
                        x_max = X_axis
                    if Y_axis > y_max and Y_axis > y_min:
                        y_max = Y_axis
                #identifying ends

                last_file_path = new_file_path
                
                # Move to the next position
                Y_axis += mf.STEP_LENGTH
        
            # Move to the next column
            X_axis += mf.STEP_LENGTH
            Y_axis = 0
            mf.move_to(X_axis + x_wafer*scale, Y_axis + y_wafer*scale)
            time.sleep(4)

        print("Capture complete")

    except Exception as e:
        print(f"Error during capture: {e}")

    finally:
        # Clean up or return to initial position
        mf.move_to(x_wafer*scale, y_wafer*scale)
        observer.stop()
        observer.join()