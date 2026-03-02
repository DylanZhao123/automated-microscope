import os, json
import cv2
import numpy as np

IMG_DIR = "/Users/jason/Desktop/automated microscope/images"
OUT_JSON = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/Graphene_GMM.json"
CACHE = "/Users/jason/Desktop/automated microscope/2DMatGMM-Main/GMMDetector/trained_parameters/click_cache.json"

def contrast(bgr, bg):
    bgr = bgr.astype(np.float32)
    bg  = bg.astype(np.float32)
    return (bgr - bg) / np.clip(bg, 1.0, None)

# 读取缓存（可以跨图片累积）
if os.path.exists(CACHE):
    cache = json.load(open(CACHE, "r"))
else:
    cache = {"BG": [], "1L": [], "2L": []}

# 选一张你要点的图（按文件名排序，依次点）
files = sorted([f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg",".jpeg",".png",".tif",".tiff"))])
if not files:
    raise SystemExit("No images found in " + IMG_DIR)

print("Images:")
for i,f in enumerate(files):
    print(i, f)

idx = input("Type image index to label (e.g. 0): ").strip()
if not idx.isdigit():
    raise SystemExit("Invalid index")
idx = int(idx)
if idx < 0 or idx >= len(files):
    raise SystemExit("Index out of range")

path = os.path.join(IMG_DIR, files[idx])
img = cv2.imread(path)
if img is None:
    raise SystemExit("Cannot read: " + path)

mode = None
win = f"{files[idx]} | 1=BG 2=1L 3=2L  s=save_cache  w=write_json  q=quit"
disp = img.copy()
cv2.putText(disp, win, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

colors = {"BG": (255,255,255), "1L": (255,0,255), "2L": (0,255,255)}

def on_mouse(event, x, y, flags, param):
    global disp
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    if mode is None:
        return
    bgr = img[y,x,:].tolist()
    cache[mode].append(bgr)
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
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump(cache, f, indent=2)
        print("Saved cache:", CACHE, "| counts:", {k: len(cache[k]) for k in cache})
        print("You can label another image by rerunning this script.")
        break

    if k == ord('w'):
        # 写最终 Graphene_GMM.json（需要足够样本）
        if len(cache["BG"]) < 25:
            print("Need >=25 BG clicks (across images). Current:", len(cache["BG"]))
            continue
        if len(cache["1L"]) < 20:
            print("Need >=20 1L clicks (across images). Current:", len(cache["1L"]))
            continue
        if len(cache["2L"]) < 20:
            print("Need >=20 2L clicks (across images). Current:", len(cache["2L"]))
            continue

        bg_rgb = np.median(np.array(cache["BG"], dtype=np.float32), axis=0).astype(np.uint8)

        payload = {"bg_rgb": bg_rgb.tolist(), "classes": {}, "note": "multi-image calibration BG+1L+2L"}
        for cls in ["BG","1L","2L"]:
            X = np.stack([contrast(np.array(c, dtype=np.float32), bg_rgb) for c in cache[cls]], axis=0)
            mu = X.mean(axis=0)
            cov = np.cov(X.T) + np.eye(3)*1e-4
            payload["classes"][cls] = {"mu": mu.tolist(), "cov": cov.tolist()}

        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w") as f:
            json.dump(payload, f, indent=2)

        print("Wrote:", OUT_JSON)
        print("counts:", {k: len(cache[k]) for k in cache})
        print("bg_rgb:", payload["bg_rgb"])
        break

cv2.destroyAllWindows()
