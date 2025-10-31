import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import soundfile as sf
import numpy as np
import os
import subprocess
import re

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

def create_silent_audio(duration_seconds, output_audio_path):
    """創建指定長度的靜音音頻文件"""
    try:
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 創建音頻輸出目錄: {output_dir}")
        
        command = f'ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t {duration_seconds} -ar 16000 -ac 1 "{output_audio_path}"'
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
    except Exception as e:
        print(f"❌ 靜音音頻創建過程發生錯誤: {e}")
        raise Exception(f"靜音音頻創建失敗: {e}")

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

def extract_audio_from_video(video_path, output_audio_path):
    """從視頻文件中提取音頻，如果沒有音頻流則創建靜音音頻"""
    try:
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 創建音頻輸出目錄: {output_dir}")
        
        # 先檢查視頻是否包含音頻流
        has_audio = check_audio_stream(video_path)
        
        if has_audio:
            # 有音頻流，正常提取
            print(f"🎵 檢測到音頻流，正在提取...")
            command = f'ffmpeg -y -i "{video_path}" -ar 16000 -ac 1 "{output_audio_path}"'
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
    except Exception as e:
        print(f"❌ 音頻提取過程發生錯誤: {e}")
        raise Exception(f"音頻提取失敗: {e}")

def split_text(text, max_length=80):
    """將長文本分割成較小的片段"""
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

def xttsv(text, speaker_audio_path, output_path="output.wav", language="日文"):
    config = XttsConfig()
    config.load_json("app/XTTS-v2/config.json")
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir="app/XTTS-v2", eval=True)
    device = torch.device("cpu")
    model.to(device)

    # 確保輸出目錄存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 創建語音克隆輸出目錄: {output_dir}")

    # 處理輸入音檔格式
    file_ext = os.path.splitext(speaker_audio_path)[1].lower()
    
    if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
        # 如果是視頻文件，提取音頻
        temp_audio_path = "temp/extracted_audio.wav"
        os.makedirs("temp", exist_ok=True)
        speaker_wav = extract_audio_from_video(speaker_audio_path, temp_audio_path)
        print(f"已從視頻文件提取音頻: {speaker_wav}")
    elif file_ext in ['.mp3', '.m4a', '.aac']:
        # 如果是其他音頻格式，轉換為 WAV
        temp_audio_path = "temp/converted_audio.wav"
        os.makedirs("temp", exist_ok=True)
        try:
            command = f'ffmpeg -y -i "{speaker_audio_path}" -ar 16000 -ac 1 "{temp_audio_path}"'
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            speaker_wav = temp_audio_path
            print(f"已轉換音頻格式: {speaker_wav}")
        except subprocess.CalledProcessError as e:
            print(f"❌ 音頻轉換失敗: {e}")
            print(f"❌ FFmpeg stderr: {e.stderr}")
            raise Exception(f"音頻轉換失敗: {e}")
    else:
        # 如果已經是 WAV 格式，直接使用
        speaker_wav = speaker_audio_path
    
    # 設置語言代碼和字符限制
    language_configs = {
        "日文": {"code": "ja", "max_length": 80},
        "英文": {"code": "en", "max_length": 100}, 
        "中文": {"code": "zh", "max_length": 82},
        "德文": {"code": "de", "max_length": 100},
        "法文": {"code": "fr", "max_length": 100},
        "俄文": {"code": "ru", "max_length": 90},
        "義大利文": {"code": "it", "max_length": 100},
        "西班牙文": {"code": "es", "max_length": 100}
    }
    
    lang_config = language_configs.get(language, {"code": "en", "max_length": 100})
    language_code = lang_config["code"]
    max_length = lang_config["max_length"]

    # 檢查文本長度並分割
    if len(text) > max_length:
        print(f"文本長度 {len(text)} 超過限制 {max_length}，進行分割處理...")
        text_chunks = split_text(text, max_length)
        print(f"分割為 {len(text_chunks)} 個片段")
        
        # 分別合成每個片段
        audio_chunks = []
        for i, chunk in enumerate(text_chunks):
            print(f"正在合成第 {i+1}/{len(text_chunks)} 片段: {chunk[:50]}...")
            
            outputs = model.synthesize(
                chunk,
                config,
                speaker_wav=speaker_wav,
                gpt_cond_len=3,
                language=language_code,
            )
            
            # 从字典中获取音频数据
            if isinstance(outputs, dict):
                audio = outputs.get("wav", None)
                if audio is None:
                    raise ValueError("无法在模型输出中找到音频数据")
            else:
                audio = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
            
            # 确保音频数据是正确的格式
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
            
            audio_chunks.append(audio)
        
        # 合併所有音頻片段
        print("正在合併音頻片段...")
        if audio_chunks:
            combined_audio = np.concatenate(audio_chunks, axis=0)
        else:
            raise ValueError("沒有生成任何音頻片段")
    else:
        # 文本長度在限制內，直接合成
        outputs = model.synthesize(
            text,
            config,
            speaker_wav=speaker_wav,
            gpt_cond_len=3,
            language=language_code,
        )

        # 从字典中获取音频数据
        if isinstance(outputs, dict):
            audio = outputs.get("wav", None)
            if audio is None:
                raise ValueError("无法在模型输出中找到音频数据")
        else:
            audio = outputs[0] if isinstance(outputs, (list, tuple)) else outputs
        
        # 确保音频数据是正确的格式
        if isinstance(audio, torch.Tensor):
            audio = audio.cpu().numpy()
        
        combined_audio = audio
    
    # 确保音频数据是正确的格式
    if len(combined_audio.shape) == 1:
        combined_audio = combined_audio.reshape(-1, 1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    sf.write(output_path, combined_audio, samplerate=config.audio["sample_rate"])
    print(f"已輸出克隆音訊檔 {output_path}")
    
    return output_path

if __name__ == "__main__":
    # 測試用例
    text = "It took me quite a long time to develop a voice and now that I have it I am not going to be silent."
    speaker_path = "app/XTTS-v2/samples/zh-cn-sample.wav"
    xttsv(text, speaker_path)
