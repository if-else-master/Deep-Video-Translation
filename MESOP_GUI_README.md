# Deep Video Translation - Mesop GUI 版本

## 概要

這是原本 tkinter GUI 的 Mesop 網頁版本，提供更現代化的網頁界面，支援：

- 大型、置中、圓角的影片上傳框
- 現代化的網頁界面
- 響應式設計
- 實時進度顯示

## 新增文件說明

### 1. `mesop_gui.py`
- 主要的 Mesop GUI 界面
- 包含所有原有功能的網頁版本
- 特色：大型置中的圓角文件上傳區域

### 2. `video_processor.py`
- 完整的視頻處理邏輯類
- 從原始 `main.py` 中分離出來的處理功能
- 支援進度回調更新

### 3. `run_mesop.py`
- Mesop 應用啟動腳本
- 使用命令行方式啟動 Mesop 應用

## 安裝和使用

### 1. 安裝依賴
```bash
cd /Users/raychang/Documents/專案/Deep-Video-Translation
pip install mesop
```

### 2. 啟動應用

#### 🥇 方法一：使用WSGI啟動器 (最推薦)
```bash
source .venv/bin/activate
cd app
python start_mesop_simple.py
```

#### 🥈 方法二：使用bash腳本
```bash
./start_mesop.sh
```

#### 🥉 方法三：查看啟動說明
```bash
source .venv/bin/activate
cd app
python mesop_gui.py
# 會顯示詳細的啟動說明
```

#### 🛠️ 方法四：手動命令（如果其他方法不工作）
```bash
# 激活虛擬環境
source .venv/bin/activate

# 進入app目錄
cd app

# 導入模塊測試
python -c "import mesop_gui; print('模塊載入成功')"

# 然後查看說明
python mesop_gui.py
```

### 3. 訪問應用
在瀏覽器中打開: http://localhost:32123

**注意：** 如果32123端口被占用，Mesop會自動選擇其他端口，請查看終端輸出的實際地址。

## 主要改進

### 文件上傳區域
- **尺寸**: 600px x 200px（比原來大很多）
- **位置**: 完全置中
- **樣式**: 20px 圓角，虛線邊框
- **互動**: 支援拖拽上傳

### 界面布局
- 響應式設計，適配不同螢幕大小
- 現代化的表單樣式
- 即時進度顯示
- 清晰的狀態反饋

### 功能完整性
- 保持所有原有功能
- 智能分段分析
- 人臉檢測和語音翻譯
- 簡報OCR翻譯
- 自動剪接

## 使用方式

1. **輸入 Gemini API Key**: 在第一個欄位輸入您的 API 密鑰
2. **上傳影片**: 點擊大型上傳區域或拖拽 MP4 文件
3. **選擇語言**: 選擇語音翻譯的目標語言
4. **設定選項**: 
   - 啟用/停用簡報翻譯
   - 調整分段參數
5. **開始處理**: 點擊「開始處理」按鈕
6. **查看進度**: 實時進度條和狀態更新
7. **完成**: 處理完成後會顯示成功訊息

## 故障排除

### 🛠️ 快速診斷工具
**如果遇到任何問題，首先運行診斷工具：**
```bash
cd app
python test_mesop.py
```
這個工具會自動檢查安裝和配置問題。

### 如果 Mesop 啟動失敗：

#### 問題：`No module named mesop.__main__`
**解決方案：**
1. 確認已安裝 mesop: `pip install mesop`
2. 使用推薦的啟動方式: `python mesop_gui.py`
3. 如果仍有問題，嘗試: `python test_mesop.py`

#### 問題：端口被占用
**解決方案：**
1. 檢查端口 32123 是否被占用: `lsof -i :32123`
2. 殺死占用進程或使用其他端口
3. Mesop通常會自動選擇可用端口

#### 問題：導入錯誤
**解決方案：**
```bash
# 確保在正確目錄
cd /Users/raychang/Documents/專案/Deep-Video-Translation/app

# 檢查Python路徑
python -c "import sys; print('\\n'.join(sys.path))"

# 測試模塊導入
python -c "import mesop; print('Mesop OK')"
python -c "import video_processor; print('VideoProcessor OK')"
```

### 如果文件上傳失敗：
1. 確認文件是 MP4 格式
2. 檢查 `temp/uploads` 目錄權限: `ls -la temp/`
3. 確認文件大小不超過限制（建議<1GB）
4. 嘗試使用較小的測試文件

### 如果處理失敗：
1. 檢查 Gemini API Key 是否正確和有效
2. 確認所有依賴都已安裝: `pip install -r requirements.txt`
3. 查看終端詳細錯誤訊息
4. 檢查網絡連接（需要訪問Gemini API）
5. 確認有足夠的磁盤空間（處理過程會產生臨時文件）

### 常見錯誤和解決方案：

#### 錯誤：`ImportError: No module named 'txtvoice'`
```bash
# 確保在app目錄中且所有文件都存在
cd app
ls -la txtvoice.py xttsv.py video_processor.py
```

#### 錯誤：`cv2.error` 或人臉檢測失敗
```bash
# 重新安裝OpenCV
pip uninstall opencv-python
pip install opencv-python==4.8.1.78
```

#### 錯誤：`ffmpeg not found`
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# 下載並安裝 FFmpeg 官方版本
```

### 🆘 獲得幫助
如果上述方法都無法解決問題：
1. 運行 `python test_mesop.py` 並記錄完整輸出
2. 檢查 Python 版本: `python --version` (需要3.8+)
3. 查看完整的錯誤堆疊跟蹤
4. 確認所有依賴版本兼容

## 與原版差異

| 功能 | tkinter 版本 | Mesop 版本 |
|------|-------------|------------|
| 界面類型 | 桌面應用 | 網頁應用 |
| 文件上傳 | 小型文件對話框 | 大型拖拽區域 |
| 進度顯示 | 基本進度條 | 現代化進度指示 |
| 響應式 | 固定大小 | 自適應大小 |
| 部署 | 本地運行 | 可網頁訪問 |

## 開發說明

如果需要修改界面：
1. 編輯 `mesop_gui.py` 中的樣式函數
2. 修改 `video_processor.py` 中的處理邏輯
3. 重新啟動應用查看變更

樣式修改示例：
```python
def upload_box_style():
    return me.Style(
        width="800px",  # 調整寬度
        height="250px", # 調整高度
        border_radius="30px",  # 更大圓角
        # ... 其他樣式
    )
```
