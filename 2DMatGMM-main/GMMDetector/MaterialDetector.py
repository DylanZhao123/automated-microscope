from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import cv2

@dataclass
class Flake:
    center: Tuple[int, int]
    layer: Optional[str] = None
    confidence: float = 0.0
    area: float = 0.0
    bbox: Optional[Tuple[int,int,int,int]] = None
    contour: Optional[np.ndarray] = None

    # Additional properties for compatibility
    @property
    def false_positive_probability(self) -> float:
        """Returns 1 - confidence for backward compatibility."""
        return 1.0 - self.confidence

    @property
    def thickness(self) -> int:
        """Extract layer number from layer string (e.g., '1L' -> 1)."""
        if self.layer and self.layer.endswith('L'):
            try:
                return int(self.layer[:-1])
            except ValueError:
                return 0
        return 0

    @property
    def size(self) -> float:
        """Alias for area."""
        return self.area

    def get_mask(self, image_shape: Optional[Tuple[int, int]] = None) -> Optional[np.ndarray]:
        """
        Generate full-size mask from contour.

        Args:
            image_shape: (height, width) of the target image. If None, use bbox size.

        Returns:
            Binary mask with same size as image_shape, or bbox-sized mask if shape not provided.
        """
        if self.contour is None:
            return None

        if image_shape is not None:
            # Full-size mask for the entire image
            mask = np.zeros(image_shape, dtype=np.uint8)
            cv2.drawContours(mask, [self.contour], -1, 255, -1)
        elif self.bbox is not None:
            # Bbox-sized mask (for local operations)
            x, y, w, h = self.bbox
            mask = np.zeros((h, w), dtype=np.uint8)
            shifted_contour = self.contour.copy()
            shifted_contour[:, :, 0] -= x
            shifted_contour[:, :, 1] -= y
            cv2.drawContours(mask, [shifted_contour], -1, 255, -1)
        else:
            return None

        return mask

    @property
    def mask(self) -> Optional[np.ndarray]:
        """
        Generate bbox-sized mask for compatibility.
        For full-size mask, use get_mask(image_shape).
        """
        return self.get_mask(image_shape=None)

def _prep_gaussian(mu_list, cov_list, cov_floor: float):
    mu = np.array(mu_list, dtype=np.float32)
    cov = np.array(cov_list, dtype=np.float32)
    cov = cov + np.eye(3, dtype=np.float32) * cov_floor  # 关键：避免 cov 太尖导致“全是薄片”
    inv = np.linalg.inv(cov).astype(np.float32)
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        cov = cov + np.eye(3, dtype=np.float32) * (10 * cov_floor)
        inv = np.linalg.inv(cov).astype(np.float32)
        sign, logdet = np.linalg.slogdet(cov)
    return mu, inv, float(logdet)

def _logpdf(X: np.ndarray, mu: np.ndarray, inv_cov: np.ndarray, logdet: float) -> np.ndarray:
    D = X - mu.reshape(1,1,3)
    d2 = (
        D[:,:,0]*(inv_cov[0,0]*D[:,:,0] + inv_cov[0,1]*D[:,:,1] + inv_cov[0,2]*D[:,:,2]) +
        D[:,:,1]*(inv_cov[1,0]*D[:,:,0] + inv_cov[1,1]*D[:,:,1] + inv_cov[1,2]*D[:,:,2]) +
        D[:,:,2]*(inv_cov[2,0]*D[:,:,0] + inv_cov[2,1]*D[:,:,1] + inv_cov[2,2]*D[:,:,2])
    )
    return -0.5 * (d2 + logdet)

def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))

