  
# start by importing the necessary packages
import cv2
import os
#import matplotlib.pyplot as plt
#from demo_functions import visualise_flakes, remove_vignette
import json
import numpy as np
import msvcrt
from typing import List,Tuple

# import the detector
from GMMDetector import MaterialDetector

IMAGE_DIR = "C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-Main/test_images"



contrast_dict = json.load(open("C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json", "r"))


model = MaterialDetector(
    contrast_dict=contrast_dict,
    size_threshold=500,
    standard_deviation_threshold=5,
    used_channels="BGR",
)

# Set the confidence threshold to 0 to see all the flakes
CONFIDENCE_THRESHOLD = 0.5

# read the flatfield image if necessary
# flatfield = cv2.imread("flatfield.png")

#image_names = os.listdir(IMAGE_DIR)
#for image_name in image_names:
#    image_path = os.path.join(IMAGE_DIR, image_name)
#    image = cv2.imread(image_path)
#    
    # Remove vignette if necessary
    # image = remove_vignette(image, flatfield)

    # The model itself can also be called directly
    # flakes = model(flakes)
#    flakes = model.detect_flakes(image)

#    image = visualise_flakes(
#        flakes,
#        image,
#        confidence_threshold=CONFIDENCE_THRESHOLD,
#    )
#    plt.figure(figsize=(10, 10))
#    plt.imshow(image[:, :, ::-1])
#    plt.axis("off")
#    plt.show()

#image_path="C:/Users/Graph/OneDrive/Desktop/automated microscope/2DMatGMM-main/demo/images/20_20.jpg"
#image=cv2.imread(image_path)
#flakes=model.detect_flakes(image)
#flake_centers=np.array([flake.center for flake in flakes])
#print("Flake centers:",flake_centers)

def get_image_files(folder_path: str) -> List[str]:
    image_files=[]
    for file_name in os.listdir(folder_path):
        image_files.append(file_name)
    return image_files

def extract_axes_from_filename(file_name: str) -> Tuple[int,int]:
    try:
        parts=os.path.splitext(file_name)[0].split("_")
        x_axis=int(parts[0])
        y_axis=int(parts[1])
        return x_axis,y_axis
    except (IndexError, ValueError):
        return None, None
    
folder_path=IMAGE_DIR

image_files=get_image_files(folder_path)
for image_file in image_files:
    X_axis, Y_axis=extract_axes_from_filename(image_file)
    image_path=os.path.join(folder_path, image_file)
    image=cv2.imread(image_path)
    flakes=model.detect_flakes(image)
    
    for flake in flakes:
        print(f"{flake.center} {X_axis},{Y_axis}")

print("Done!")