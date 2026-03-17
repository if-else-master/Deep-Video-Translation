import whisper
import os

# 設定影片路徑
VIDEO_PATH = "test2_translated_2025-10-27T06-30-55.mp4"

# 載入 Whisper 模型（可選：tiny, base, small, medium, large）
# 小模型速度快，大模型準確度高
model = whisper.load_model("small")

# 轉錄 mp4
print("🎧 正在轉錄影片音訊中...")
result = model.transcribe(VIDEO_PATH, verbose=True)

# 儲存完整逐字稿
output_txt = "transcript.txt"
with open(output_txt, "w", encoding="utf-8") as f:
    for segment in result["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        f.write(f"[{start:.2f} → {end:.2f}] {text}\n")

print(f"✅ 逐字稿已輸出至：{output_txt}")