class MaterialDetector:
    """
    Material detector using Gaussian Mixture Models.

    Supports both old format (numbered layers) and new format (BG/1L/2L classes).
    """

    def __init__(
        self,
        contrast_dict: Optional[Dict[str, Any]] = None,
        size_threshold: int = 120,
        standard_deviation_threshold: float = 5.0,
        used_channels: str = "BGR",
        max_components: int = 60,
        supported_layers: Optional[List[str]] = None,
        **kwargs
    ):
        self.contrast_dict = contrast_dict or {}
        self.size_threshold = int(size_threshold)
        self.std_thr = float(standard_deviation_threshold)
        self.used_channels = used_channels
        self.max_components = int(max_components)

        # Supported layers (default: 1L and 2L only)
        self.supported_layers = supported_layers or ["1L", "2L"]

        # Convert std_thr to llr_threshold (higher = stricter)
        self.llr_threshold = 0.8 * self.std_thr + 1.5

        # Covariance floor to prevent numerical issues
        self.cov_floor = 5e-4

        # Parse contrast_dict - handle both formats
        self._parse_parameters()

    def _parse_parameters(self):
        """Parse parameters from contrast_dict, handling multiple formats."""
        if "classes" in self.contrast_dict:
            # New format: {"bg_rgb": [...], "classes": {"BG": {...}, "1L": {...}, ...}}
            self.bg_rgb = np.array(
                self.contrast_dict.get("bg_rgb", [160, 160, 160]),
                dtype=np.float32
            )
            classes = self.contrast_dict["classes"]

            # Prepare background
            if "BG" in classes:
                self.mu_bg, self.inv_bg, self.logdet_bg = _prep_gaussian(
                    classes["BG"]["mu"], classes["BG"]["cov"], self.cov_floor
                )
            else:
                # Default background if not provided
                self.mu_bg = np.zeros(3, dtype=np.float32)
                self.inv_bg = np.eye(3, dtype=np.float32)
                self.logdet_bg = 0.0

            # Prepare layer classes (only supported layers)
            self.layers = {}
            for layer_name in self.supported_layers:
                if layer_name in classes:
                    mu, inv_cov, logdet = _prep_gaussian(
                        classes[layer_name]["mu"],
                        classes[layer_name]["cov"],
                        self.cov_floor
                    )
                    self.layers[layer_name] = (mu, inv_cov, logdet)
                else:
                    print(f"Warning: Layer {layer_name} not found in parameter file")

        elif "1" in self.contrast_dict:
            # Old format: {"1": {"contrast": {...}, "covariance_matrix": [...]}, ...}
            # Convert to new format on the fly
            print("Warning: Using old parameter format. Consider converting to new format.")

            # Estimate background RGB (use default if not provided)
            self.bg_rgb = np.array([160, 160, 160], dtype=np.float32)

            # Create default background Gaussian
            self.mu_bg = np.zeros(3, dtype=np.float32)
            self.inv_bg = np.eye(3, dtype=np.float32) * 10.0
            self.logdet_bg = -np.log(10.0) * 3

            # Convert numbered layers to named layers (only supported layers)
            self.layers = {}
            for layer_name in self.supported_layers:
                # Extract layer number (e.g., "1L" -> "1")
                try:
                    layer_num = int(layer_name[:-1])
                    layer_key = str(layer_num)
                except (ValueError, IndexError):
                    print(f"Warning: Invalid layer name {layer_name}")
                    continue

                if layer_key in self.contrast_dict:
                    layer_data = self.contrast_dict[layer_key]
                    # Convert contrast to mu
                    contrast = layer_data.get("contrast", {})
                    mu = np.array([
                        contrast.get("r", 0.0),
                        contrast.get("g", 0.0),
                        contrast.get("b", 0.0)
                    ], dtype=np.float32)

                    cov = np.array(layer_data["covariance_matrix"], dtype=np.float32)

                    mu_prep, inv_cov, logdet = _prep_gaussian(mu, cov, self.cov_floor)
                    self.layers[layer_name] = (mu_prep, inv_cov, logdet)
                else:
                    print(f"Warning: Layer {layer_name} (key '{layer_key}') not found in parameter file")

        else:
            raise ValueError("Invalid contrast_dict format: must contain either 'classes' or numbered layers")

    def _contrast(self, img_bgr: np.ndarray) -> np.ndarray:
        bg = self.bg_rgb.reshape(1,1,3)
        img = img_bgr.astype(np.float32)
        return (img - bg) / np.clip(bg, 1.0, None)

    def detect_flakes(self, image: np.ndarray) -> List[Flake]:
        """Detect flakes in the given image."""
        if image is None or getattr(image, "size", 0) == 0:
            return []
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        H, W = image.shape[:2]
        X = self._contrast(image)

        # Compute log-likelihood for background
        ll_bg = _logpdf(X, self.mu_bg, self.inv_bg, self.logdet_bg)

        # Compute log-likelihood for all available layers
        ll_layers = {}
        for layer_name, (mu, inv_cov, logdet) in self.layers.items():
            ll_layers[layer_name] = _logpdf(X, mu, inv_cov, logdet)

        if not ll_layers:
            return []

        # Find the best layer for each pixel
        layer_names = list(ll_layers.keys())
        ll_stack = np.stack([ll_layers[name] for name in layer_names], axis=2)
        ll_max = np.max(ll_stack, axis=2)
        cls_idx = np.argmax(ll_stack, axis=2)

        # Log-likelihood ratio
        llr = ll_max - ll_bg

        # Smooth to reduce noise
        llr_blur = cv2.GaussianBlur(llr.astype(np.float32), (0, 0), 1.4)

        # Threshold to find material regions
        material_mask = (llr_blur > self.llr_threshold).astype(np.uint8)

        # Create separate masks for each layer
        layer_masks = {}
        k = np.ones((3, 3), np.uint8)
        for i, layer_name in enumerate(layer_names):
            mask = (material_mask & (cls_idx == i)).astype(np.uint8) * 255
            # Morphological operations to clean up
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
            layer_masks[layer_name] = mask

        # Extract flakes from each layer mask
        flakes: List[Flake] = []

        def extract(mask, layer_name):
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = float(cv2.contourArea(c))
                if area < self.size_threshold:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                if w < 5 or h < 5:
                    continue
                if area > 0.8 * W * H:
                    continue

                M = cv2.moments(c)
                if M.get("m00", 0) > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w // 2, y + h // 2

                roi = llr_blur[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
                med = float(np.median(roi)) if roi.size else self.llr_threshold

                # Confidence using sigmoid to avoid saturation
                conf = float(_sigmoid((med - self.llr_threshold) / 1.2))

                flakes.append(Flake(
                    center=(cx, cy),
                    layer=layer_name,
                    confidence=conf,
                    area=area,
                    bbox=(x, y, w, h),
                    contour=c
                ))

        for layer_name, mask in layer_masks.items():
            extract(mask, layer_name)

        # Sort by confidence and filter
        flakes.sort(key=lambda f: f.confidence, reverse=True)
        flakes = [f for f in flakes if f.confidence >= 0.5]

        # Keep only best flakes (remove strict one-per-layer limit)
        return flakes[: self.max_components]
