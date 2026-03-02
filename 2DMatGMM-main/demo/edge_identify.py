import cv2
import numpy as np
import matplotlib.pyplot as plt

def is_sample_present(image_path, threshold=100, max_bg_pixels=1000):
    image = cv2.imread(image_path)
    image = image[94:1000, 2300:2489]
    red_channel = image[:,:,0]
    _, thresholded = cv2.threshold(red_channel, threshold, 255, cv2.THRESH_BINARY)
    white_pixel_count = np.sum(thresholded == 255)
    #print(white_pixel_count)
    return white_pixel_count >= max_bg_pixels

def choose_threshold(image_path):
    image = cv2.imread(image_path)
    image = image[94:1969, 614:2489]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    plt.hist(gray.ravel(), bins=256, range=[0,256])
    plt.title('Grayscale Histogram')
    plt.xlabel('Gray level')
    plt.ylabel('Frequency')
    plt.show()


def show_histogram(image_path1):
    image1 = cv2.imread(image_path1)
    image1 = image1[94:1000, 2300:2489]
    # Calculate the histogram for the green channel of each image
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