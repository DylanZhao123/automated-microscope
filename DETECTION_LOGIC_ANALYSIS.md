# 检测逻辑分析：原始 vs 现在

## 一、紫色轮廓（检测到的薄片）是如何决定的

### 原始程序 (AI生成的版本)

**MaterialDetector.detect_flakes() - 原始逻辑**:

1. **计算对比度**：
   - `X = (image - bg_rgb) / bg_rgb`
   - 将图像转换为相对于背景的对比度

2. **计算log-likelihood**：
   - `ll_bg` = 背景的高斯概率
   - `ll_1l` = 1L层的高斯概率
   - `ll_2l` = 2L层的高斯概率

3. **选择最可能的层**：
   ```python
   ll_thin = np.maximum(ll_1l, ll_2l)  # 每个像素选1L或2L中较大的
   cls_thin = np.where(ll_1l >= ll_2l, 1, 2)  # 标记是1还是2
   ```

4. **计算log-likelihood ratio (LLR)**：
   ```python
   llr = ll_thin - ll_bg  # 材料 vs 背景的差异
   llr_blur = cv2.GaussianBlur(llr, (0,0), 1.4)  # 平滑
   ```

5. **阈值过滤**：
   ```python
   thin = (llr_blur > self.llr_threshold)  # llr_threshold = 0.8 * std_thr + 1.5
   ```
   - `std_thr = 3` 时，`llr_threshold = 3.9`
   - 这个阈值越高，检测越严格

6. **形态学处理**：
   ```python
   mask_1l = open(mask_1l, iterations=1)  # 去除小点
   mask_1l = close(mask_1l, iterations=2) # 填充小洞
   ```

7. **提取轮廓**：
   - 使用 `cv2.findContours()` 找到所有连续区域

8. **过滤条件**：
   - `area >= size_threshold` (1800像素)
   - `w >= 5 and h >= 5`
   - `area < 0.8 * 图像面积` (排除整图)

9. **计算置信度**：
   ```python
   roi = llr_blur[bbox区域]
   median_llr = np.median(roi)
   confidence = sigmoid((median_llr - llr_threshold) / 1.2)
   ```
   - 使用sigmoid避免置信度饱和到1.0

10. **原始的筛选逻辑**（AI写的，有问题）：
    ```python
    flakes = [f for f in flakes if f.confidence >= 0.75]  # 只保留高置信度
    # 每层只保留一个（最大面积优先）
    best = {}
    for f in flakes:
        if layer not in best or f.area > best[layer].area:
            best[layer] = f
    ```

---

### 现在的程序（修复后）

**MaterialDetector.detect_flakes() - 修复后逻辑**:

前面1-9步**完全相同**，但第10步改为：

10. **修复后的筛选逻辑**：
    ```python
    flakes.sort(key=lambda f: f.confidence, reverse=True)
    flakes = [f for f in flakes if f.confidence >= 0.5]  # 降低阈值到0.5
    return flakes[:max_components]  # 返回所有符合条件的flakes
    ```

**关键改进**：
- ✅ 置信度阈值从0.75降到0.5（更宽容）
- ✅ 不再限制每层只保留一个
- ✅ 支持1L-5L（虽然现在配置只用1L和2L）

---

## 二、左上角白色文字是如何决定的

### 原始程序

**demo_functions.py - visualise_flakes() 原始**:

```python
confident_flakes = [
    flake for flake in flakes
    if (1 - flake.false_positive_probability) > confidence_threshold
]

# 显示所有符合条件的flakes（可能多个）
for idx, flake in enumerate(confident_flakes):
    # 文字内容
    text = f"{(idx+1):2}. {flake.thickness:1}L {int(flake.size * 0.3844**2):4}um2 {1- flake.false_positive_probability:.0%}"

    # 画在左上角，每个间隔30像素
    cv2.putText(image, text, (10, 30 * (idx + 1)), ...)

    # 连线从固定位置(370, y)到中心
    cv2.line(image, (370, 30 * (idx + 1) - 15), flake.center, color, 2)
```

**决定因素**：
1. **显示哪些**: 所有 `confidence > 0.5` 的flakes
2. **文字内容**:
   - `idx + 1`: 序号
   - `flake.thickness`: 层数（从layer字符串提取，如"1L"->1）
   - `int(flake.size * 0.3844**2)`: 面积（像素²转um²）
   - `1 - flake.false_positive_probability`: 置信度百分比
3. **颜色**: rainbow色谱（每个flake不同颜色）

**问题**:
- ❌ 文字格式有额外空格（`:2`, `:1`, `:4` 的格式化）
- ❌ 显示多个flakes
- ❌ 使用rainbow色

---

