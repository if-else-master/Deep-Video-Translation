# Deep Video Translation - 專案轉移指南

本指南協助您將專案轉移到新的 Mac 電腦。

## 📋 系統需求

- **作業系統**: macOS (建議 macOS 12+)
- **Python**: 3.10.x
- **硬碟空間**: 至少 10GB (模型和依賴)
- **記憶體**: 建議 16GB+
- **FFmpeg**: 必須安裝

## 🚀 完整安裝步驟

### 1️⃣ 安裝系統依賴

```bash
# 安裝 Homebrew (如果尚未安裝)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝 FFmpeg
brew install ffmpeg

# 驗證安裝
ffmpeg -version
```

### 2️⃣ 複製專案文件

```bash
# 將整個專案資料夾複製到新 Mac
# 可以使用 AirDrop、USB、或雲端儲存

# 確認專案結構完整
cd Deep-Video-Translation
ls -la
```

### 3️⃣ 建立 Python 虛擬環境

```bash
# 使用 Python 3.10
python3.10 -m venv .venv

# 啟動虛擬環境
source .venv/bin/activate

# 升級 pip
pip install --upgrade pip
```

### 4️⃣ 安裝 Python 依賴

```bash
# 安裝所有依賴 (約需 5-15 分鐘)
pip install -r requirements.txt

# 檢查安裝狀態
python check_dependencies.py
```

### 5️⃣ 設定環境變數

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env 文件
nano .env
# 或使用 VS Code
code .env
```

填入以下資訊：
```env
# SMTP Email 配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=Deep Video Translation
```

### 6️⃣ 驗證字體文件

```bash
# 檢查字體文件是否存在
ls -lh app/*.{ttf,otf}
```

應該看到：
- `app/NotoSansCJKjp-Regular.otf` (日文字體，約 16MB)
- `app/NotoSansTC-Regular.ttf` (中文字體，約 11MB)

如果缺少，請從原 Mac 複製這些字體文件。

### 7️⃣ 測試功能

```bash
# 測試簡報翻譯功能
python test_slide_translation.py

# 測試 SMTP 郵件發送
python test_smtp.py
```

### 8️⃣ 啟動應用

```bash
# 切換到 app 目錄
cd app

# 啟動主程式
python main.py
```

應該看到：
```
* Running on http://0.0.0.0:32123
```

在瀏覽器開啟：
- 首頁: http://localhost:32123
- 應用: http://localhost:32123/app

## 📦 重要文件清單

確保以下文件/資料夾已完整複製：

### 必要文件
- ✅ `requirements.txt` - Python 依賴清單
- ✅ `.env.example` - 環境變數範本
- ✅ `app/` - 主應用程式碼
- ✅ `app/NotoSansCJKjp-Regular.otf` - 日文字體
- ✅ `app/NotoSansTC-Regular.ttf` - 中文字體
- ✅ `app/F5-TTS/` - F5-TTS 模型
- ✅ `app/Wav2Lip/` - Wav2Lip 模型
- ✅ `app/XTTS-v2/` - XTTS-v2 模型

### 選用文件
- `temp/` - 暫存檔案 (可刪除，會自動重建)
- `.venv/` - 虛擬環境 (不要複製，在新 Mac 重建)
- `__pycache__/` - Python 快取 (可刪除)

## 🔧 常見問題排除

### 問題 1: `ModuleNotFoundError: No module named 'xxx'`

**解決方案**:
```bash
# 重新安裝依賴
pip install -r requirements.txt

# 或單獨安裝缺少的模組
pip install xxx
```

### 問題 2: `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**解決方案**:
```bash
# 安裝 FFmpeg
brew install ffmpeg

# 驗證
which ffmpeg
```

### 問題 3: SMTP 郵件發送失敗

**解決方案**:
1. 確認已啟用 Gmail 兩步驟驗證
2. 前往 https://myaccount.google.com/apppasswords
3. 產生新的應用程式密碼
4. 更新 `.env` 中的 `SMTP_PASSWORD`

### 問題 4: 字體顯示亂碼

**解決方案**:
```bash
# 確認字體文件存在
ls -lh app/*.{ttf,otf}

# 如果缺少，從原 Mac 複製
# 或重新下載 Noto Fonts
```

### 問題 5: GPU 相關錯誤 (Mac M1/M2/M3)

**解決方案**:
```python
# 專案已設定 MPS fallback
# 如果仍有問題，可以在程式中強制使用 CPU：
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
```

## 📊 安裝驗證清單

完成以下檢查確保安裝成功：

- [ ] Python 3.10.x 已安裝
- [ ] FFmpeg 已安裝並可執行
- [ ] 虛擬環境已建立並啟動
- [ ] 所有 Python 依賴已安裝 (`check_dependencies.py` 通過)
- [ ] `.env` 文件已設定
- [ ] 字體文件存在於 `app/` 目錄
- [ ] 模型文件完整 (F5-TTS, Wav2Lip, XTTS-v2)
- [ ] 簡報翻譯測試通過 (`test_slide_translation.py`)
- [ ] SMTP 測試通過 (`test_smtp.py`)
- [ ] 主程式可以啟動 (`python app/main.py`)

## 🎯 效能優化建議

### Mac M1/M2/M3 (Apple Silicon)

```bash
# 安裝針對 Apple Silicon 優化的 PyTorch
pip install --upgrade torch torchvision torchaudio
```

### 記憶體管理

如果遇到記憶體不足：
- 關閉其他大型應用程式
- 減少同時處理的影片數量
- 考慮升級 RAM

### 處理速度

- GPU 加速: Mac M 系列晶片會自動使用 MPS (Metal Performance Shaders)
- CPU 處理: EasyOCR 和部分功能使用 CPU，為正常現象

## 📞 技術支援

如遇到其他問題：

1. 檢查錯誤訊息
2. 查看日誌文件
3. 確認所有依賴版本正確
4. 重啟虛擬環境和應用程式

## 🎉 完成！

專案轉移完成後，您可以：
1. 上傳影片進行翻譯
2. 使用排隊系統管理任務
3. 透過 Email 接收處理完成通知
4. 下載翻譯後的影片

祝您使用愉快！ 🚀
