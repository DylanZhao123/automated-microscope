import os, json
import cv2
import numpy as np

IMG = "/Users/jason/Desktop/automated microscope/images/test1.JPG"
OUT_JSON = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"

def contrast(bgr, bg):
    bgr = bgr.astype(np.float32)
    bg  = bg.astype(np.float32)
    return (bgr - bg) / np.clip(bg, 1.0, None)

img = cv2.imread(IMG)
if img is None:
    raise SystemExit("Cannot read image: " + IMG)

clicks = {"BG": [], "1L": [], "2L": []}
mode = None

win = "Press 1(BG) 2(1L) 3(2L), then click. s=save q=quit"
disp = img.copy()
cv2.putText(disp, win, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

colors = {"BG": (255,255,255), "1L": (255,0,255), "2L": (0,255,255)}

def on_mouse(event, x, y, flags, param):
    global disp
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if mode is None:
        return
    bgr = img[y,x,:]
    clicks[mode].append(bgr)
    cv2.circle(disp, (x,y), 6, colors[mode], 2)

cv2.namedWindow(win, cv2.WINDOW_NORMAL)
cv2.resizeWindow(win, 1200, 800)
cv2.setMouseCallback(win, on_mouse)

while True:
    cv2.imshow(win, disp)
    k = cv2.waitKey(20) & 0xFF
    if k == ord('q'):
        break
    if k == ord('1'):
        mode = "BG"
    if k == ord('2'):
        mode = "1L"
    if k == ord('3'):
        mode = "2L"

    if k == ord('s'):
        if len(clicks["BG"]) < 25:
            print("Need >=25 BG clicks (press 1 then click background).")
            continue
        if len(clicks["1L"]) < 20:
            print("Need >=20 1L clicks (press 2 then click thinnest flakes).")
            continue
        if len(clicks["2L"]) < 20:
            print("Need >=20 2L clicks (press 3 then click slightly thicker flakes).")
            continue

        bg_rgb = np.median(np.stack(clicks["BG"], axis=0), axis=0).astype(np.uint8)

        payload = {"bg_rgb": bg_rgb.tolist(), "classes": {}, "note": "BG+1L+2L calibration"}
        for cls in ["BG","1L","2L"]:
            X = np.stack([contrast(c, bg_rgb) for c in clicks[cls]], axis=0)
            mu = X.mean(axis=0)
            cov = np.cov(X.T) + np.eye(3)*1e-4
            payload["classes"][cls] = {"mu": mu.tolist(), "cov": cov.tolist()}

        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w") as f:
            json.dump(payload, f, indent=2)

        print("Saved:", OUT_JSON)
        print("bg_rgb:", bg_rgb.tolist())
        print("1L mu:", payload["classes"]["1L"]["mu"])
        print("2L mu:", payload["classes"]["2L"]["mu"])
        break

cv2.destroyAllWindows()
