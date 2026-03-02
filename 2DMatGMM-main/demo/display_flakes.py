import os
import cv2
import json
import motor_functions as mf
import capture_functions as cf



class Display:
    def __init__(self, flake_list_directory):
        self.flake_list_directory = flake_list_directory
        self.image = None
        self.blank_image = r"C:\Users\Graph\OneDrive\Desktop\automated microscope\2DMatGMM-main\demo\blank.png"
        self.curr_X_axis = 0
        self.curr_Y_axis = 0
        self.X_axis = []
        self.Y_axis = []

        with open(self.flake_list_directory, 'r') as f:
            json_list = json.load(f)
            self.json_list = json_list  # Keep a copy of the original json list
            self.flake_paths = [item[0] for item in json_list]
            
            # stepper motor: X axis goes up, Y axis goes right; image: X axis goes right, Y axis goes down
            self.center = [item[3] for item in json_list]  # List of centers

            for item, center in zip(json_list, self.center):
                center_x = center[0]
                center_y = center[1]
                x_adjustment = (center_x - 937) * 0.0016
                y_adjustment = (center_y - 937) * 0.0016
                self.X_axis.append(item[1] - y_adjustment + 0.0016 * 130 + item[4]*cf.scale)
                self.Y_axis.append(item[2] + x_adjustment + item[5]*cf.scale)

        self.current_index = 0

    def display(self):
        cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
        self.update_image()

        while True:
            cv2.imshow("Image", self.image)
            cv2.setWindowTitle("Image", f"{self.current_index + 1}/{len(self.flake_paths)}")
            key = cv2.waitKey(10)

            if key == 27:
                break

            if key == ord("l"):
                if self.current_index < len(self.flake_paths) - 1:
                    self.current_index += 1
                    self.update_image()

            if key == ord("j"):
                if self.current_index > 0:
                    self.current_index -= 1
                    self.update_image()

            if key == ord("k"):
                mf.move_to(self.X_axis[self.current_index], self.Y_axis[self.current_index])
                self.curr_X_axis = self.X_axis[self.current_index]
                self.curr_Y_axis = self.Y_axis[self.current_index]

            if key == ord("a"):
                mf.move_to(self.curr_X_axis, self.curr_Y_axis - 0.1)
                self.curr_X_axis = self.curr_X_axis
                self.curr_Y_axis = self.curr_Y_axis - 0.1

            if key == ord("w"):
                mf.move_to(self.curr_X_axis + 0.1, self.curr_Y_axis)
                self.curr_X_axis = self.curr_X_axis + 0.1
                self.curr_Y_axis = self.curr_Y_axis

            if key == ord("d"):
                mf.move_to(self.curr_X_axis, self.curr_Y_axis + 0.1)
                self.curr_X_axis = self.curr_X_axis
                self.curr_Y_axis = self.curr_Y_axis + 0.1

            if key == ord("s"):
                mf.move_to(self.curr_X_axis - 0.1, self.curr_Y_axis)
                self.curr_X_axis = self.curr_X_axis - 0.1
                self.curr_Y_axis = self.curr_Y_axis

            if key == ord("0"):
                self.delete_current_flake()

        cv2.destroyAllWindows()

    def update_image(self):
        self.image = cv2.imread(str(self.flake_paths[self.current_index]))

    def delete_current_flake(self):
        if len(self.flake_paths) == 0:
            return

        # Remove the current image from the list and JSON data
        del self.flake_paths[self.current_index]
        del self.X_axis[self.current_index]
        del self.Y_axis[self.current_index]
        del self.json_list[self.current_index]

        # Save the updated JSON list back to the file
        with open(self.flake_list_directory, 'w') as f:
            json.dump(self.json_list, f, indent=4)

        # Adjust current_index if it is out of bounds
        if self.current_index >= len(self.flake_paths):
            self.current_index = len(self.flake_paths) - 1

        # Update the displayed image
        if len(self.flake_paths) > 0:
            self.update_image()
        else:
            self.image = cv2.imread(self.blank_image)  # Display a blank image if no flakes are left
