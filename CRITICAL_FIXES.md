# 🔧 重大問題修復總結

## 發現的問題

### 1. **重複處理問題** 🔄
**問題**：段落被重複處理多次
- `01.mp4` → `01_processed.mp4` → `01_processed_processed.mp4` → `01_processed_processed_processed.mp4`
- 導致處理時間增加 3-5 倍
- 輸出檔案累積無用的 `_processed` 後綴

**原因**：
- `process_face_segments` 和 `process_slide_segments` 會處理目錄下所有 `.mp4` 檔案
- 處理後的 `_processed.mp4` 檔案也被當作新的輸入再次處理

**修復**：
```python
# 只處理原始段落文件（不含 _processed）
face_files = sorted([f for f in os.listdir(face_dir) 
                   if f.endswith('.mp4') and not '_processed' in f])

# 如果已經處理過，跳過
if os.path.exists(processed_path):
    self.log(f"  ✅ 段落 {filename} 已處理過，跳過")
    processed_segments.append(processed_path)
    continue
```

---

### 2. **EasyOCR 語言組合錯誤** ❌
**問題**：
```
ValueError: Chinese_tra is only compatible with English, try lang_list=["ch_tra","en"]
```

**原因**：
- EasyOCR 的 `ch_tra` (繁體中文) 只能與 `en` (英文) 組合
- 不能同時使用 `ch_tra`, `ja`, `en` 三種語言

**修復**：
```python
# 所有目標語言統一使用中英文識別
# 翻譯階段才轉換到目標語言
ocr_languages = ['ch_tra', 'en']
```

---

### 3. **Wav2Lip MPS 不相容** ⚠️
**問題**：
```
ValueError (in face_detection module)
```

**原因**：
- Wav2Lip 的 `face_detection` 模組不支援 MPS (Apple Silicon GPU)
- 強制使用 MPS 會導致 face detection 失敗

**修復**：
```python
# 檢測到 MPS 時仍使用 CPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
if torch.backends.mps.is_available() and device == 'cpu':
    print("⚠️  檢測到 MPS 可用，但 face_detection 模組不支援 MPS，使用 CPU")
```

---

### 4. **檔案路徑重複問題** 📁
**問題**：
- `processed_path` 在多處定義，導致混亂
- 臨時檔案路徑不一致

**修復**：
- 統一在函數開頭定義 `processed_path`
- 確保所有路徑一致使用

---

## 修復後的流程

### 人臉段落處理：
```
1. 掃描目錄，只處理 XX.mp4（不含 _processed）
2. 檢查 XX_processed.mp4 是否存在
   ├─ 存在 → 跳過，直接使用
   └─ 不存在 → 執行處理
3. 音頻翻譯 (voice + Gemini API)
4. 語音克隆 (XTTS)
5. 分析人臉幀比例
   ├─ ≥30% → 嘴形同步 (Wav2Lip CPU)
   └─ <30% → 音頻合成 (FFmpeg)
6. 輸出 XX_processed.mp4
```

### 簡報段落處理：
```
1. 掃描目錄，只處理 XX.mp4（不含 _processed）
2. 檢查 XX_processed.mp4 是否存在
   ├─ 存在 → 跳過，直接使用
   └─ 不存在 → 執行處理
3. 音頻翻譯 (voice + Gemini API)
4. 語音克隆 (XTTS)
5. OCR 翻譯 (EasyOCR ['ch_tra', 'en'] + Gemini API)
   ├─ 識別文字 (繁中/英文)
   ├─ 移除原文
   ├─ 翻譯到目標語言
   └─ 重繪翻譯文字
6. 合成音頻和視頻
7. 輸出 XX_processed.mp4
```

---

## 使用清理腳本

在重新處理之前，建議先清理舊的臨時文件：

```bash
# 執行清理腳本
./cleanup_temp.sh

# 或手動清理
rm -f temp/faceai/*_processed*.mp4
rm -f temp/pptai/*_processed*.mp4
rm -f temp/faceai/*_audio.wav
rm -f temp/pptai/*_audio.wav
```

---

## 測試步驟

1. **清理舊文件**：
```bash
./cleanup_temp.sh
```

2. **重新處理影片**：
- 上傳影片到 Web UI
- 啟用「簡報翻譯」選項
- 開始處理

3. **檢查 log 中的關鍵訊息**：
- ✅ `只處理原始段落文件` - 不會重複處理
- ✅ `段落 XX.mp4 已處理過，跳過` - 避免重複處理
- ✅ `使用 OCR 語言: ['ch_tra', 'en']` - 語言組合正確
- ✅ `使用設備進行 Wav2Lip 推理: cpu` - 避免 MPS 錯誤
- ❌ `Chinese_tra is only compatible` - 不應再出現

4. **驗證輸出**：
```bash
# 檢查處理後的段落
ls -lh temp/faceai/*_processed.mp4
ls -lh temp/pptai/*_processed.mp4

# 每個原始段落應該只有一個對應的 _processed 檔案
```

---

## 預期改進

- ✅ **處理速度**：不再重複處理，速度提升 3-5 倍
- ✅ **OCR 翻譯**：語言組合正確，OCR 正常執行
- ✅ **嘴形同步**：CPU 模式穩定運行
- ✅ **檔案管理**：每個段落只有一個 `_processed` 版本
- ✅ **輸出品質**：包含完整的翻譯、語音克隆和 OCR 效果

---

## 注意事項

1. **首次處理後的再次運行**：
   - 已處理的段落會被跳過（節省時間）
   - 如需重新處理，請先執行 `./cleanup_temp.sh`

2. **Wav2Lip 限制**：
   - 目前使用 CPU 模式（因 face_detection 不支援 MPS）
   - 處理速度較慢，但結果穩定

3. **OCR 語言支援**：
   - 識別階段：僅支援繁中和英文
   - 翻譯階段：支援多種目標語言（日文、英文、中文等）

---

## 故障排除

### 如果仍出現重複處理：
```bash
# 檢查目錄內容
ls -lh temp/faceai/
ls -lh temp/pptai/

# 手動刪除所有 _processed 文件
rm -f temp/faceai/*_processed*.mp4
rm -f temp/pptai/*_processed*.mp4
```

### 如果 OCR 失敗：
- 檢查 log 確認使用的語言組合是 `['ch_tra', 'en']`
- 確認 Gemini API Key 有效
- 檢查網路連線

### 如果嘴形同步失敗：
- 這是正常的（當人臉幀 < 30%）
- 系統會自動降級為音頻合成
- 輸出仍包含翻譯音頻，只是沒有嘴形同步
