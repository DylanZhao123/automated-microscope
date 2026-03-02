import sys, os
sys.path.append(os.path.abspath(".."))
import os, json, cv2
from GMMDetector import MaterialDetector

IMAGE_DIR = "/Users/jason/Desktop/automated microscope/images"
PARAM_PATH = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"

contrast_dict = json.load(open(PARAM_PATH, "r"))

model = MaterialDetector(
    contrast_dict=contrast_dict,
    size_threshold=500,
    standard_deviation_threshold=11,
    used_channels="BGR",
)

CONFIDENCE_THRESHOLD = 0.5

print("Reading images from:", IMAGE_DIR)
imgs = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".tif",".tiff"))]
print("Found", len(imgs), "images:", imgs)

for name in imgs:
    path = os.path.join(IMAGE_DIR, name)
    image = cv2.imread(path)
    if image is None:
        print("Cannot read:", name)
        continue

    flakes = model.detect_flakes(image)
    kept = [flake for flake in flakes if getattr(flake, "confidence", 1.0) >= CONFIDENCE_THRESHOLD]

    print("\n==", name, "==")
    print("Detected flakes:", len(flakes), " | after threshold:", len(kept))
    for flake in kept[:20]:
        print("center:", flake.center, "layer:", getattr(flake, "layer", None), "conf:", getattr(flake, "confidence", None))

print("\nDone.")
