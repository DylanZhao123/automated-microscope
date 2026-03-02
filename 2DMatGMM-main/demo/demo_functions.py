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

    # get a colors for each flake
    colors = cm.rainbow(np.linspace(0, 1, len(confident_flakes)))[:, :3] * 255

    image = image.copy()
    H, W = image.shape[:2]

    for idx, flake in enumerate(confident_flakes):
        # Draw contour outline instead of using mask
        if flake.contour is not None:
            # Draw filled contour with color
            overlay = image.copy()
            cv2.drawContours(overlay, [flake.contour], -1, tuple(colors[idx].tolist()), -1)
            image = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)

            # Draw contour outline
            cv2.drawContours(image, [flake.contour], -1, tuple(colors[idx].tolist()), 3)
        elif flake.bbox is not None:
            # Fallback: draw bounding box
            x, y, w, h = flake.bbox
            cv2.rectangle(image, (x, y), (x+w, y+h), tuple(colors[idx].tolist()), 3)

        # Put text on the top left corner
        cv2.putText(
            image,
            f"{(idx + 1):2}. {flake.thickness:1}L {int(flake.size * 0.3844**2):4}um2 {1- flake.false_positive_probability:.0%}",
            (10, 30 * (idx + 1)),
            cv2.QT_FONT_NORMAL,
            1,
            (255, 255, 255),
            2,
        )

        # Draw a line from the text to the center of the flake
        cv2.line(
            image,
            (370, 30 * (idx + 1) - 15),
            (int(flake.center[0]), int(flake.center[1])),
            tuple(colors[idx].tolist()),
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
