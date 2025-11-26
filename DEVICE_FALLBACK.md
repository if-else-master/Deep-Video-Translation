# 🔄 智能設備自動降級機制

## 問題背景

在 Apple Silicon Mac 上，PyTorch 支援三種運算設備：
- **CUDA** - NVIDIA GPU（Mac 上不可用）
- **MPS** (Metal Performance Shaders) - Apple Silicon GPU
- **CPU** - 中央處理器

但是 Wav2Lip 的 `face_detection` 模組有設備限制：
```python
# face_detection/detection/core.py
if 'cpu' not in device and 'cuda' not in device:
    raise ValueError  # ❌ 不接受 'mps'
```

這導致即使 MPS 可用，也無法使用，必須手動指定 CPU。

---

## 解決方案：智能設備選擇

### 實現邏輯

```python
def get_device_with_fallback():
    """智能選擇設備，自動處理不支援的設備類型"""
    
    # 1️⃣ 優先：CUDA（最快）
    if torch.cuda.is_available():
        return 'cuda'
    
    # 2️⃣ 次選：MPS（Apple Silicon GPU）
    if torch.backends.mps.is_available():
        try:
            # 測試 face_detection 是否支援 MPS
            test_detector = FaceAlignment(LandmarksType._2D, device='mps')
            del test_detector
            print("✅ face_detection 模組支援 MPS，使用 MPS 加速")
            return 'mps'
        except (ValueError, RuntimeError) as e:
            # MPS 不支援，自動降級
            print(f"⚠️  MPS 可用但 face_detection 模組不支援")
            print("   自動降級使用 CPU")
            return 'cpu'
    
    # 3️⃣ 保底：CPU（最慢但最穩定）
    return 'cpu'
```

---

## 自動降級流程

### 情境 A：CUDA 可用（Windows/Linux with NVIDIA GPU）
```
1. 檢測到 CUDA ✅
2. 使用 CUDA 設備
3. 輸出: 🖥️ Wav2Lip 推理設備: CUDA
```

### 情境 B：MPS 可用且支援（未來版本的 face_detection）
```
1. CUDA 不可用 ❌
2. 檢測到 MPS ✅
3. 測試 face_detection 支援 MPS ✅
4. 使用 MPS 設備
5. 輸出: ✅ face_detection 模組支援 MPS，使用 MPS 加速
        🖥️ Wav2Lip 推理設備: MPS
```

### 情境 C：MPS 可用但不支援（當前版本）
```
1. CUDA 不可用 ❌
2. 檢測到 MPS ✅
3. 測試 face_detection 支援 MPS ❌
   → ValueError: Expected values for device are: {cpu, cuda}
4. 捕捉錯誤，自動降級到 CPU ✅
5. 輸出: ⚠️  MPS 可用但 face_detection 模組不支援 (錯誤: ValueError)
        自動降級使用 CPU
        🖥️ Wav2Lip 推理設備: CPU
```

### 情境 D：只有 CPU（舊款 Mac 或其他設備）
```
1. CUDA 不可用 ❌
2. MPS 不可用 ❌
3. 使用 CPU 設備
4. 輸出: 🖥️ Wav2Lip 推理設備: CPU
```

---

## 優勢

### ✅ **自動化**
- 不需要手動檢測和配置設備
- 代碼在不同硬件上都能正常運行

### ✅ **容錯性**
- 遇到不支援的設備時自動降級
- 不會因為設備問題導致程式崩潰

### ✅ **未來兼容**
- 當 face_detection 更新支援 MPS 時，自動啟用
- 不需要修改代碼

### ✅ **清晰的反饋**
- 明確告知使用的設備
- 降級時顯示原因

---

## 測試方法

### 1. 測試自動降級（Apple Silicon Mac）
```bash
# 在 macOS 上運行
python app/Wav2Lip/inference.py

# 預期輸出：
⚠️  MPS 可用但 face_detection 模組不支援 (錯誤: ValueError)
   自動降級使用 CPU
🖥️  Wav2Lip 推理設備: CPU
```

### 2. 測試 CUDA 優先（有 NVIDIA GPU 的系統）
```bash
# 在有 NVIDIA GPU 的系統上運行
python app/Wav2Lip/inference.py

# 預期輸出：
🖥️  Wav2Lip 推理設備: CUDA
```

### 3. 測試純 CPU（無 GPU）
```bash
# 在沒有 GPU 的系統上運行
python app/Wav2Lip/inference.py

# 預期輸出：
🖥️  Wav2Lip 推理設備: CPU
```

---

## 技術細節

### 設備優先級
```
CUDA > MPS > CPU
```

### 為什麼是這個順序？
1. **CUDA** - 專業 GPU 運算，Wav2Lip 原生支援，最快
2. **MPS** - Apple Silicon GPU，比 CPU 快，但相容性未知
3. **CPU** - 最慢但最穩定，所有模組都支援

### 測試方法
```python
# 創建一個臨時的 face_detection 實例
test_detector = FaceAlignment(LandmarksType._2D, device='mps')

# 如果成功 → MPS 支援 ✅
# 如果拋出 ValueError/RuntimeError → MPS 不支援 ❌
```

### 清理資源
```python
del test_detector  # 立即釋放測試用的檢測器
```

---

## 與其他模組的整合

### main.py 中的使用
```python
# main.py 不需要修改
# inference.py 會自動處理設備選擇
from app.Wav2Lip.inference import run_inference

run_inference(input_video, audio, output_video)
# ✅ 自動使用最佳可用設備
```

### 其他 PyTorch 模型的應用
這個模式可以應用到其他 PyTorch 模型：
```python
def get_device_for_model(model_class, model_args):
    """通用的設備選擇函數"""
    for device in ['cuda', 'mps', 'cpu']:
        try:
            test_model = model_class(**model_args, device=device)
            del test_model
            return device
        except Exception:
            continue
    return 'cpu'
```

---

## 效能對比

### 理論效能（嘴形同步 1 分鐘影片）
- **CUDA (RTX 3080)** - ~30 秒
- **MPS (M1 Pro)** - ~60 秒（如果支援）
- **CPU (M1 Pro)** - ~180 秒（當前情況）

### 實際效果
由於 face_detection 不支援 MPS，目前在 Apple Silicon 上：
- 使用 CPU 處理
- 比原生 MPS 慢約 3 倍
- 但穩定性最佳

---

## 故障排除

### 如果總是使用 CPU
```bash
# 檢查 PyTorch MPS 支援
python3 -c "import torch; print(f'MPS 可用: {torch.backends.mps.is_available()}')"

# 檢查 CUDA 支援
python3 -c "import torch; print(f'CUDA 可用: {torch.cuda.is_available()}')"
```

### 如果想強制使用特定設備
```python
# 在 inference.py 中修改
device = 'cpu'  # 強制使用 CPU
# 或
device = 'cuda'  # 強制使用 CUDA
```

### 如果 MPS 測試卡住
- 可能是 face_detection 初始化問題
- 添加超時機制：
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5 秒超時
try:
    test_detector = FaceAlignment(...)
except TimeoutError:
    return 'cpu'
finally:
    signal.alarm(0)
```

---

## 總結

智能設備選擇機制實現了：

1. **自動檢測** - 嘗試使用最快的可用設備
2. **自動降級** - 遇到不支援時切換到 CPU
3. **清晰反饋** - 告知用戶實際使用的設備
4. **未來兼容** - 當模組更新時自動啟用更快的設備

現在您不需要手動配置設備，系統會自動選擇最佳方案！🎉
