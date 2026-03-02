"""
Batch test script to process multiple images.

Usage:
    python batch_test.py <input_dir> <output_dir> [num_images]

Example:
    python batch_test.py ../../trials/0820_2/input ./test_output 5
"""

import sys
import os
import json
import cv2
import glob

# Add parent directories to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.dirname(script_dir))  # 2DMatGMM-main

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


def batch_test(input_dir, output_dir, num_images=5, use_flatfield=False):
    """
    Batch test detection on multiple images.

    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save output images
        num_images: Number of images to process
        use_flatfield: Whether to apply flatfield correction
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Find input images
    image_patterns = [
        os.path.join(input_dir, "*.JPG"),
        os.path.join(input_dir, "*.jpg"),
        os.path.join(input_dir, "*.png"),
    ]
    image_files = []
    for pattern in image_patterns:
        image_files.extend(glob.glob(pattern))

    if not image_files:
        print(f"Error: No images found in {input_dir}")
        return

    # Limit to num_images
    image_files = sorted(image_files)[:num_images]
    print(f"Found {len(image_files)} images to process")

    # Load parameter file
    param_file = config.PARAM_FILE
    if not os.path.exists(param_file):
        # Try alternative locations
        for alt_path in [
            os.path.join(os.path.dirname(__file__), "..", "final_f.json"),
            os.path.join(os.path.dirname(__file__), "..", "retrain", "final_f.json"),
            os.path.join(os.path.dirname(__file__), "..", "GMMDetector", "trained_parameters", "Graphene_GMM.json"),
        ]:
            if os.path.exists(alt_path):
                param_file = alt_path
                break

    print(f"Loading parameters from: {param_file}")
    with open(param_file, 'r') as f:
        contrast_dict = json.load(f)

    # Create detector
    print(f"Creating detector with supported layers: {config.SUPPORTED_LAYERS}")
    detector = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=config.SIZE_THRESHOLD,
        standard_deviation_threshold=config.STD_THRESHOLD,
        used_channels="BGR",
        supported_layers=config.SUPPORTED_LAYERS,
    )

    # Load flatfield if requested
    flatfield = None
    if use_flatfield:
        flatfield_path = os.path.join(os.path.dirname(__file__), "flatfield.JPG")
        if os.path.exists(flatfield_path):
            flatfield = cv2.imread(flatfield_path)
            print("Using flatfield correction")

    # Process each image
    results = []
    for i, image_path in enumerate(image_files):
        print(f"\n[{i+1}/{len(image_files)}] Processing: {os.path.basename(image_path)}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"  Error: Could not read image")
            continue

        # Apply flatfield correction if requested
        if flatfield is not None:
            image = remove_vignette(image, flatfield)

        # Crop image
        image_cropped = image[
            config.CROP_Y_START:config.CROP_Y_END,
            config.CROP_X_START:config.CROP_X_END
        ]

        # Detect flakes
        flakes = detector.detect_flakes(image_cropped)
        print(f"  Found {len(flakes)} flakes")

        if len(flakes) > 0:
            # Get best flake
            best_flake = max(flakes, key=lambda f: f.confidence)
            print(f"  Best flake:")
            print(f"    Layer: {best_flake.layer}")
            print(f"    Confidence: {best_flake.confidence:.2%}")
            print(f"    Area (um2): {int(best_flake.area * 0.3844**2)}")

            # Visualize
            confidence_threshold = 0.5
            annotated = visualise_flakes(flakes, image_cropped, confidence_threshold)

            # Save output
            output_filename = f"processed_{os.path.basename(image_path)}"
            output_path = os.path.join(output_dir, output_filename)
            cv2.imwrite(output_path, annotated)
            print(f"  Saved to: {output_filename}")

            results.append({
                "input": os.path.basename(image_path),
                "output": output_filename,
                "layer": best_flake.layer,
                "confidence": float(best_flake.confidence),
                "area_um2": int(best_flake.area * 0.3844**2),
                "center": best_flake.center,
            })
        else:
            print(f"  No flakes detected")
            results.append({
                "input": os.path.basename(image_path),
                "output": None,
                "layer": None,
                "confidence": 0.0,
                "area_um2": 0,
            })

    # Save summary
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved to: {summary_path}")
    print(f"\nProcessed {len(image_files)} images")
    print(f"Detected flakes in {sum(1 for r in results if r['output'] is not None)} images")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    num_images = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    batch_test(input_dir, output_dir, num_images)


if __name__ == "__main__":
    main()
