"""
F5-TTS 語音克隆模組
使用 F5-TTS 進行高品質的語音克隆

使用方式:
    from f5ttsv import f5ttsv
    output_path = f5ttsv(text, speaker_audio_path, output_path, language)
"""

import os
import sys
import subprocess
import re
import numpy as np
import soundfile as sf

# 設置環境變數，解決 Mac MPS 設備兼容性問題
# 某些 PyTorch 操作在 MPS 上未實現，需要回退到 CPU
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

# 添加 F5-TTS 路徑到系統路徑
f5_tts_path = os.path.join(os.path.dirname(__file__), 'F5-TTS', 'src')
if f5_tts_path not in sys.path:
    sys.path.insert(0, f5_tts_path)


def check_audio_stream(video_path):
    """檢查視頻是否包含音頻流"""
    try:
        command = f'ffprobe -v quiet -print_format json -show_streams "{video_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            
            # 檢查是否有音頻流
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
            return len(audio_streams) > 0
        else:
            print(f"⚠️ 無法檢查音頻流: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ 檢查音頻流時發生錯誤: {e}")
        return False


def get_video_duration(video_path):
    """獲取視頻時長（秒）"""
    try:
        command = f'ffprobe -v quiet -print_format json -show_format "{video_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            return duration
        else:
            print(f"⚠️ 無法獲取視頻時長: {result.stderr}")
            return 5.0  # 預設5秒
    except Exception as e:
        print(f"⚠️ 獲取視頻時長時發生錯誤: {e}")
        return 5.0  # 預設5秒


def create_silent_audio(duration_seconds, output_audio_path):
    """創建指定長度的靜音音頻文件"""
    try:
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 創建音頻輸出目錄: {output_dir}")
        
        command = f'ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t {duration_seconds} -ar 24000 -ac 1 "{output_audio_path}"'
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        if os.path.exists(output_audio_path):
            print(f"✅ 靜音音頻創建成功: {output_audio_path} ({duration_seconds}秒)")
            return output_audio_path
        else:
            raise Exception(f"靜音音頻創建後文件不存在: {output_audio_path}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 靜音音頻創建失敗: {e}")
        print(f"❌ FFmpeg stderr: {e.stderr}")
        raise Exception(f"靜音音頻創建失敗: {e}")


def extract_audio_from_video(video_path, output_audio_path):
    """從視頻文件中提取音頻，如果沒有音頻流則創建靜音音頻"""
    try:
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 創建音頻輸出目錄: {output_dir}")
        
        # 先檢查視頻是否包含音頻流
        has_audio = check_audio_stream(video_path)
        
        if has_audio:
            # 有音頻流，正常提取 (F5-TTS 使用 24000 採樣率)
            print(f"🎵 檢測到音頻流，正在提取...")
            command = f'ffmpeg -y -i "{video_path}" -ar 24000 -ac 1 "{output_audio_path}"'
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            
            if os.path.exists(output_audio_path):
                print(f"✅ 音頻提取成功: {output_audio_path}")
                return output_audio_path
            else:
                raise Exception(f"音頻提取後文件不存在: {output_audio_path}")
        else:
            # 沒有音頻流，創建靜音音頻
            print(f"⚠️ 視頻沒有音頻流，創建靜音音頻...")
            duration = get_video_duration(video_path)
            return create_silent_audio(duration, output_audio_path)
            
    except subprocess.CalledProcessError as e:
        # 如果提取失敗，嘗試創建靜音音頻
        print(f"❌ 音頻提取失敗，嘗試創建靜音音頻: {e}")
        try:
            duration = get_video_duration(video_path)
            return create_silent_audio(duration, output_audio_path)
        except Exception as e2:
            print(f"❌ 靜音音頻創建也失敗: {e2}")
            raise Exception(f"音頻處理完全失敗: 原始錯誤={e}, 靜音創建錯誤={e2}")


def split_text(text, max_length=120):
    """將長文本分割成較小的片段（F5-TTS 支援較長文本）"""
    if len(text) <= max_length:
        return [text]
    
    # 優先按句號分割
    sentences = re.split(r'[.!?。！？]', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 如果當前句子本身就太長，按逗號分割
        if len(sentence) > max_length:
            sub_sentences = re.split(r'[,，]', sentence)
            for sub_sentence in sub_sentences:
                sub_sentence = sub_sentence.strip()
                if not sub_sentence:
                    continue
                    
                if len(current_chunk + sub_sentence) <= max_length:
                    current_chunk += sub_sentence + "，"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip("，"))
                        current_chunk = sub_sentence + "，"
                    else:
                        # 如果單個子句還是太長，強制分割
                        if len(sub_sentence) > max_length:
                            for i in range(0, len(sub_sentence), max_length):
                                chunks.append(sub_sentence[i:i+max_length])
                        else:
                            current_chunk = sub_sentence + "，"
        else:
            if len(current_chunk + sentence) <= max_length:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip("。"))
                current_chunk = sentence + "。"
    
    if current_chunk:
        chunks.append(current_chunk.rstrip("。，"))
    
    return chunks


# 全局 F5-TTS 模型實例（避免重複載入）
_f5tts_model = None


def get_f5tts_model():
    """獲取或初始化 F5-TTS 模型"""
    global _f5tts_model
    
    if _f5tts_model is None:
        try:
            from f5_tts.api import F5TTS
            print("🔄 正在初始化 F5-TTS 模型...")
            _f5tts_model = F5TTS(model="F5TTS_v1_Base")
            print("✅ F5-TTS 模型初始化完成")
        except ImportError as e:
            print(f"❌ 無法導入 F5-TTS: {e}")
            print("💡 請確保已安裝 F5-TTS: pip install f5-tts")
            raise ImportError(f"F5-TTS 模組未安裝: {e}")
        except Exception as e:
            print(f"❌ F5-TTS 模型初始化失敗: {e}")
            raise
    
    return _f5tts_model


