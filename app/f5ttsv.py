"""
Qwen3-TTS 語音克隆模組（替代 F5-TTS）
使用 Qwen/Qwen3-TTS-12Hz-1.7B-Base 進行聲音克隆

支援語言: 中文, 英文, 日文, 韓文, 德文, 法文, 俄文, 葡萄牙文, 西班牙文, 義大利文
原始介面完全相容，main.py 無需修改。
"""

import os
import sys
import subprocess
import json
import numpy as np
import soundfile as sf

# ─── 語言對照表 (中文 UI 名稱  →  Qwen3-TTS 英文語言碼) ────────────────────
LANGUAGE_MAP = {
    "英文":    "English",
    "中文":    "Chinese",
    "日文":    "Japanese",
    "韓文":    "Korean",
    "德文":    "German",
    "法文":    "French",
    "俄文":    "Russian",
    "葡萄牙文": "Portuguese",
    "西班牙文": "Spanish",
    "義大利文": "Italian",
    "印地文":  "English",   # Qwen3-TTS 不支援，退而求其次
}


# ════════════════════════════════════════════════════════
#  通用輔助函數（ffmpeg / ffprobe，與 TTS 無關）
#  這些函數被 main.py 直接 import，介面不可改動
# ════════════════════════════════════════════════════════

def check_audio_stream(video_path):
    """使用 ffprobe 檢查影片是否包含音訊流。"""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
               "-show_streams", "-select_streams", "a", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        info = json.loads(result.stdout)
        return len(info.get("streams", [])) > 0
    except Exception:
        return False


