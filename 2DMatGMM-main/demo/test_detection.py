"""
Test script to verify MaterialDetector outputs correct visualizations.

Usage:
    python test_detection.py <image_path> [output_path]

Example:
    python test_detection.py ../../trials/0820_2/input/DSC00256.JPG test_output.jpg
"""

import sys
import os
import json
import cv2

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


def test_detection(image_path, output_path=None, use_flatfield=False):
    """
    Test detection on a single image.

    Args:
        image_path: Path to input image
        output_path: Path to save output (default: processed_<input_name>)
        use_flatfield: Whether to apply flatfield correction
    """
    # Load parameter file (use Graphene_GMM.json - validated and working)
    param_file = None
    for alt_path in [
        os.path.join(os.path.dirname(__file__), "..", "GMMDetector", "trained_parameters", "Graphene_GMM.json"),
        config.PARAM_FILE,
    ]:
        if os.path.exists(alt_path):
            param_file = alt_path
            break

    if param_file is None:
        print("Error: No parameter file found")
        return

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

    # Load image
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return

    print(f"Original image size: {image.shape}")

    # Apply flatfield correction if requested
    if use_flatfield:
        flatfield_path = os.path.join(os.path.dirname(__file__), "flatfield.JPG")
        if os.path.exists(flatfield_path):
            flatfield = cv2.imread(flatfield_path)
            print("Applying flatfield correction")
            image = remove_vignette(image, flatfield)

    # Crop image
    image_cropped = image[
        config.CROP_Y_START:config.CROP_Y_END,
        config.CROP_X_START:config.CROP_X_END
    ]
    print(f"Cropped image size: {image_cropped.shape}")

    # Detect flakes
    print("Detecting flakes...")
    flakes = detector.detect_flakes(image_cropped)
    print(f"Found {len(flakes)} flakes")

    # Print flake information
    for i, flake in enumerate(flakes):
        print(f"\nFlake {i+1}:")
        print(f"  Layer: {flake.layer}")
        print(f"  Center: {flake.center}")
        print(f"  Confidence: {flake.confidence:.2%}")
        print(f"  Area (pixels): {flake.area:.0f}")
        print(f"  Area (um2): {int(flake.area * 0.3844**2)}")
        print(f"  Bbox: {flake.bbox}")

    # Visualize
    if len(flakes) > 0:
        print("\nGenerating visualization...")
        confidence_threshold = 0.5
        annotated = visualise_flakes(flakes, image_cropped, confidence_threshold)

        # Save output
        if output_path is None:
            output_path = f"processed_{os.path.basename(image_path)}"

        cv2.imwrite(output_path, annotated)
        print(f"Saved output to: {output_path}")
    else:
        print("No flakes detected above threshold")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    image_path = sys.argv[1]

    # Default output directory
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        # Default to new_outputs folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        output_dir = os.path.join(project_root, "new_outputs")
        os.makedirs(output_dir, exist_ok=True)

        # Generate output filename from input
        input_filename = os.path.basename(image_path)
        output_filename = f"processed_{input_filename}"
        output_path = os.path.join(output_dir, output_filename)

    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    # Use flatfield correction by default (same as batch_test_selected.py)
    test_detection(image_path, output_path, use_flatfield=True)


if __name__ == "__main__":
    main()
