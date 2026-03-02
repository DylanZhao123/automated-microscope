import os, json, math
import cv2
import numpy as np

# ========= 你需要确认/可调的路径 =========
IMG_DIR = "/Users/jason/Desktop/automated microscope/images"
PARAM_JSON = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"
OUT_DIR = "/Users/jason/Desktop/automated microscope/out_vis_friend"

# ========= 可调参数：用来“只抓薄片” =========
# 像你朋友那种输出：通常希望每张图最终只留下 1 个 1L 或/和 1 个 2L
KEEP_TOPK_PER_LAYER = 1

# 过滤噪点（太小的连通域）
MIN_AREA_PX = 300         # 太小会出一堆点；你现在就像这样
# 过滤明显大厚片（黄的通常面积很大）
MAX_AREA_PX = 120000

# 过滤颜色：薄的 graphene（1L/2L）在你图里更偏青蓝/青绿，不是黄
# OpenCV HSV: H in [0,179]，蓝绿/青色大概在 55~110
HUE_MIN = 55
HUE_MAX = 110
SAT_MAX = 170             # 太饱和（很黄/很艳）的不要
VAL_MIN = 40              # 太暗的不要（灰黑脏点）

# 像素面积转 um^2：你朋友肯定有显微镜标定，这里给个可改的常数
# 如果你知道 1px 对应多少 um，把 UM_PER_PX 改掉
UM_PER_PX = 0.50


def softmax(x, axis=-1):
    x = x - np.max(x, axis=axis, keepdims=True)
    ex = np.exp(x)
    return ex / (np.sum(ex, axis=axis, keepdims=True) + 1e-12)


def mvn_logpdf(X, mu, cov):
    # X: (N,3)
    mu = np.asarray(mu, dtype=np.float64).reshape(1, -1)
    cov = np.asarray(cov, dtype=np.float64)
    d = X.shape[1]
    cov = cov + np.eye(d) * 1e-9
    inv = np.linalg.inv(cov)
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        logdet = np.log(np.maximum(np.linalg.det(cov), 1e-12))
    Xm = X - mu
    quad = np.einsum("ni,ij,nj->n", Xm, inv, Xm)
    return -0.5 * (d * np.log(2*np.pi) + logdet + quad)


