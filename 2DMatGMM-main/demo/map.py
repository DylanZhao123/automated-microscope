import json
from PIL import Image, ImageDraw, ImageFont
import os
import math
import motor_functions as mf

def add_red_border(image, number, border_width = 5):
    # Convert the image to RGB mode if it's not already
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create a drawing context
    draw = ImageDraw.Draw(image)

    try:
            font = ImageFont.truetype("arial.ttf", 100)
    except IOError:
        # If the specified font is not available, load the default font
        font = ImageFont.load_default()

    # Define the text color (red)
    text_color = (255, 0, 0)
    # Add text on the image
    draw.text((1,1), str(number), fill=text_color, font=font)
    
    # Get image dimensions
    width, height = image.size
    
    # Draw the border lines
    draw.rectangle(
        [(0, 0), (width - 1, height - 1)],  # Coordinates of the border's outer edge
        outline='red',  # Border color
        width=border_width  # Border width
    )
    
    # Return the image with the border
    return image

def mapping(target_folder):
    # Load image information from JSON-like list

    scale = 67.8

    X_LIMIT, Y_LIMIT = scale*3, scale*3

    image_json = os.path.join(target_folder, f"captured_images_list.json")
    flake_json = os.path.join(target_folder, f"detected_flakes_list.json")

    with open(image_json) as f:
        image_list = json.load(f)

    # Dimensions of each individual square image (assuming they are all the same size)
    image_width = 300  # replace with actual width of your images
    image_height = 300  # replace with actual height of your images

    # Number of images in each row and column
    num_images_x = math.ceil(X_LIMIT/mf.STEP_LENGTH) + 1  # replace with the actual number of images in x direction
    num_images_y = math.ceil(Y_LIMIT/mf.STEP_LENGTH) + 1  # replace with the actual number of images in y direction

    # Calculate total size of the final image
    final_width = num_images_x * image_width
    final_height = num_images_y * image_height

    # Create a blank image to stitch the smaller images onto
    result_image = Image.new('RGB', (final_width, final_height))

    # Iterate through the images in image_list
    for item in image_list:
        path = item[0]
        y = round(item[1]/3) + math.ceil(item[3]*scale/3)
        x = round(item[2]/3) + math.ceil(item[4]*scale/3)

        try:
            # Open the image file using PIL
            current_image = Image.open(path)

            current_image = current_image.crop((614, 94, 2489, 1969))
            
            # Resize the image to match the expected size if necessary
            current_image = current_image.resize((image_width, image_height), Image.Resampling.LANCZOS)
            
            # Calculate the paste position on the result image
            paste_x = x * image_width
            paste_y = (num_images_y - y - 1) * image_height
            
            # Paste the current image onto the result image
            result_image.paste(current_image, (paste_x, paste_y))

            #print(f"image at {x},{y} pasted")
        except IOError:
            print(f"Error: Unable to open image file {path}")

    # Save the resulting image
    #print("saving image")
    #result_image.save(r"C:\Users\Graph\OneDrive\Desktop\automated microscope\2DMatGMM-main\demo\trial13\stitched_image.png")

    with open(flake_json) as f:
        flake_list = json.load(f)

    i=1

    for item in flake_list:
        path = item[0]
        y = round(item[1]/3) + math.ceil(item[4]*scale/3)
        x = round(item[2]/3) + math.ceil(item[5]*scale/3)

        try:
            # Open the image file using PIL
            current_image = Image.open(path)
            
            # Resize the image to match the expected size if necessary
            current_image = current_image.resize((image_width, image_height), Image.Resampling.LANCZOS)

            current_image = add_red_border(current_image, i)
            
            # Calculate the paste position on the result image
            paste_x = x * image_width
            paste_y = (num_images_y - y - 1) * image_height
            
            # Paste the current image onto the result image
            result_image.paste(current_image, (paste_x, paste_y))

            i+=1

            #print(f"image at {x},{y} pasted")
        except IOError:
            print(f"Error: Unable to open image file {path}")

    result_image.save(os.path.join(target_folder, f"map.png"))
    #print("showing image")
    # Optionally, display the resulting image
    result_image.show()
