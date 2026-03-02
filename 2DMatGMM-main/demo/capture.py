import time
import pyautogui
import cv2
import json
import threading
import queue
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import motor_functions as mf
from GMMDetector import MaterialDetector
from demo_functions import visualise_flakes, remove_vignette


image_queue = queue.Queue()
detected_flakes_list = []  # List to store information about detected flakes


def detect(output_dir):
    print("Detecting has started")
    contrast_dict = json.load(open("C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/gaussian_mixture_model_contrast_data1.json", "r"))
    model = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=5000,
        standard_deviation_threshold=3,
        used_channels="BGR",
    )
    flatfield = cv2.imread("C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-main/train_images/DSC00014.JPG")

    while True:
        print("detecting new image")
        try:
            image_path, X_axis, Y_axis = image_queue.get(timeout=13)
        except queue.Empty:
            break
            
        image = cv2.imread(image_path)
        image = remove_vignette(image, flatfield)
        image = image[0:4128, 1100:5092]
        flakes = model.detect_flakes(image)
        flag = False

        if set(flakes):
            for flake in flakes:
                if (1 - flake.false_positive_probability) > 0.2:
                    flag = True
                    break

        if flag:
            # Visualize and save annotated image
            annotated_image = visualise_flakes(
                flakes,
                image,
                confidence_threshold=0.2,
            )
            output_path = os.path.join(output_dir, f"processed_{os.path.basename(image_path)}")
            cv2.imwrite(output_path, annotated_image)
            print("Detected new flakes and saved annotated image:", output_path)
            
            # Associate detected image with coordinates based on capture count
            detected_flakes_list.append((image_path, X_axis, Y_axis))
            print(f"Detected flakes in: {image_path} at X_axis={X_axis}, Y_axis={Y_axis}")
            
        else:
            print(f"No flakes detected in: {image_path}")

    image_queue.task_done()
    print("task is complete")


def capture():
    pyautogui.keyDown('1')
    time.sleep(2)
    pyautogui.keyUp('1')
    time.sleep(1.5)


class ImageHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.new_file_path = None

    def on_created(self, event):
        if not event.is_directory:
            self.new_file_path = event.src_path
            print(f"Detected new file in folder: {self.new_file_path}")

def capture_image(input_folder):
    print("Capturing has started")
    X_axis = Y_axis = 0
    captured_times = 0
    # Set up file monitoring for 'XXX' folder
    folder_to_watch = input_folder
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    try:
        while X_axis <= mf.X_MAX:
            while Y_axis <= mf.Y_MAX + mf.STEP_LENGTH:
                capture()  # Assume this function captures an image or performs an action
                captured_times += 1
                
                # Check if a new file path is detected
                new_file_path = event_handler.new_file_path
                if new_file_path:       
                    print("adding new image to queue")  
                    image_queue.put((new_file_path,X_axis,Y_axis))
                
                # Move to the next position
                Y_axis += mf.STEP_LENGTH
                mf.move_to(X_axis, Y_axis)
                time.sleep(1.5)

            # Move to the next column
            X_axis += mf.STEP_LENGTH
            Y_axis = 0
            mf.move_to(X_axis, Y_axis)
            time.sleep(4)

        print("Capture complete")

    except Exception as e:
        print(f"Error during capture: {e}")

    finally:
        # Clean up or return to initial position
        mf.move_to(0, 0)
        observer.stop()
        observer.join()


if __name__ == "__main__":
    input_folder = "C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-main/demo/trial6/input"
    output_folder = "C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-main/demo/trial6/output"

    mf.initialize()
    pyautogui.click(672, 17)
    time.sleep(1)

    try:
        print("Starting capture")
        capture_thread = threading.Thread(target=capture_image, args=(input_folder,))
        capture_thread.start()

        print("Starting detect")
        detect_thread = threading.Thread(target=detect, args=(output_folder,))
        detect_thread.start()

        # Wait for threads to complete
        capture_thread.join()
        detect_thread.join()

        # Use detected_flakes_list somewhere else as needed
        print("Detected flakes list:", detected_flakes_list)
        
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Stopping threads...")

    finally:
        # Perform cleanup
        image_queue=queue.Queue()
        image_queue.join()
        mf.ser.close()
        print("Serial connection closed")
