# 检测输出文件夹

这个文件夹用于存储所有检测测试的输出结果。

## 自动输出位置

所有测试脚本的默认输出都会保存到这里：

### 单张图片测试
```bash
python test_detection.py "..\..\trials\0820_2\input\DSC00009.JPG"
```
输出 → `new_outputs/processed_DSC00009.JPG`

### 批量测试（预选图片）
```bash
python batch_test_selected.py
```
输出 → `new_outputs/processed_DSC00009.JPG`, `processed_DSC00011.JPG`, 等等

### 批量测试（指定数量）
```bash
python batch_test.py "..\..\trials\0820_2\input" 10
```
输出 → `new_outputs/processed_*.JPG` (前10张)

---

## 自定义输出位置

如果需要指定其他输出位置，可以作为参数传入：

```bash
python test_detection.py input.jpg custom_output.jpg
python batch_test_selected.py input_dir custom_output_dir
```

---

## 文件说明

- `processed_*.JPG` - 带紫色标注的检测结果图片
- `summary.json` - 批量测试的详细结果（只有batch测试会生成）

---

**注意**：此文件夹中的图片文件不会被git追踪（已在.gitignore中排除）
