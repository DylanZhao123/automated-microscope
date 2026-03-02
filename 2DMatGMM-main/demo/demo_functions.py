import cv2
import matplotlib.cm as cm
import numpy as np


def visualise_flakes(
    flakes,
    image: np.ndarray,
    confidence_threshold: float = 0.5,
) -> np.ndarray:
    """Visualise the flakes on the image.

    Args:
        flakes (List[Flake]): List of flakes to visualise.
        image (np.ndarray): Image to visualise the flakes on.
        confidence_threshold (float, optional): The confidence threshold to use, flakes with less confidence are not drawn. Defaults to 0.5.

    Returns:
        np.ndarray: Image with the flakes visualised.
    """

    confident_flakes = [
        flake
        for flake in flakes
        if (1 - flake.false_positive_probability) > confidence_threshold
    ]

    # Only keep the best flake (highest confidence)
    if len(confident_flakes) > 0:
        best_flake = max(confident_flakes, key=lambda f: f.confidence)
        confident_flakes = [best_flake]
    else:
        return image.copy()

    # Magenta color for contour (matching the example output)
    magenta = (255, 0, 255)
    white = (255, 255, 255)

    image = image.copy()

    # Only one flake to draw
    flake = confident_flakes[0]
    idx = 0

    # Draw contour outline (no fill, just the outline)
    if flake.contour is not None:
        cv2.drawContours(image, [flake.contour], -1, magenta, 2)
    elif flake.bbox is not None:
        # Fallback: draw bounding box
        x, y, w, h = flake.bbox
        cv2.rectangle(image, (x, y), (x+w, y+h), magenta, 2)

    # Format text exactly as in the example: "1. 2L 304um2 84%"
    area_um2 = int(flake.size * 0.3844**2)
    confidence_pct = int((1 - flake.false_positive_probability) * 100)
    text = f"{idx + 1}. {flake.thickness}L {area_um2}um2 {confidence_pct}%"

    # Put text on the top left corner in white
    cv2.putText(
        image,
        text,
        (10, 30),
        cv2.QT_FONT_NORMAL,
        1,
        white,
        2,
    )

    # Draw a line from the text to the center of the flake (magenta)
    # Calculate text width to position line start
    text_size = cv2.getTextSize(text, cv2.QT_FONT_NORMAL, 1, 2)[0]
    line_start_x = 10 + text_size[0] + 5

    cv2.line(
        image,
        (line_start_x, 15),
        (int(flake.center[0]), int(flake.center[1])),
        magenta,
        2,
    )

    return image


def remove_vignette(
    image,
    flatfield,
    max_background_value: int = 241,
):
    """Removes the Vignette from the Image

    Args:
        image (NxMx3 Array): The Image with the Vignette
        flatfield (NxMx3 Array): the Flat Field in RGB
        max_background_value (int): the maximum value of the background

    Returns:
        (NxMx3 Array): The Image without the Vignette
    """
    image_no_vigentte = image / (flatfield+1e-6) * cv2.mean(flatfield)[:-1]
    image_no_vigentte[image_no_vigentte > max_background_value] = max_background_value
    return np.asarray(image_no_vigentte, dtype=np.uint8)
