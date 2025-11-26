# 🎯 嘴形同步失敗修復方案

## 問題根源

Wav2Lip 的 `inference.py` 在逐幀處理時，如果**任何一幀**檢測不到人臉，就會立即拋出錯誤：
```
ValueError: Face not detected! Ensure the video contains a face in all the frames.
```

這在實際影片中很常見，因為：
- 👤 講者轉身或側面
- 📊 PPT 過渡動畫
- 🎬 鏡頭切換
- 💡 畫面中只有簡報內容

## 解決方案

### 1️⃣ **修改 Wav2Lip 的 face_detect() 函數**

**位置**: `app/Wav2Lip/inference.py` Line 91-106

**改動**:
```python
# ❌ 舊版：檢測不到人臉就拋出錯誤
if rect is None:
    raise ValueError('Face not detected! Ensure the video contains a face in all the frames.')

# ✅ 新版：允許部分幀沒有人臉
if rect is None:
    results.append(None)  # 標記為 None，稍後處理
    continue
```

**新增邏輯**:
- 計算人臉幀比例
- 如果 **< 50%** 幀有人臉 → 拋出錯誤（品質太差）
- 如果 **≥ 50%** 幀有人臉 → 繼續處理，跳過沒有人臉的幀

```python
valid_results = [r for r in results if r is not None]
face_ratio = len(valid_results) / len(results)
print(f"  人臉檢測: {len(valid_results)}/{len(results)} 幀 ({face_ratio*100:.1f}%)")

if face_ratio < 0.5:
    raise ValueError(f'Too few faces detected ({face_ratio*100:.1f}% < 50%)!')
```

---

### 2️⃣ **修改 datagen() 函數**

**位置**: `app/Wav2Lip/inference.py` Line 138-148

**改動**: 在處理幀之前，過濾掉 `None` 值（沒有人臉的幀）

```python
# 過濾掉 None 結果（沒有人臉的幀）
if args.box[0] == -1:
    valid_frames = [(i, f, r) for i, (f, r) in enumerate(zip(frames, face_det_results)) if r is not None]
    if len(valid_frames) == 0:
        raise ValueError('No valid frames with faces detected!')
    frame_indices, frames, face_det_results = zip(*valid_frames)
    frames = list(frames)
    face_det_results = list(face_det_results)
```

**效果**: 
- 只處理有人臉的幀
- 輸出的嘴形同步影片會自動跳過沒有人臉的幀
- 不會因為個別幀失敗而導致整個處理中斷

---

### 3️⃣ **調整 main.py 的預檢閾值**

**位置**: `app/main.py` Line 1096

**改動**: 將人臉幀比例閾值從 **30%** 提高到 **50%**

```python
# ❌ 舊版：只要 30% 幀有人臉就嘗試嘴形同步
if face_ratio < 0.3:

# ✅ 新版：需要 50% 幀有人臉才嘗試嘴形同步
if face_ratio < 0.5:
```

**原因**:
- 與 Wav2Lip 的 50% 閾值保持一致
- 減少低品質嘴形同步的嘗試
- 當人臉幀不足時，直接使用音頻合成（更快更穩定）

---

## 處理流程

### 情境 A: 人臉幀 ≥ 50%
```
1. main.py 檢測 → 人臉幀比例 75% ✅
2. 進入 Wav2Lip 處理
3. Wav2Lip face_detect → 75% 幀有人臉 ✅
4. datagen 過濾掉 25% 沒有人臉的幀
5. 只對有人臉的幀進行嘴形同步
6. 輸出嘴形同步影片 ✅
```

### 情境 B: 人臉幀 < 50% 但 ≥ 30%
```
1. main.py 檢測 → 人臉幀比例 40% ⚠️
2. 直接跳過嘴形同步
3. 使用 FFmpeg 合成翻譯音頻和原始影片
4. 輸出音頻翻譯版本（無嘴形同步）✅
```

### 情境 C: 人臉幀 < 30%
```
1. main.py 檢測 → 人臉幀比例 15% ❌
2. 直接跳過嘴形同步
3. 使用 FFmpeg 合成翻譯音頻和原始影片
4. 輸出音頻翻譯版本（無嘴形同步）✅
```

