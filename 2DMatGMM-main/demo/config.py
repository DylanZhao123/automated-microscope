"""
Configuration file for automated microscope system.
Update these paths according to your setup.
"""

import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Parameter files
PARAM_FILE = os.path.join(PROJECT_ROOT, "..", "final_f.json")
FLATFIELD_IMAGE = os.path.join(BASE_DIR, "flatfield.JPG")

# Detection parameters
SIZE_THRESHOLD = 1800
STD_THRESHOLD = 3
CONFIDENCE_THRESHOLD = 0.5

# Image cropping (adjust based on your camera setup)
CROP_Y_START = 94
CROP_Y_END = 1969
CROP_X_START = 614
CROP_X_END = 2489

# Motor control
SERIAL_PORT = "COM3"
SERIAL_BAUDRATE = 115200
STEP_LENGTH = 3
SCALE_FACTOR = 67.9

# Edge detection
EDGE_THRESHOLD = 100
EDGE_MAX_BG_PIXELS = 1000

# Capture limits
X_LIMIT = 80
Y_LIMIT = 80
