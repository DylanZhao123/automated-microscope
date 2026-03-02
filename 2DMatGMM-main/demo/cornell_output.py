import os, sys, math
import cv2
import numpy as np

# 让 Python 找到 GMMDetector（你已经补好了 MaterialDetector）
sys.path.append("/Users/jason/Desktop/automated microscope/2DMatGMM-main")
from GMMDetector import MaterialDetector

# ====== 你要改的只有这里两行（如果以后知道标定）======
IMG_DIR = "/Users/jason/Desktop/automated microscope/images"
OUT_DIR = "/Users/jason/Desktop/automated microscope/processed_out"
UM_PER_PX = 0.50  # 默认 0.50 um/px；如果以后知道显微镜标定就改这个
# =====================================================

os.makedirs(OUT_DIR, exist_ok=True)

# 检测器：你可以把 size_threshold 调小一点抓更多小蓝片（比如 150~300）
model = MaterialDetector(size_threshold=300, standard_deviation_threshold=5)

def estimate_layer(bg_bgr, flake_bgr):
    """
    没有 Cornell 的 GMM 参数时，只能用“颜色/对比度”做近似分层。
    目标是输出像 1L/2L/3L/4L 这样的字符串（不保证科学准确，但格式对齐你朋友）。
    """
    bg = bg_bgr.astype(np.float32)
    fk = flake_bgr.astype(np.float32)
    # 简单对比度（防止除零）
    contrast = (fk - bg) / np.clip(bg, 1.0, None)  # B,G,R
    cmag = float(np.linalg.norm(contrast))

    # 用色相辅助（蓝/青通常偏薄，黄/绿通常偏厚 —— 仅经验规则）
    fk_hsv = cv2.cvtColor(fk.reshape(1,1,3).astype(np.uint8), cv2.COLOR_BGR2HSV).reshape(3)
    hue = int(fk_hsv[0])  # 0..179

    # 粗规则：你后面可以按样本调阈值
    if cmag < 0.10:
        return "1L"
    if 70 <= hue <= 110 and cmag < 0.22:  # 蓝青
        return "1L"
    if cmag < 0.18:
        return "2L"
    if cmag < 0.26:
        return "3L"
    return "4L"

def compute_background_bgr(img):
    # 用边框区域估计背景颜色（更稳）
    h, w = img.shape[:2]
    border = np.concatenate([
        img[0:50, :, :].reshape(-1,3),
        img[h-50:h, :, :].reshape(-1,3),
        img[:, 0:50, :].reshape(-1,3),
        img[:, w-50:w, :].reshape(-1,3),
    ], axis=0)
    return np.median(border, axis=0).astype(np.uint8)

def contour_from_bbox(img_gray, bbox):
    x,y,w,h = bbox
    h_img, w_img = img_gray.shape[:2]
    x0 = max(0, x-8); y0 = max(0, y-8)
    x1 = min(w_img, x+w+8); y1 = min(h_img, y+h+8)
    roi = img_gray[y0:y1, x0:x1].copy()

    # 自适应阈值 + close，尽量把 flake 填出来
    roi_blur = cv2.GaussianBlur(roi, (7,7), 0)
    thr = cv2.adaptiveThreshold(roi_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 5)
    thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8), iterations=2)

    cnts, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    # 选最大轮廓
    c = max(cnts, key=cv2.contourArea)
    c = c + np.array([[[x0, y0]]], dtype=np.int32)
    return c

def contour_mean_bgr(img, contour):
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)
    m = cv2.mean(img, mask=mask)[:3]
    return np.array(m, dtype=np.float32)

def contour_area_um2(contour):
    area_px = float(cv2.contourArea(contour))
    return area_px * (UM_PER_PX ** 2)

def contour_centroid(contour):
    M = cv2.moments(contour)
    if M.get("m00", 0) > 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy)
    x,y,w,h = cv2.boundingRect(contour)
    return (x+w//2, y+h//2)

def confidence_percent(img_gray, contour):
    # 用轮廓内部灰度标准差作为“置信度”近似（只是格式对齐）
    mask = np.zeros(img_gray.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)
    vals = img_gray[mask == 255]
    if vals.size < 50:
        return 60
    s = float(np.std(vals))
    # 映射到 60~99
    pct = int(max(60, min(99, 60 + (s / 25.0) * 39)))
    return pct

def draw_cornell_style(img, items):
    # 粉色（BGR）
    PINK = (255, 0, 255)

    # 左上角文字起点
    x_text = 20
    y_text = 35
    line_gap = 40

    for i, it in enumerate(items, start=1):
        contour = it["contour"]
        cx, cy = it["center"]
        layer = it["layer"]
        area_um2 = it["area_um2"]
        conf = it["conf"]

        # 画轮廓
        cv2.drawContours(img, [contour], -1, PINK, 3)

        # 左上角写字
        label = f"{i}. {layer}  {int(area_um2)}um2 {conf}%"
        ty = y_text + (i-1)*line_gap
        cv2.putText(img, label, (x_text, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 3, cv2.LINE_AA)

        # 从文字右侧拉一条线到 flake
        start = (x_text + 320, ty - 8)  # 大概对齐你朋友那种“从文字旁边出线”
        cv2.line(img, start, (cx, cy), PINK, 3)

    return img

# ====== 主流程 ======
image_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".tif",".tiff"))]
image_files.sort()

for fn in image_files:
    path = os.path.join(IMG_DIR, fn)
    img = cv2.imread(path)
    if img is None:
        continue

    bg = compute_background_bgr(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    flakes = model.detect_flakes(img)

    # 把 flakes 转成“轮廓 + 面积 + layer + conf”
    items = []
    for f in flakes:
        if not f.bbox:
            continue

        contour = contour_from_bbox(gray, f.bbox)
        if contour is None:
            continue

        area_um2 = contour_area_um2(contour)
        # 太小的碎屑不要（你可以调）
        if area_um2 < 50:
            continue

        fk_bgr = contour_mean_bgr(img, contour)
        layer = estimate_layer(bg, fk_bgr)
        conf = confidence_percent(gray, contour)
        center = contour_centroid(contour)

        items.append({
            "contour": contour,
            "area_um2": area_um2,
            "layer": layer,
            "conf": conf,
            "center": center,
        })

    # 按面积从大到小排序，输出更像你朋友
    items.sort(key=lambda d: d["area_um2"], reverse=True)
    # 只标注前 N 个（避免全屏都是线）
    items = items[:15]

    out = img.copy()
    out = draw_cornell_style(out, items)

    out_path = os.path.join(OUT_DIR, "processed_" + fn)
    cv2.imwrite(out_path, out)
    print("wrote:", out_path, "flakes:", len(items))

print("Done. Open:", OUT_DIR)
