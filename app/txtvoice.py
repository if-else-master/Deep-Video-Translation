"""
語音識別和翻譯模組
使用本地 Whisper 進行語音識別，Ollama (llama4) 進行翻譯
"""

import os
import subprocess
import json
import threading
import time
import whisper
import ollama

# 全域 Whisper 模型快取，避免重複載入
_whisper_model = None

def get_whisper_model():
    """取得或載入 Whisper 模型（快取以提升效能）"""
    global _whisper_model
    if _whisper_model is None:
        print("🔄 正在載入 Whisper 模型（base）...")
        _whisper_model = whisper.load_model("base")
        print("✅ Whisper 模型載入完成")
    return _whisper_model

def check_if_file_has_audio(file_path):
    """檢查文件是否包含音頻內容"""
    try:
        command = f'ffprobe -v quiet -print_format json -show_streams "{file_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            
            # 檢查是否有音頻流
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
            has_audio_stream = len(audio_streams) > 0
            
            # 如果有音頻流，進一步檢查是否有實際音頻內容
            if has_audio_stream:
                # 檢查音頻流的時長
                for stream in audio_streams:
                    duration = stream.get('duration')
                    if duration and float(duration) > 0.1:  # 至少0.1秒的音頻
                        return True
            
            return False
        else:
            print(f"⚠️ 無法檢查文件音頻內容: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ 檢查文件音頻內容時發生錯誤: {e}")
        return False


def extract_audio_to_wav(video_path, output_path):
    """從視頻文件提取音頻為 WAV 格式"""
    try:
        command = f'ffmpeg -y -i "{video_path}" -ar 16000 -ac 1 -c:a pcm_s16le "{output_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        else:
            print(f"⚠️ 音頻提取失敗: {result.stderr}")
            return None
    except Exception as e:
        print(f"⚠️ 音頻提取錯誤: {e}")
        return None


def translate_with_ollama(text, target_language="英文"):
    """使用 Ollama llama4 翻譯文字"""
    language_map = {
        "英文": "English",
        "中文": "Chinese (Traditional)",
        "德文": "German",
        "法文": "French",
        "印地文": "Hindi",
        "韓文": "Korean",
        "俄文": "Russian",
        "義大利文": "Italian",
        "西班牙文": "Spanish",
        "English": "English",
        "Chinese": "Chinese (Traditional)",
        "German": "German",
        "French": "French",
        "Russian": "Russian",
        "Italian": "Italian",
        "Spanish": "Spanish",
        "Japanese": "Japanese",
        "日文": "Japanese",
    }

    target_lang_en = language_map.get(target_language, "English")
    prompt = (
        f"Translate the following text to {target_lang_en}. "
        f"Output ONLY the translated text, no explanations, no prefixes.\n\nText: {text}"
    )

    print(f"🤖 [Ollama llama4] 正在翻譯至 {target_lang_en}，請稍候（llama4 模型較大，需要數十秒）...")

    # 背景進度指示器
    _stop_spinner = threading.Event()
    def _spinner():
        dots = 0
        while not _stop_spinner.is_set():
            time.sleep(10)
            if not _stop_spinner.is_set():
                dots += 1
                print(f"   ⏳ Ollama 思考中... ({dots * 10}s)")
    spinner_thread = threading.Thread(target=_spinner, daemon=True)
    spinner_thread.start()

    try:
        client = ollama.Client(timeout=300)  # 5 分鐘超時
        response = client.chat(
            model='llama4:latest',
            messages=[{'role': 'user', 'content': prompt}],
        )
        result = response.message.content.strip()
        for prefix in ["Translation:", "Here is the translation:", "Here's the translation:", "翻譯："]:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
        print(f"   ✅ Ollama 翻譯完成")
        return result
    except Exception as e:
        print(f"❌ Ollama 翻譯失敗: {e}")
        return text
    finally:
        _stop_spinner.set()


def voice(voice_file, target_language="英文"):
    """
    語音識別並翻譯函數（本地 Whisper + Ollama llama4）

    參數:
        voice_file: 音頻/視頻文件路徑
        target_language: 目標語言（中文或英文名稱）

    回傳:
        翻譯後的文字，若無音頻則回傳空字串
    """
    if not os.path.exists(voice_file):
        raise Exception(f"音頻文件不存在: {voice_file}")

    has_audio = check_if_file_has_audio(voice_file)
    if not has_audio:
        print(f"⚠️ 文件 {voice_file} 沒有音頻內容或音頻時長太短")
        return ""

    temp_audio_path = "temp/whisper_temp_audio.wav"
    os.makedirs("temp", exist_ok=True)
    audio_path = extract_audio_to_wav(voice_file, temp_audio_path)
    if not audio_path:
        raise Exception("無法提取音頻文件")

    try:
        # 步驟 1：本地 Whisper 語音識別
        print(f"🎵 正在使用本地 Whisper 進行語音識別...")
        model = get_whisper_model()
        result = model.transcribe(audio_path)
        transcript = result.get("text", "").strip()

        print(f"📝 語音識別結果: {transcript[:100]}{'...' if len(transcript) > 100 else ''}")

        if not transcript:
            print("⚠️ Whisper 沒有識別到任何文字")
            return ""

        # 步驟 2：Ollama llama4 翻譯
        print(f"🔄 正在使用 Ollama llama4 翻譯至 {target_language}...")
        translated = translate_with_ollama(transcript, target_language)
        print(f"✅ 翻譯完成: {translated[:100]}{'...' if len(translated) > 100 else ''}")
        return translated

    except Exception as e:
        print(f"❌ 語音識別/翻譯失敗: {e}")
        raise Exception(f"語音識別和翻譯失敗: {e}")
    finally:
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass
