import cv2
import numpy as np
import matplotlib.pyplot as plt

try:
    import config
except ImportError:
    class config:
        CROP_Y_START = 94
        CROP_Y_END = 1969
        CROP_X_START = 614
        CROP_X_END = 2489
        EDGE_THRESHOLD = 100
        EDGE_MAX_BG_PIXELS = 1000

def is_sample_present(image_path, threshold=None, max_bg_pixels=None):
    """Check if sample is present in the image."""
    if threshold is None:
        threshold = config.EDGE_THRESHOLD
    if max_bg_pixels is None:
        max_bg_pixels = config.EDGE_MAX_BG_PIXELS

    image = cv2.imread(image_path)
    if image is None:
        return False

    # Use edge detection region
    image = image[config.CROP_Y_START:1000, 2300:config.CROP_X_END]
    red_channel = image[:, :, 0]
    _, thresholded = cv2.threshold(red_channel, threshold, 255, cv2.THRESH_BINARY)
    white_pixel_count = np.sum(thresholded == 255)
    return white_pixel_count >= max_bg_pixels

def choose_threshold(image_path):
    """Display histogram to help choose threshold."""
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return

    image = image[
        config.CROP_Y_START:config.CROP_Y_END,
        config.CROP_X_START:config.CROP_X_END
    ]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    plt.hist(gray.ravel(), bins=256, range=[0,256])
    plt.title('Grayscale Histogram')
    plt.xlabel('Gray level')
    plt.ylabel('Frequency')
    plt.show()


def show_histogram(image_path1):
    """Display histogram for edge detection region."""
    image1 = cv2.imread(image_path1)
    if image1 is None:
        print(f"Error: Could not read image {image_path1}")
        return

    image1 = image1[config.CROP_Y_START:1000, 2300:config.CROP_X_END]
    # Calculate the histogram for the red channel
    hist1 = cv2.calcHist([image1], [0], None, [256], [0, 256])


    # Plot the histograms
    plt.figure(figsize=(12, 6))

    plt.plot(hist1, color='green', label='Image 1 Green Channel')


    plt.title('Green Channel Histogram Comparison')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.xlim([0, 256])
    plt.legend()
    plt.grid(True)

    # Show the plot
    plt.tight_layout()
    plt.show()

if __name__=="__main__":
    #show_histogram(r"C:\Users\Graph\OneDrive\Desktop\automated microscope\trials\0805_3\input\DSC00815.JPG")
    print(is_sample_present(r"C:\Users\Graph\OneDrive\Desktop\automated microscope\trials\0805_2\input\DSC01724.JPG"))