def f5ttsv(text, speaker_audio_path, output_path="output.wav", language="日文"):
    """
    使用 F5-TTS 進行語音克隆
    
    參數:
        text: 要合成的文字
        speaker_audio_path: 說話者音頻參考（可以是視頻或音頻文件）
        output_path: 輸出音頻路徑
        language: 語言選項（日文、英文、中文等）
    
    返回:
        output_path: 輸出音頻文件路徑
    """
    print(f"🎤 F5-TTS 語音克隆開始...")
    print(f"📝 文本: {text[:100]}{'...' if len(text) > 100 else ''}")
    print(f"🔊 參考音頻: {speaker_audio_path}")
    print(f"🌐 語言: {language}")
    
    # 確保輸出目錄存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 創建語音克隆輸出目錄: {output_dir}")
    
    # 處理輸入音檔格式
    file_ext = os.path.splitext(speaker_audio_path)[1].lower()
    
    if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
        # 如果是視頻文件，提取音頻
        temp_audio_path = "temp/f5_extracted_audio.wav"
        os.makedirs("temp", exist_ok=True)
        speaker_wav = extract_audio_from_video(speaker_audio_path, temp_audio_path)
        print(f"已從視頻文件提取音頻: {speaker_wav}")
    elif file_ext in ['.mp3', '.m4a', '.aac', '.flac']:
        # 如果是其他音頻格式，轉換為 WAV (24000Hz for F5-TTS)
        temp_audio_path = "temp/f5_converted_audio.wav"
        os.makedirs("temp", exist_ok=True)
        try:
            command = f'ffmpeg -y -i "{speaker_audio_path}" -ar 24000 -ac 1 "{temp_audio_path}"'
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            speaker_wav = temp_audio_path
            print(f"已轉換音頻格式: {speaker_wav}")
        except subprocess.CalledProcessError as e:
            print(f"❌ 音頻轉換失敗: {e}")
            raise Exception(f"音頻轉換失敗: {e}")
    else:
        # 如果已經是 WAV 格式，確保採樣率正確
        temp_audio_path = "temp/f5_resampled_audio.wav"
        os.makedirs("temp", exist_ok=True)
        try:
            command = f'ffmpeg -y -i "{speaker_audio_path}" -ar 24000 -ac 1 "{temp_audio_path}"'
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            speaker_wav = temp_audio_path
        except:
            speaker_wav = speaker_audio_path
    
    # 設置語言配置（F5-TTS 支持中文和英文）
    # F5-TTS 是基於中文/英文訓練的，但可以處理多語言文本
    language_configs = {
        "日文": {"max_length": 120},
        "英文": {"max_length": 150}, 
        "中文": {"max_length": 120},
        "德文": {"max_length": 150},
        "法文": {"max_length": 150},
        "俄文": {"max_length": 130},
        "義大利文": {"max_length": 150},
        "西班牙文": {"max_length": 150}
    }
    
    lang_config = language_configs.get(language, {"max_length": 120})
    max_length = lang_config["max_length"]
    
    try:
        # 獲取 F5-TTS 模型
        f5_model = get_f5tts_model()
        
        # 檢查文本長度並分割
        if len(text) > max_length:
            print(f"文本長度 {len(text)} 超過限制 {max_length}，進行分割處理...")
            text_chunks = split_text(text, max_length)
            print(f"分割為 {len(text_chunks)} 個片段")
            
            # 分別合成每個片段
            audio_chunks = []
            sample_rate = None
            
            for i, chunk in enumerate(text_chunks):
                print(f"正在合成第 {i+1}/{len(text_chunks)} 片段: {chunk[:50]}...")
                
                wav, sr, _ = f5_model.infer(
                    ref_file=speaker_wav,
                    ref_text="",  # 讓 F5-TTS 自動識別參考文本
                    gen_text=chunk,
                    file_wave=None,  # 暫時不保存
                    seed=None,
                )
                
                audio_chunks.append(wav)
                if sample_rate is None:
                    sample_rate = sr
            
            # 合併所有音頻片段
            print("正在合併音頻片段...")
            if audio_chunks:
                combined_audio = np.concatenate(audio_chunks, axis=0)
            else:
                raise ValueError("沒有生成任何音頻片段")
        else:
            # 文本長度在限制內，直接合成
            print("🔄 正在進行語音合成...")
            combined_audio, sample_rate, _ = f5_model.infer(
                ref_file=speaker_wav,
                ref_text="",  # 讓 F5-TTS 自動識別參考文本
                gen_text=text,
                file_wave=None,  # 暫時不保存
                seed=None,
            )
        
        # 保存音頻文件
        sf.write(output_path, combined_audio, samplerate=sample_rate)
        print(f"✅ F5-TTS 語音克隆完成: {output_path}")
        
        return output_path
        
    except ImportError as e:
        print(f"❌ F5-TTS 未安裝或導入失敗: {e}")
        raise
    except Exception as e:
        print(f"❌ F5-TTS 語音合成失敗: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"F5-TTS 語音合成失敗: {e}")


if __name__ == "__main__":
    # 測試用例
    text = "這是一個測試文字，用於測試 F5-TTS 語音克隆功能。"
    speaker_path = "temp/test_speaker.wav"
    
    if os.path.exists(speaker_path):
        f5ttsv(text, speaker_path, "temp/f5_output.wav", "中文")
    else:
        print("測試音頻文件不存在，請提供有效的參考音頻")