class SimpleMaterialDetector:
    """
    只依赖 Graphene_GMM.json（BG/1L/2L 的 mu/cov + bg_rgb）
    """
    def __init__(self, param_json):
        self.params = json.load(open(param_json, "r"))
        self.bg_rgb = np.array(self.params["bg_rgb"], dtype=np.float64)
        self.classes = self.params["classes"]  # dict: BG/1L/2L
        self.class_names = list(self.classes.keys())

    def _features(self, img_rgb):
        # 用 log-ratio 相对 bg 做特征（跟你 quick_calibrate 打出来的 mu 量级匹配）
        img = img_rgb.astype(np.float64)
        eps = 1.0
        bg = self.bg_rgb.reshape(1,1,3)
        feat = np.log((img + eps) / (bg + eps))
        return feat.reshape(-1, 3)

    def pixel_posterior(self, img_rgb):
        X = self._features(img_rgb)
        logps = []
        for name in self.class_names:
            mu = self.classes[name]["mu"]
            cov = self.classes[name]["cov"]
            logps.append(mvn_logpdf(X, mu, cov))
        logps = np.stack(logps, axis=1)  # (N,C)
        post = softmax(logps, axis=1)
        return post.reshape(img_rgb.shape[0], img_rgb.shape[1], -1)

    def detect(self, img_bgr):
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        post = self.pixel_posterior(img_rgb)
        cls_idx = np.argmax(post, axis=2)
        conf = np.max(post, axis=2)

        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        H,S,V = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]

        results = []

        for target in ["1L","2L"]:
            if target not in self.class_names:
                continue
            k = self.class_names.index(target)

            # 初始 mask：像素被判为该类 & 置信度足够
            mask = (cls_idx == k) & (conf >= 0.55)

            # 颜色过滤：只保留青蓝/青绿那种（薄片）
            mask = mask & (H >= HUE_MIN) & (H <= HUE_MAX) & (S <= SAT_MAX) & (V >= VAL_MIN)

            mask = mask.astype(np.uint8) * 255

            # 形态学：去散点，合并裂缝
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

            # 找连通域
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            cand = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < MIN_AREA_PX or area > MAX_AREA_PX:
                    continue

                x,y,w,h = cv2.boundingRect(cnt)
                # 计算该连通域的平均 posterior 作为置信度
                comp_mask = np.zeros(mask.shape, np.uint8)
                cv2.drawContours(comp_mask, [cnt], -1, 255, -1)
                pts = comp_mask.astype(bool)
                mean_conf = float(np.mean(post[:,:,k][pts])) if np.any(pts) else 0.0

                # 评分：更偏向“面积较大且更自信”的薄片
                score = mean_conf * math.sqrt(area)

                M = cv2.moments(cnt)
                if M["m00"] > 1e-6:
                    cx = int(M["m10"]/M["m00"])
                    cy = int(M["m01"]/M["m00"])
                else:
                    cx, cy = x+w//2, y+h//2

                cand.append((score, mean_conf, area, (cx,cy), cnt))

            cand.sort(key=lambda t: t[0], reverse=True)
            cand = cand[:KEEP_TOPK_PER_LAYER]

            for score, mean_conf, area, (cx,cy), cnt in cand:
                results.append({
                    "layer": target,
                    "conf": mean_conf,
                    "area_px": float(area),
                    "center": (cx,cy),
                    "contour": cnt
                })

        # 如果 1L/2L 都有，按 conf 排序输出
        results.sort(key=lambda r: r["conf"], reverse=True)
        return results


def draw_friend_style(img_bgr, flakes):
    out = img_bgr.copy()
    h, w = out.shape[:2]
    # 画每个 flake：粉色轮廓 + 粉色引线 + 左上角文字
    base_x, base_y = 10, 28
    line_color = (255, 0, 255)  # BGR: magenta
    font = cv2.FONT_HERSHEY_SIMPLEX

    for i, f in enumerate(flakes, start=1):
        cnt = f["contour"]
        cx, cy = f["center"]
        conf = f["conf"]
        area_um2 = f["area_px"] * (UM_PER_PX**2)

        # 轮廓
        cv2.drawContours(out, [cnt], -1, line_color, 2)

        # 文字
        text = f"{i}. {f['layer']}  {area_um2:.0f}um2  {int(round(conf*100))}%"
        tx, ty = base_x, base_y + (i-1)*26
        cv2.putText(out, text, (tx, ty), font, 0.8, (255,255,255), 3, cv2.LINE_AA)
        cv2.putText(out, text, (tx, ty), font, 0.8, (0,0,0), 1, cv2.LINE_AA)

        # 引线：从文字右侧到 flake 中心
        start = (min(tx + 280, w-10), max(ty-18, 10))
        cv2.line(out, start, (cx, cy), line_color, 2)

    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    det = SimpleMaterialDetector(PARAM_JSON)

    imgs = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".tif",".tiff"))]
    imgs.sort()

    print(f"Reading images from: {IMG_DIR}")
    print(f"Found {len(imgs)} images: {imgs}")

    for name in imgs:
        path = os.path.join(IMG_DIR, name)
        img = cv2.imread(path)
        if img is None:
            print("Skip unreadable:", name)
            continue

        flakes = det.detect(img)

        print(f"\n== {name} ==")
        print(f"Detected flakes (kept): {len(flakes)}")
        for f in flakes[:20]:
            print(f"center: {f['center']} layer: {f['layer']} conf: {f['conf']:.3f}")

        out = draw_friend_style(img, flakes)
        out_path = os.path.join(OUT_DIR, f"processed_{name}")
        cv2.imwrite(out_path, out)

    print("\nDone.")
    print("Saved to:", OUT_DIR)


if __name__ == "__main__":
    main()