---

## 優勢

### ✅ **容錯性提升**
- 不會因為個別幀失敗而中斷整個處理
- 適應各種影片場景（講者走動、鏡頭切換、PPT 切換）

### ✅ **品質保證**
- 50% 閾值確保嘴形同步品質
- 低於閾值時自動降級為音頻合成

### ✅ **處理速度**
- 跳過沒有人臉的幀，減少處理時間
- 快速判斷是否適合嘴形同步

### ✅ **穩定性**
- 雙重檢測機制（main.py + Wav2Lip）
- 避免不必要的 Wav2Lip 調用

---

## 測試建議

### 1. **測試不同人臉比例的影片**
```bash
# 高人臉比例（應執行嘴形同步）
- 主播類影片（80-100%）
- 訪談影片（70-90%）

# 中人臉比例（應執行嘴形同步）
- 演講影片（50-70%）
- 教學影片（50-80%）

# 低人臉比例（應跳過嘴形同步）
- 簡報為主的影片（10-40%）
- 動畫影片（0-30%）
```

### 2. **檢查 Log 訊息**
```
✅ 成功情況：
  人臉檢測: 45/60 幀 (75.0%)
  ✅ 人臉幀充足，進行嘴形同步...

⚠️ 跳過情況：
  📊 人臉幀比例: 20/60 (33.3%)
  ⚠️ 段落 01.mp4 人臉幀不足 (33.3% < 50%)，跳過嘴形同步，直接合成音頻
```

### 3. **驗證輸出品質**
```bash
# 查看處理後的影片
open temp/faceai/01_processed.mp4

# 確認：
- ✅ 翻譯音頻正確
- ✅ 語音克隆自然
- ✅ 嘴形同步流暢（如有執行）
- ✅ 沒有黑屏或跳幀
```

---

## 故障排除

### 如果仍然出現 "Face not detected" 錯誤

1. **檢查 face_detect 函數是否正確修改**
```bash
grep -A 5 "if rect is None:" app/Wav2Lip/inference.py
# 應顯示: results.append(None)
```

2. **檢查 datagen 函數是否正確修改**
```bash
grep -A 3 "過濾掉 None" app/Wav2Lip/inference.py
# 應顯示過濾邏輯
```

3. **檢查閾值是否正確**
```bash
grep "face_ratio < 0\." app/main.py
grep "face_ratio < 0\." app/Wav2Lip/inference.py
# 應都顯示 0.5
```

### 如果嘴形同步品質不佳

- 調低 main.py 的閾值（例如從 0.5 → 0.6）
- 只處理人臉比例更高的段落

### 如果所有影片都跳過嘴形同步

- 調高 main.py 的閾值（例如從 0.5 → 0.4）
- 檢查 `detect_faces_in_frame` 函數是否正常運作

---

## 技術細節

### Wav2Lip 的幀處理邏輯
```python
# 原始流程
for rect, image in zip(predictions, images):
    if rect is None:
        raise ValueError(...)  # ❌ 直接中斷

# 新流程
for rect, image in zip(predictions, images):
    if rect is None:
        results.append(None)  # ✅ 標記並繼續
        continue
    # 處理有人臉的幀
```

### 過濾機制
```python
# 第一層：過濾 None 值
valid_results = [r for r in results if r is not None]

# 第二層：檢查比例
if len(valid_results) / len(results) < 0.5:
    raise ValueError(...)

# 第三層：重構結果
final_results = []
for result in results:
    if result is None:
        final_results.append(None)
    else:
        # 處理有效結果
```

---

## 總結

這次修復實現了：

1. **容錯處理** - 允許部分幀沒有人臉
2. **品質保證** - 50% 閾值確保嘴形同步效果
3. **自動降級** - 人臉不足時使用音頻合成
4. **穩定性** - 不會因個別幀失敗而中斷

現在系統可以處理各種類型的影片，從高人臉比例的訪談到低人臉比例的簡報教學都能適應！🎉
