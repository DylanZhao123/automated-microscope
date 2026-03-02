import os, json, sys, glob
import cv2
import numpy as np

# ---- 可调参数（先用这套）----
IMAGES_DIR = "/Users/jason/Desktop/automated microscope/images"
OUT_DIR    = "/Users/jason/Desktop/automated microscope/out_vis_friend"
PARAM_PATH = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"

# 只要 1 个结果（最像薄片的）
TOPK_PER_IMAGE = 1

# 过滤黄/厚片：在 centroid 附近取 patch，看 HSV
PATCH = 31  # 取中心 31x31
# 薄片一般偏蓝/青：Hue 大概 70~170（OpenCV Hue: 0~179）
H_MIN, H_MAX = 70, 170
# 黄色/厚片 Saturation 往往更高，给个上限（可调）
S_MAX = 160
# 亮度太低/太高也可能是噪声（可调）
V_MIN, V_MAX = 40, 240

# 置信度阈值（可调）
CONF_MIN = 0.55
# 面积阈值（如果你的 flake 很小可以再降）
AREA_MIN_UM2 = 50

# 画图样式
MAGENTA = (255, 0, 255)

# ---- 适配你现有工程的 import ----
# demo 目录在 sys.path
sys.path.insert(0, os.path.abspath("."))  
# repo 根目录
sys.path.insert(0, os.path.abspath("..")) 

from GMMDetector import MaterialDetector


def _get(obj, key, default=None):
    # flake 可能是 dict，也可能是 object
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _centroid_from_flake(f):
    c = _get(f, "center", None)
    if c is not None:
        return int(c[0]), int(c[1])
    x = _get(f, "x", None); y = _get(f, "y", None)
    if x is not None and y is not None:
        return int(x), int(y)
    cen = _get(f, "centroid", None)
    if cen is not None:
        return int(cen[0]), int(cen[1])
    # bbox fallback
    bb = _get(f, "bbox", None)
    if bb is not None:
        x,y,w,h = bb
        return int(x+w/2), int(y+h/2)
    return None

def _area_um2(f):
    a = _get(f, "area_um2", None)
    if a is not None:
        return float(a)
    a = _get(f, "area", None)
    if a is not None:
        return float(a)
    # bbox fallback（没标定就只能像素面积）
    bb = _get(f, "bbox", None)
    if bb is not None:
        x,y,w,h = bb
        return float(w*h)
    return 0.0

def _conf(f):
    c = _get(f, "conf", None)
    if c is None:
        c = _get(f, "confidence", None)
    if c is None:
        return 1.0
    return float(c)

def _layer(f):
    return _get(f, "layer", None)

def _contour(f):
    # 可能是 contour / cnt / mask
    cnt = _get(f, "contour", None)
    if cnt is None:
        cnt = _get(f, "cnt", None)
    if cnt is not None:
        cnt = np.array(cnt).astype(np.int32)
        if cnt.ndim == 2:
            cnt = cnt.reshape((-1,1,2))
        return cnt
    mask = _get(f, "mask", None)
    if mask is not None:
        mask = np.array(mask).astype(np.uint8)
        if mask.ndim == 2:
            cs,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cs:
                return max(cs, key=cv2.contourArea)
    # bbox fallback
    bb = _get(f, "bbox", None)
    if bb is not None:
        x,y,w,h = map(int, bb)
        return np.array([[[x,y]],[[x+w,y]],[[x+w,y+h]],[[x,y+h]]], dtype=np.int32)
    return None

def _thin_color_pass(img_bgr, cx, cy):
    h, w = img_bgr.shape[:2]
    r = PATCH//2
    x0, x1 = max(0, cx-r), min(w, cx+r+1)
    y0, y1 = max(0, cy-r), min(h, cy+r+1)
    patch = img_bgr[y0:y1, x0:x1]
    if patch.size == 0:
        return False
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    H = hsv[...,0].mean()
    S = hsv[...,1].mean()
    V = hsv[...,2].mean()
    return (H_MIN <= H <= H_MAX) and (S <= S_MAX) and (V_MIN <= V <= V_MAX)

def pick_best_thinflake(img_bgr, flakes):
    candidates = []
    for f in flakes:
        c = _centroid_from_flake(f)
        if c is None:
            continue
        cx, cy = c
        conf = _conf(f)
        area = _area_um2(f)
        layer = _layer(f)

        if layer not in ("1L", "2L"):
            continue
        if conf < CONF_MIN:
            continue
        if area < AREA_MIN_UM2:
            continue
        if not _thin_color_pass(img_bgr, cx, cy):
            continue

        # score：优先 conf，其次面积
        score = conf*1000.0 + min(area, 1e6)*0.001
        candidates.append((score, f))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in candidates[:TOPK_PER_IMAGE]]

def draw_friend_style(img_bgr, flake, idx=1):
    out = img_bgr.copy()
    cx, cy = _centroid_from_flake(flake)
    cnt = _contour(flake)
    conf = _conf(flake)
    area = _area_um2(flake)
    layer = _layer(flake)

    if cnt is not None:
        cv2.drawContours(out, [cnt], -1, MAGENTA, 3)

    # 引线：从左上角文字位置到 flake
    text = f"{idx}. {layer}  {int(round(area))}um2  {int(round(conf*100))}%"
    org = (15, 35)
    cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 3, cv2.LINE_AA)
    cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, 1.0, MAGENTA, 1, cv2.LINE_AA)

    # 线连到 flake
    cv2.line(out, (org[0]+5, org[1]+5), (cx, cy), MAGENTA, 3)

    return out

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    contrast_dict = json.load(open(PARAM_PATH, "r"))
    model = MaterialDetector(
        contrast_dict=contrast_dict,
        size_threshold=500,               # 你原来用的
        standard_deviation_threshold=5,   # 你原来用的
        used_channels="BGR",
    )

    exts = ("*.JPG","*.JPEG","*.PNG","*.jpg","*.jpeg","*.png")
    paths = []
    for e in exts:
        paths += glob.glob(os.path.join(IMAGES_DIR, e))
    paths = sorted(paths)

    print(f"Reading images from: {IMAGES_DIR}")
    print(f"Found {len(paths)} images: {[os.path.basename(p) for p in paths]}")

    for p in paths:
        name = os.path.basename(p)
        img = cv2.imread(p)
        if img is None:
            print(f"Skip unreadable: {name}")
            continue

        flakes = model.detect_flakes(img)
        best = pick_best_thinflake(img, flakes)

        print(f"\n== {name} ==")
        print(f"Detected flakes: {len(flakes)}  | best(thin): {len(best)}")
        if not best:
            continue

        # 只画第一个
        out = draw_friend_style(img, best[0], idx=1)
        out_path = os.path.join(OUT_DIR, f"processed_{name}")
        cv2.imwrite(out_path, out)
        c = _centroid_from_flake(best[0])
        print(f"picked center: {c} layer: {_layer(best[0])} conf: {_conf(best[0])}")

    print(f"\nDone. Outputs in: {OUT_DIR}")

if __name__ == "__main__":
    main()