### 现在的程序（修复后）

**demo_functions.py - visualise_flakes() 修复后**:

```python
confident_flakes = [
    flake for flake in flakes
    if (1 - flake.false_positive_probability) > confidence_threshold
]

# 只保留最佳的一个
if len(confident_flakes) > 0:
    best_flake = max(confident_flakes, key=lambda f: f.confidence)
    confident_flakes = [best_flake]

# 固定使用紫色
magenta = (255, 0, 255)
white = (255, 255, 255)

flake = confident_flakes[0]

# 文字格式修正
area_um2 = int(flake.size * 0.3844**2)
confidence_pct = int((1 - flake.false_positive_probability) * 100)
text = f"{1}. {flake.thickness}L {area_um2}um2 {confidence_pct}%"

# 白色文字，固定在(10, 30)
cv2.putText(image, text, (10, 30), font, 1, white, 2)

# 连线从文字末尾开始
text_width = cv2.getTextSize(text, font, 1, 2)[0][0]
line_start_x = 10 + text_width + 5
cv2.line(image, (line_start_x, 15), flake.center, magenta, 2)
```

**决定因素**：
1. **显示哪个**: **只显示confidence最高的那一个**
2. **文字内容**:
   - 固定序号 "1"
   - `flake.thickness`: 层数
   - `area_um2`: 面积（um²）
   - `confidence_pct`: 置信度（整数百分比）
3. **颜色**:
   - 轮廓 = magenta紫色 (255, 0, 255)
   - 文字 = white白色 (255, 255, 255)
   - 连线 = magenta紫色

**改进**:
- ✅ 只显示最好的一个flake
- ✅ 文字格式精确匹配example（无额外空格）
- ✅ 固定紫色+白色配色
- ✅ 连线从文字末尾开始（动态计算）

---

## 三、关键参数总结

### MaterialDetector参数

| 参数 | 原始值 | 现在值 | 说明 |
|------|--------|--------|------|
| `size_threshold` | 1800 | 1800 | 最小面积（像素²）|
| `std_thr` | 3 | 3 | 标准差阈值 |
| `llr_threshold` | 3.9 | 3.9 | log-likelihood ratio阈值 |
| `confidence_min` | 0.75 | 0.5 | 最低置信度 |
| `max_components` | 60 | 60 | 最多返回数量 |
| `supported_layers` | ["1L", "2L"] | ["1L", "2L"] | 支持的层数 |

### visualise_flakes参数

| 参数 | 原始 | 现在 | 说明 |
|------|------|------|------|
| 显示数量 | 所有符合的 | 只显示最好的1个 | 只要最高confidence |
| 轮廓颜色 | rainbow多色 | magenta (255,0,255) | 固定紫色 |
| 文字颜色 | 白色 | 白色 | 保持 |
| 连线起点 | 固定x=370 | 文字末尾+5px | 动态计算 |
| 文字格式 | 有额外空格 | 精确格式 | "1. 2L 304um2 84%" |

---

## 四、置信度计算详解

**核心公式**:
```python
roi_llr = llr_blur[bbox区域]
median_llr = np.median(roi_llr)
confidence = sigmoid((median_llr - llr_threshold) / 1.2)
```

其中sigmoid函数：
```python
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))
```

**含义**:
- `llr_threshold = 3.9` 是"及格线"
- `median_llr` 是该flake区域的中位数llr值
- 差值越大，薄片越明显
- 除以1.2是为了调整sigmoid的陡度
- 最终得到0-1之间的置信度

**示例**:
- `median_llr = 3.9` → `confidence ≈ 50%` (刚好在阈值上)
- `median_llr = 5.0` → `confidence ≈ 73%` (明显高于背景)
- `median_llr = 6.2` → `confidence ≈ 85%` (非常清晰)
- `median_llr = 8.0` → `confidence ≈ 98%` (极高置信度)

---

## 五、总结

### 原始程序的问题
1. ❌ 显示多个flakes，与output不符
2. ❌ 使用rainbow色，应该用magenta
3. ❌ 置信度阈值0.75太高，漏检
4. ❌ 文字格式有多余空格
5. ❌ 连线位置固定，不够灵活

### 现在程序的改进
1. ✅ 只显示confidence最高的一个
2. ✅ 固定magenta紫色轮廓
3. ✅ 置信度阈值降到0.5
4. ✅ 文字格式精确匹配
5. ✅ 连线从文字末尾动态计算

### 核心检测逻辑保持不变
- GMM模型参数（mu, cov）
- LLR计算方法
- 形态学处理
- 轮廓提取算法
- 置信度计算公式

**只修改了可视化和筛选策略，检测核心算法完全保留。**