def get_video_duration(video_path):
    """回傳影片 / 音訊的時長（秒，float）。"""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
               "-show_format", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def create_silent_audio(duration_seconds, output_audio_path, sample_rate=24000):
    """建立指定時長的靜音 WAV 檔案。"""
    out_dir = os.path.dirname(output_audio_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    cmd = (
        f'ffmpeg -y -f lavfi '
        f'-i anullsrc=channel_layout=mono:sample_rate={sample_rate} '
        f'-t {duration_seconds} "{output_audio_path}"'
    )
    subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    return output_audio_path


def extract_audio_from_video(video_path, output_audio_path, sample_rate=24000):
    """從影片提取音訊；若無音訊流則建立靜音替代。"""
    out_dir = os.path.dirname(output_audio_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    try:
        if not check_audio_stream(video_path):
            print(f"⚠️  影片無音訊流，建立靜音替代: {video_path}")
            duration = get_video_duration(video_path)
            return create_silent_audio(duration or 5.0, output_audio_path, sample_rate)
        cmd = (
            f'ffmpeg -y -i "{video_path}" -vn -ar {sample_rate} -ac 1 '
            f'-acodec pcm_s16le "{output_audio_path}"'
        )
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return output_audio_path
    except Exception as e:
        print(f"❌ 音訊提取失敗，建立靜音替代: {e}")
        try:
            duration = get_video_duration(video_path)
            return create_silent_audio(duration or 5.0, output_audio_path, sample_rate)
        except Exception as e2:
            raise Exception(f"音訊處理完全失敗: 提取錯誤={e}, 靜音建立錯誤={e2}")


# ════════════════════════════════════════════════════════
#  Qwen3-TTS 模型管理（全域單例，避免重複載入）
# ════════════════════════════════════════════════════════

_qwen3tts_model = None


def _get_device_dtype():
    """偵測最佳執行裝置與資料型態。"""
    import torch
    if torch.cuda.is_available():
        return "cuda:0", torch.bfloat16
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        # Apple Silicon MPS: bfloat16 支援不穩定，使用 float16
        return "mps", torch.float16
    return "cpu", torch.float32


def get_qwen3tts_model():
    """取得（或延遲初始化）Qwen3-TTS-Base 模型。"""
    global _qwen3tts_model
    if _qwen3tts_model is not None:
        return _qwen3tts_model

    try:
        from qwen_tts import Qwen3TTSModel
        import torch

        device, dtype = _get_device_dtype()
        print(f"🔄 初始化 Qwen3-TTS (device={device}, dtype={dtype}) …")

        kwargs = dict(device_map=device, dtype=dtype)
        # flash_attention_2 僅在 CUDA float16/bfloat16 環境啟用
        if "cuda" in str(device) and dtype in (torch.bfloat16, torch.float16):
            kwargs["attn_implementation"] = "flash_attention_2"

        _qwen3tts_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base", **kwargs
        )
        print("✅ Qwen3-TTS 模型初始化完成")
        return _qwen3tts_model

    except ImportError as e:
        print(f"❌ 無法導入 qwen-tts: {e}")
        print("💡 請安裝: pip install -U qwen-tts")
        raise
    except Exception as e:
        print(f"❌ Qwen3-TTS 模型初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        raise


# ════════════════════════════════════════════════════════
#  主要語音克隆函數（與原 f5ttsv 介面完全相同）
# ════════════════════════════════════════════════════════

def f5ttsv(text, speaker_audio_path, output_path="output.wav", language="英文"):
    """
    使用 Qwen3-TTS 進行語音克隆（介面與原 F5-TTS 模組完全相同）。

    參數:
        text              : 要合成的文字
        speaker_audio_path: 說話者參考音訊（可為影片或音訊檔案）
        output_path       : 輸出 WAV 路徑（預設 output.wav）
        language          : 語言（中文 UI 名稱，如「英文」「中文」「德文」等）

    回傳:
        output_path: 輸出音訊檔案路徑
    """
    print("🎤 Qwen3-TTS 語音克隆開始…")
    print(f"📝 文本: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"🔊 參考音訊: {speaker_audio_path}")
    print(f"🌐 語言: {language}")

    # 確保輸出目錄存在
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # 語言名稱轉換
    qwen_lang = LANGUAGE_MAP.get(language, "English")
    print(f"🌐 Qwen3-TTS 語言碼: {qwen_lang}")

    # 準備參考音訊（統一重採樣至 22050 Hz mono WAV）
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    file_ext = os.path.splitext(speaker_audio_path)[1].lower()

    if file_ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        ref_wav = os.path.join(tmp_dir, "qwen3_ref_audio.wav")
        ref_wav = extract_audio_from_video(speaker_audio_path, ref_wav, sample_rate=22050)
    else:
        ref_wav = os.path.join(tmp_dir, "qwen3_ref_resampled.wav")
        try:
            cmd = f'ffmpeg -y -i "{speaker_audio_path}" -ar 22050 -ac 1 "{ref_wav}"'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            ref_wav = speaker_audio_path  # fallback

    print(f"✅ 參考音訊就緒: {ref_wav}")

    try:
        model = get_qwen3tts_model()
        print("🔄 正在合成語音…")

        # x_vector_only_mode=True 省略 ref_text 轉錄
        # 品質略低於提供轉錄文字，但無需額外 ASR 步驟
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=qwen_lang,
            ref_audio=ref_wav,
            ref_text="",
            x_vector_only_mode=True,
        )

        sf.write(output_path, wavs[0], sr)
        print(f"✅ Qwen3-TTS 語音克隆完成: {output_path}")
        return output_path

    except ImportError:
        raise
    except Exception as e:
        print(f"❌ Qwen3-TTS 語音合成失敗: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Qwen3-TTS 語音合成失敗: {e}")


# ════════════════════════════════════════════════════════
#  快速測試入口：python f5ttsv.py --ref <audio> --text "..."
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Qwen3-TTS 語音克隆測試")
    parser.add_argument("--text", default="這是一個測試文字，用於測試 Qwen3-TTS 語音克隆功能。")
    parser.add_argument("--ref",  default="temp/test_speaker.wav", help="參考音訊路徑")
    parser.add_argument("--out",  default="temp/qwen3_output.wav",  help="輸出路徑")
    parser.add_argument("--lang", default="中文",                    help="語言（中文 UI 名稱）")
    args = parser.parse_args()

    if not os.path.exists(args.ref):
        print(f"❌ 參考音訊不存在: {args.ref}")
        print("請提供有效的參考音訊路徑後重試。")
        sys.exit(1)

    result = f5ttsv(args.text, args.ref, args.out, args.lang)
    print(f"\n🎉 輸出音訊: {result}")
