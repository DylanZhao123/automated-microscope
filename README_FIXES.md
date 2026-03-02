# 代码修复说明

## 快速开始

### 1. 检查修改内容
```bash
git log --oneline
git show HEAD
```

### 2. 更新配置文件
编辑 `2DMatGMM-main/demo/config.py`，修改路径为你的实际路径：
```python
PARAM_FILE = "你的参数文件路径"
FLATFIELD_IMAGE = "你的flatfield图像路径"
SERIAL_PORT = "你的COM口"  # 比如 "COM3"
```

### 3. （可选）转换参数文件格式
如果你要用旧格式的final_f.json：
```bash
cd 2DMatGMM-main/demo
python convert_params.py ../../final_f.json ../../final_f_new.json
```

然后在config.py中指向新文件：
```python
PARAM_FILE = os.path.join(PROJECT_ROOT, "..", "final_f_new.json")
```

**注意**: MaterialDetector已经可以直接读取旧格式，但会有警告。建议转换为新格式以获得更好的性能。

### 4. 测试修改
运行一个简单的测试来确认修复有效：
```python
from GMMDetector import MaterialDetector
import json
import cv2

# 加载参数
with open("path/to/final_f.json") as f:
    params = json.load(f)

# 创建detector（现在支持两种格式）
detector = MaterialDetector(
    contrast_dict=params,
    size_threshold=1800,
    standard_deviation_threshold=3
)

# 测试检测
image = cv2.imread("path/to/test/image.jpg")
flakes = detector.detect_flakes(image)

# 检查属性是否存在
for flake in flakes:
    print(f"Layer: {flake.layer}")
    print(f"Confidence: {flake.confidence}")
    print(f"FP Prob: {flake.false_positive_probability}")  # 新增
    print(f"Thickness: {flake.thickness}")  # 新增
    print(f"Has mask: {flake.mask is not None}")  # 新增
```

## 主要修改点

1. **MaterialDetector 现在支持**:
   - 1L到5L的所有层
   - 两种JSON格式（自动检测）
   - 完整的Flake属性

2. **不再崩溃**:
   - 文件找不到会提示而不是崩溃
   - 串口打开失败会继续运行（电机功能禁用）
   - 图像读取失败会跳过

3. **配置集中化**:
   - 所有路径和参数在config.py
   - 修改一个地方就能更新全局

## 如果遇到问题

### 问题1: ImportError: No module named 'config'
**解决**: 确保在demo文件夹下运行，或者把demo加到Python路径。

### 问题2: 检测结果为空
**检查**:
1. final_f.json格式是否正确
2. llr_threshold是否太高（在config.py调整STD_THRESHOLD）
3. 图像是否正确裁剪

### 问题3: 串口错误
**检查**:
1. COM口是否正确
2. 设备是否连接
3. 权限是否足够

代码现在会打印清晰的错误信息，照着提示修复即可。

## 回退到原始版本

如果修改有问题，可以回退：
```bash
git log  # 找到 "Initial commit" 的哈希值
git checkout <initial-commit-hash>
```

恢复最新版本：
```bash
git checkout master
```

## 详细修改记录

参见 `CHANGES.md` 文件。
