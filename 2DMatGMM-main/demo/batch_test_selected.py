"""
Batch test script with pre-selected images that have known flakes.
"""

import sys
import os
import json
import cv2

# Add parent directories to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(script_dir))

try:
    import config
except ImportError:
    class config:
        PARAM_FILE = "../final_f.json"
        SIZE_THRESHOLD = 1800
        STD_THRESHOLD = 3
        CROP_Y_START = 94
        CROP_Y_END = 1969
        CROP_X_START = 614
        CROP_X_END = 2489
        SUPPORTED_LAYERS = ["1L", "2L"]

from GMMDetector import MaterialDetector
from demo_functions import visualise_flakes, remove_vignette


# Pre-selected images that have flakes
SELECTED_IMAGES = [
    "DSC00009.JPG",
    "DSC00011.JPG",
    "DSC00057.JPG",
    "DSC00065.JPG",
    "DSC00074.JPG",
]


def batch_test_selected(input_dir, output_dir):
    """Batch test on pre-selected images."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {os.path.abspath(output_dir)}\n")

    # Build full paths
    image_files = []
    for filename in SELECTED_IMAGES:
        path = os.path.join(input_dir, filename)
        if os.path.exists(path):
            image_files.append(path)
        else:
            print(f"Warning: {filename} not found, skipping")

    if not image_files:
        print(f"Error: No images found in {input_dir}")
        return

    print(f"Processing {len(image_files)} images\n")

    # Load parameter file
    param_file = config.PARAM_FILE
    for alt_path in [
        os.path.join(script_dir, "..", "final_f.json"),
        os.path.join(script_dir, "..", "retrain", "final_f.json"),
        os.path.join(script_dir, "..", "GMMDetector", "trained_parameters", "Graphene_GMM.json"),
    ]:
        if os.path.exists(alt_path):
            param_file = alt_path
            break

    print(f"Parameters: {os.path.basename(param_file)}")
    with open(param_file, 'r') as f:
        contrast_dict = json.load(f)

    # Create detector
    detector = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=config.SIZE_THRESHOLD,
        standard_deviation_threshold=config.STD_THRESHOLD,
        used_channels="BGR",
        supported_layers=config.SUPPORTED_LAYERS,
    )
    print(f"Supported layers: {config.SUPPORTED_LAYERS}\n")

    # Load flatfield
    flatfield = None
    flatfield_path = os.path.join(script_dir, "flatfield.JPG")
    if os.path.exists(flatfield_path):
        flatfield = cv2.imread(flatfield_path)

    # Process each image
    results = []
    for i, image_path in enumerate(image_files):
        filename = os.path.basename(image_path)
        print(f"[{i+1}/{len(image_files)}] {filename}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"  ERROR: Could not read image\n")
            continue

        # Apply flatfield correction
        if flatfield is not None:
            image = remove_vignette(image, flatfield)

        # Crop image
        image_cropped = image[
            config.CROP_Y_START:config.CROP_Y_END,
            config.CROP_X_START:config.CROP_X_END
        ]

        # Detect flakes
        flakes = detector.detect_flakes(image_cropped)

        if len(flakes) > 0:
            # Get best flake
            best_flake = max(flakes, key=lambda f: f.confidence)
            area_um2 = int(best_flake.area * 0.3844**2)
            conf_pct = int(best_flake.confidence * 100)

            print(f"  [OK] Detected: {best_flake.layer}  {area_um2}um2  {conf_pct}%")

            # Visualize
            annotated = visualise_flakes(flakes, image_cropped, 0.5)

            # Save output
            output_filename = f"processed_{filename}"
            output_path = os.path.join(output_dir, output_filename)
            cv2.imwrite(output_path, annotated)
            print(f"  Saved: {output_filename}\n")

            results.append({
                "input": filename,
                "output": output_filename,
                "layer": best_flake.layer,
                "confidence": float(best_flake.confidence),
                "area_um2": area_um2,
                "center": best_flake.center,
            })
        else:
            print(f"  [--] No flakes detected\n")
            results.append({
                "input": filename,
                "detected": False,
            })

    # Save summary
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)

    detected_count = sum(1 for r in results if r.get("output"))
    print(f"=" * 60)
    print(f"SUMMARY: Detected flakes in {detected_count}/{len(image_files)} images")
    print(f"Output saved to: {os.path.abspath(output_dir)}")
    print(f"=" * 60)


if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "../../trials/0820_2/input"

    # Default output directory: new_outputs folder
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        output_dir = os.path.join(project_root, "new_outputs")

    batch_test_selected(input_dir, output_dir)
