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
    适配你朋友的调用参数：
      MaterialDetector(contrast_dict=..., size_threshold=..., standard_deviation_threshold=..., used_channels="BGR")
    我们把 standard_deviation_threshold 用作“严格度旋钮”（越大越严格、越少假阳性）。
    """

    def __init__(
        self,
        contrast_dict: Optional[Dict[str, Any]] = None,
        size_threshold: int = 120,
        standard_deviation_threshold: float = 5.0,
        used_channels: str = "BGR",
        max_components: int = 60,
        **kwargs
    ):
        self.contrast_dict = contrast_dict or {}
        self.size_threshold = int(size_threshold)
        self.std_thr = float(standard_deviation_threshold)
        self.used_channels = used_channels
        self.max_components = int(max_components)

        # 关键：把 std_thr -> llr_threshold（越大越严格）
        # 你现在 std_thr=5 还偏松，我们内部再加一点偏移
        self.llr_threshold = 0.8 * self.std_thr + 1.5   # 5 -> 5.5；7 -> 7.1

        # 关键：cov_floor 防止 1L/2L cov 太小导致“满屏1.0”
        self.cov_floor = 5e-4

        self.bg_rgb = np.array(self.contrast_dict.get("bg_rgb", [160,160,160]), dtype=np.float32)
        classes = self.contrast_dict.get("classes", {})

        self.mu_bg, self.inv_bg, self.logdet_bg = _prep_gaussian(classes["BG"]["mu"], classes["BG"]["cov"], self.cov_floor)
        self.mu_1l, self.inv_1l, self.logdet_1l = _prep_gaussian(classes["1L"]["mu"], classes["1L"]["cov"], self.cov_floor)
        self.mu_2l, self.inv_2l, self.logdet_2l = _prep_gaussian(classes["2L"]["mu"], classes["2L"]["cov"], self.cov_floor)

    def _contrast(self, img_bgr: np.ndarray) -> np.ndarray:
        bg = self.bg_rgb.reshape(1,1,3)
        img = img_bgr.astype(np.float32)
        return (img - bg) / np.clip(bg, 1.0, None)

    def detect_flakes(self, image: np.ndarray) -> List[Flake]:
        if image is None or getattr(image, "size", 0) == 0:
            return []
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)

        H, W = image.shape[:2]
        X = self._contrast(image)

        ll_bg = _logpdf(X, self.mu_bg, self.inv_bg, self.logdet_bg)
        ll_1l = _logpdf(X, self.mu_1l, self.inv_1l, self.logdet_1l)
        ll_2l = _logpdf(X, self.mu_2l, self.inv_2l, self.logdet_2l)

        ll_thin = np.maximum(ll_1l, ll_2l)
        cls_thin = np.where(ll_1l >= ll_2l, 1, 2)

        llr = ll_thin - ll_bg

        # 平滑减少散点
        llr_blur = cv2.GaussianBlur(llr.astype(np.float32), (0,0), 1.4)

        thin = (llr_blur > self.llr_threshold).astype(np.uint8)
        mask_1l = (thin & (cls_thin == 1)).astype(np.uint8) * 255
        mask_2l = (thin & (cls_thin == 2)).astype(np.uint8) * 255

        k = np.ones((3,3), np.uint8)
        mask_1l = cv2.morphologyEx(mask_1l, cv2.MORPH_OPEN, k, iterations=1)
        mask_1l = cv2.morphologyEx(mask_1l, cv2.MORPH_CLOSE, k, iterations=2)
        mask_2l = cv2.morphologyEx(mask_2l, cv2.MORPH_OPEN, k, iterations=1)
        mask_2l = cv2.morphologyEx(mask_2l, cv2.MORPH_CLOSE, k, iterations=2)

        flakes: List[Flake] = []

        def extract(mask, layer_name):
            nonlocal flakes
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                area = float(cv2.contourArea(c))
                if area < self.size_threshold:
                    continue
                x,y,w,h = cv2.boundingRect(c)
                if w < 5 or h < 5:
                    continue
                if area > 0.8 * W * H:
                    continue

                M = cv2.moments(c)
                if M.get("m00", 0) > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x+w//2, y+h//2

                roi = llr_blur[max(0,y):min(H,y+h), max(0,x):min(W,x+w)]
                med = float(np.median(roi)) if roi.size else self.llr_threshold

                # 置信度用 sigmoid，避免大量=1.0
                conf = float(_sigmoid((med - self.llr_threshold) / 1.2))

                flakes.append(Flake(
                    center=(cx,cy),
                    layer=layer_name,
                    confidence=conf,
                    area=area,
                    bbox=(x,y,w,h),
                    contour=c
                ))

        extract(mask_1l, "1L")
        extract(mask_2l, "2L")

        flakes.sort(key=lambda f: f.confidence, reverse=True)
        flakes = [f for f in flakes if f.confidence >= 0.75]
        # 每层只保留一个（最大面积优先，其次置信度）
        best = {}
        for f in flakes:
            key = f.layer or "UNK"
            if key not in best:
                best[key] = f
            else:
                b = best[key]
                if (f.area > b.area) or (f.area == b.area and f.confidence > b.confidence):
                    best[key] = f

        flakes = list(best.values())
        flakes.sort(key=lambda f: f.confidence, reverse=True)
        return flakes[: self.max_components]
