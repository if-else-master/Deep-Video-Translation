# Wav2Lip 唇形合成工具

這是一個方便使用 Wav2Lip 進行視頻唇形同步的簡易工具。

## 準備工作

1. 確保已安裝 Docker 
2. 構建 Docker 映像:
   ```bash
   docker build -t wav2lip-cpu -f Dockerfile.cpu .
   ```
3. 下載預訓練模型並放置在正確位置:
   ```bash
   mkdir -p app/Wav2Lip/checkpoints
   wget -O app/Wav2Lip/checkpoints/wav2lip.pth "https://github.com/Rudrabha/Wav2Lip/raw/master/checkpoints/wav2lip.pth"
   ```

## 使用方法

使用 Python 腳本運行 Wav2Lip:

```bash
python app/wav2lip_interface.py --video 你的視頻.mp4 --audio 你的音頻.wav
```

### 參數說明

- `--video`: 包含人臉的視頻文件路徑 (必需)
- `--audio`: 音頻文件路徑 (必需)
- `--output`: 輸出視頻的路徑 (默認: app/Wav2Lip/results/output.mp4)
- `--resize_factor`: 調整分辨率的因子，更高數值 = 更低分辨率 (默認: 2)
- `--face_det_batch_size`: 人臉檢測的批次大小 (默認: 4)
- `--wav2lip_batch_size`: Wav2Lip模型的批次大小 (默認: 32)
- `--nosmooth`: 停用人臉檢測平滑化

### 範例

```bash
python app/wav2lip_interface.py --video app/Wav2Lip/examples/input.mp4 --audio app/Wav2Lip/examples/input.wav --output app/Wav2Lip/results/my_result.mp4 --resize_factor 1
```

## 疑難排解

1. 如果遇到內存錯誤 (code 137)，請嘗試:
   - 增加 `--resize_factor` 值 (2, 3 或 4)
   - 減小 `--face_det_batch_size` 和 `--wav2lip_batch_size` 的值

2. 如果在處理過程中找不到人臉，請確保:
   - 視頻中有清晰可見的人臉
   - 嘗試不同的視頻裁剪或調整

3. 模型文件問題:
   - 確保 wav2lip.pth 文件已下載並放置在 app/Wav2Lip/checkpoints/ 目錄中

## 注意事項

- 處理時間取決於視頻長度和分辨率
- 較低的分辨率 (較高的 resize_factor) 會加快處理速度但可能降低質量
- 對於最佳效果，請使用前向拍攝的人臉視頻和清晰的音頻 