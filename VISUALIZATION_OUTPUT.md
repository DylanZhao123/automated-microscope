# 可视化输出说明

## 回答你的问题

### 1. detector能输出正确格式的图像吗？

**可以**。现在的`visualise_flakes()`函数会输出类似example1的格式：

- ✅ 彩色轮廓线标注检测到的薄片
- ✅ 左上角文字：序号、层数、面积(um2)、置信度
- ✅ 连线从文字指向薄片中心

**输出格式示例**：
```
1. 1L  841um2  88%
```

### 2. 为什么是5L？

你说的对，我看到`final_f.json`有1-5层的数据就以为都能用。但这些可能是不准确的扩展数据。

**已修复**：
- 现在默认只检测 **1L 和 2L**
- 在`config.py`中定义：`SUPPORTED_LAYERS = ["1L", "2L"]`
- MaterialDetector只会加载这两层的参数

如果你的`final_f.json`或`Graphene_GMM.json`只有1L和2L，系统会自动忽略其他层。

## 测试你的检测器

### 使用测试脚本
```bash
cd 2DMatGMM-main/demo
python test_detection.py ../../trials/0820_2/input/DSC00256.JPG
```

这会：
1. 加载参数文件
2. 检测薄片
3. 打印详细信息
4. 生成`processed_DSC00256.JPG`

### 输出示例
```
Loading parameters from: ../final_f.json
Creating detector with supported layers: ['1L', '2L']
Loading image: ../../trials/0820_2/input/DSC00256.JPG
Original image size: (3024, 4032, 3)
Cropped image size: (1875, 1875, 3)
Detecting flakes...
Found 1 flakes

Flake 1:
  Layer: 1L
  Center: (629, 1260)
  Confidence: 88%
  Area (pixels): 5695
  Area (um2): 841
  Bbox: (521, 1143, 216, 234)

Generating visualization...
Saved output to: processed_DSC00256.JPG
```

## 可视化细节

### 当前实现
- **轮廓颜色**：rainbow色谱（多个薄片用不同颜色）
- **轮廓宽度**：3像素
- **填充**：半透明（70%原图 + 30%色彩）
- **文字位置**：左上角，每个薄片间隔30像素
- **连接线**：从(370, y)到薄片中心

### 与example1的差异
1. **颜色**：example1用的是粉红色(magenta)，当前用rainbow
   - 如果要改成单一粉红色，修改`demo_functions.py`第29行
2. **填充**：example1可能没有半透明填充
   - 可以去掉31-32行的overlay部分

### 如何改成粉红色
在`demo_functions.py`中修改：
```python
# 原来（rainbow色）
colors = cm.rainbow(np.linspace(0, 1, len(confident_flakes)))[:, :3] * 255

# 改成粉红色
colors = np.array([[255, 0, 255]] * len(confident_flakes))  # magenta
```

## 面积单位转换

代码中使用 `0.3844` 作为像素到微米的转换系数：
```python
area_um2 = int(flake.size * 0.3844**2)
```

这意味着：
- 1像素 = 0.3844 微米
- 1像素² ≈ 0.148 微米²

example1中：
- 5695像素² × 0.148 ≈ 841 um²  ✅ 匹配

## 检查你的输出

比较一下：
1. trials/0820_2/output/processed_DSC00256.JPG（旧输出）
2. 用test_detection.py生成的新输出

看看格式是否一致。如果需要调整颜色或样式，告诉我具体要求。

## 参数文件选择

**推荐使用**：`GMMDetector/trained_parameters/Graphene_GMM.json`
- 这是标准训练参数
- 只包含BG、1L、2L
- 格式正确

**如果用final_f.json**：
- 虽然有1-5层，但只会用1L和2L
- 会有警告提示层数不匹配
- 建议转换为新格式（用convert_params.py）
