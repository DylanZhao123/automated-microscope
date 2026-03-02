from PIL import Image, ImageDraw, ImageFont

def add_red_number_to_image(image_path, number, position, font_size=1000, output_path=r"C:\Users\Graph\OneDrive\Desktop\automated microscope\trials\Alex\output\try.JPG"):
    # Open an image file
    with Image.open(image_path) as img:
        draw = ImageDraw.Draw(img)

        # Load a font
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            # If the specified font is not available, load the default font
            font = ImageFont.load_default()

        # Define the text color (red)
        text_color = (255, 0, 0)

        # Add text on the image
        draw.text(position, str(number), fill=text_color, font=font)

        # Save the edited image
        img.save(output_path)

# Example usage
add_red_number_to_image(r"C:\Users\Graph\OneDrive\Desktop\automated microscope\trials\Alex\output\processed_DSC00769.JPG", 5, position=(10, 10))
