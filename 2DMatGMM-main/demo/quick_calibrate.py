import os, json, sys
import cv2
import numpy as np

IMG = "/Users/jason/Desktop/automated microscope/images/test1.JPG"
OUT_JSON = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"

# 特征：相对背景的 RGB 对比度（Cornell思路的最小可用版）
def contrast(rgb, bg):
    rgb = rgb.astype(np.float32); bg = bg.astype(np.float32)
    return (rgb - bg) / np.clip(bg, 1.0, None)

clicks_bg = []
clicks_1l = []

img = cv2.imread(IMG)
if img is None:
    raise SystemExit(f"Cannot read {IMG}")
h,w = img.shape[:2]

# 背景用边框中位数估计（先给一个bg，之后可用你点击的bg更新）
border = np.concatenate([
    img[0:50,:,:].reshape(-1,3),
    img[h-50:h,:,:].reshape(-1,3),
    img[:,0:50,:].reshape(-1,3),
    img[:,w-50:w,:].reshape(-1,3),
], axis=0)
bg0 = np.median(border, axis=0).astype(np.uint8)

win = "click: b=background, f=thin flake (1L), s=save, q=quit"
disp = img.copy()
cv2.putText(disp, win, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

state = {"mode": None}

def on_mouse(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    rgb = img[y,x,:]
    if state["mode"] == "b":
        clicks_bg.append((x,y,rgb))
        cv2.circle(disp, (x,y), 6, (255,255,255), 2)
    elif state["mode"] == "f":
        clicks_1l.append((x,y,rgb))
        cv2.circle(disp, (x,y), 6, (255,0,255), 2)

cv2.namedWindow(win, cv2.WINDOW_NORMAL)
cv2.resizeWindow(win, 1200, 800)
cv2.setMouseCallback(win, on_mouse)

while True:
    cv2.imshow(win, disp)
    k = cv2.waitKey(20) & 0xFF
    if k == ord('q'):
        break
    if k == ord('b'):
        state["mode"] = "b"
    if k == ord('f'):
        state["mode"] = "f"
    if k == ord('s'):
        # 用你点的背景更新 bg（如果没点就用 bg0）
        if clicks_bg:
            bg = np.median(np.stack([c[2] for c in clicks_bg], axis=0), axis=0).astype(np.uint8)
        else:
            bg = bg0

        if len(clicks_1l) < 5:
            print("Need at least 5 thin-flake clicks (press f then click).")
            continue

        X = np.stack([contrast(c[2], bg) for c in clicks_1l], axis=0)  # Nx3
        mu = X.mean(axis=0)
        cov = np.cov(X.T) + np.eye(3)*1e-4

        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        payload = {
            "bg_rgb": bg.tolist(),
            "classes": {
                "1L": {
                    "mu": mu.tolist(),
                    "cov": cov.tolist()
                }
            },
            "note": "quick calibrated on your microscope images; minimal GMM for thin flakes"
        }
        with open(OUT_JSON, "w") as f:
            json.dump(payload, f, indent=2)
        print("Saved:", OUT_JSON)
        print("bg:", bg.tolist(), "1L mu:", mu.tolist())
        break

cv2.destroyAllWindows()
