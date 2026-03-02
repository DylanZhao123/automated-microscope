"""
Convert old parameter format to new format.

Old format: {"1": {"contrast": {r, g, b}, "covariance_matrix": [...]}, ...}
New format: {"bg_rgb": [...], "classes": {"BG": {...}, "1L": {...}, ...}}
"""

import json
import sys
import os

def convert_params(old_params, bg_rgb=None):
    """
    Convert old parameter format to new format.

    Args:
        old_params: Dict with old format
        bg_rgb: Background RGB values (default: [160, 160, 160])

    Returns:
        Dict with new format
    """
    if bg_rgb is None:
        bg_rgb = [160, 160, 160]

    new_params = {
        "bg_rgb": bg_rgb,
        "classes": {}
    }

    # Add default background class
    # Assuming background has mean near 0 and moderate variance
    new_params["classes"]["BG"] = {
        "mu": [0.0, 0.0, 0.0],
        "cov": [
            [0.0002, 0.0, 0.0],
            [0.0, 0.0002, 0.0],
            [0.0, 0.0, 0.0002]
        ]
    }

    # Convert numbered layers
    for i in range(1, 6):
        layer_key = str(i)
        if layer_key in old_params:
            layer_data = old_params[layer_key]

            # Extract contrast values as mu
            contrast = layer_data.get("contrast", {})
            mu = [
                contrast.get("r", 0.0),
                contrast.get("g", 0.0),
                contrast.get("b", 0.0)
            ]

            # Extract covariance matrix
            cov = layer_data.get("covariance_matrix", [
                [0.0001, 0.0, 0.0],
                [0.0, 0.0001, 0.0],
                [0.0, 0.0, 0.0001]
            ])

            layer_name = f"{i}L"
            new_params["classes"][layer_name] = {
                "mu": mu,
                "cov": cov
            }

    return new_params


def main():
    """Convert parameter file from command line."""
    if len(sys.argv) < 2:
        print("Usage: python convert_params.py <input_file> [output_file]")
        print("\nConverts old parameter format to new format.")
        print("If output_file not specified, prints to stdout.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    # Load old parameters
    with open(input_file, 'r') as f:
        old_params = json.load(f)

    # Check if already in new format
    if "classes" in old_params:
        print("File already in new format")
        sys.exit(0)

    # Convert
    new_params = convert_params(old_params)

    # Output
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(new_params, f, indent=2)
        print(f"Converted parameters saved to {output_file}")
    else:
        print(json.dumps(new_params, indent=2))


if __name__ == "__main__":
    main()
