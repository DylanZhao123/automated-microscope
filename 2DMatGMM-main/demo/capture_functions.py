import time
import pyautogui
import cv2
import json
import queue
import os
import sys

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import config
except ImportError:
    # Fallback if config not imported
    class config:
        PARAM_FILE = "../final_f.json"
        FLATFIELD_IMAGE = "flatfield.JPG"
        SIZE_THRESHOLD = 1800
        STD_THRESHOLD = 3
        CROP_Y_START = 94
        CROP_Y_END = 1969
        CROP_X_START = 614
        CROP_X_END = 2489
        SCALE_FACTOR = 67.9

import motor_functions as mf
import edge_identify as ei
from GMMDetector import MaterialDetector
from demo_functions import visualise_flakes, remove_vignette


image_queue = queue.Queue()
detected_flakes_list = []  # List to store information about detected flakes
captured_images_list = []

scale = config.SCALE_FACTOR


def detect(output_dir, probability):
    """Detect flakes in captured images from queue."""
    print("Detecting has started")

    # Load parameters with error handling
    param_file = config.PARAM_FILE
    if not os.path.exists(param_file):
        # Try alternative locations
        param_file = os.path.join(os.path.dirname(__file__), "..", "final_f.json")
    if not os.path.exists(param_file):
        param_file = os.path.join(os.path.dirname(__file__), "..", "retrain", "final_f.json")
    if not os.path.exists(param_file):
        print(f"Error: Parameter file not found. Tried: {config.PARAM_FILE}")
        return

    try:
        with open(param_file, "r") as f:
            contrast_dict = json.load(f)
    except Exception as e:
        print(f"Error loading parameter file: {e}")
        return

    model = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=config.SIZE_THRESHOLD,
        standard_deviation_threshold=config.STD_THRESHOLD,
        used_channels="BGR",
    )

    # Load flatfield with error handling
    flatfield_path = config.FLATFIELD_IMAGE
    if not os.path.exists(flatfield_path):
        flatfield_path = os.path.join(os.path.dirname(__file__), "flatfield.JPG")
    if not os.path.exists(flatfield_path):
        print(f"Warning: Flatfield image not found at {config.FLATFIELD_IMAGE}, skipping vignette correction")
        flatfield = None
    else:
        flatfield = cv2.imread(flatfield_path)

    while True:
        try:
            image_path, X_axis, Y_axis, x_wafer, y_wafer = image_queue.get(timeout=50)
        except queue.Empty:
            break

        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not read image {image_path}")
            continue

        # Apply vignette correction if flatfield available
        if flatfield is not None:
            image = remove_vignette(image, flatfield)

        # Crop to region of interest
        image = image[
            config.CROP_Y_START:config.CROP_Y_END,
            config.CROP_X_START:config.CROP_X_END
        ]

        flakes = model.detect_flakes(image)
        flag = False

        # Check if any flake meets confidence threshold
        flag = any(flake.confidence > probability for flake in flakes)

        if flag:
            # Visualize and save annotated image
            annotated_image = visualise_flakes(
                flakes,
                image,
                confidence_threshold=probability,
            )

            output_path = os.path.join(output_dir, f"processed_{os.path.basename(image_path)}")
            cv2.imwrite(output_path, annotated_image)

            # Associate detected image with coordinates
            for flake in flakes:
                if flake.confidence > probability:
                    detected_flakes_list.append((
                        output_path, X_axis, Y_axis, flake.center, x_wafer, y_wafer
                    ))
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