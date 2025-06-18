import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import soundfile as sf
import numpy as np
import os
import subprocess

def extract_audio_from_video(video_path, output_audio_path):
    """從視頻文件中提取音頻"""
    try:
        command = f'ffmpeg -y -i "{video_path}" -ar 16000 -ac 1 "{output_audio_path}"'
        subprocess.run(command, shell=True, check=True, capture_output=True)
        return output_audio_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"音頻提取失敗: {e}")

def xttsv(text, speaker_audio_path, output_path="output.wav", language="日文"):
    config = XttsConfig()
    config.load_json("app/XTTS-v2/config.json")
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir="app/XTTS-v2", eval=True)
    device = torch.device("cpu")
    model.to(device)

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
            subprocess.run(command, shell=True, check=True, capture_output=True)
            speaker_wav = temp_audio_path
            print(f"已轉換音頻格式: {speaker_wav}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"音頻轉換失敗: {e}")
    else:
        # 如果已經是 WAV 格式，直接使用
        speaker_wav = speaker_audio_path
    
    # 設置語言代碼
    language_codes = {
        "日文": "ja",
        "英文": "en", 
        "中文": "zh"
    }
    
    language_code = language_codes.get(language, "en")

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
    
    # 确保音频数据是二维的
    if len(audio.shape) == 1:
        audio = audio.reshape(-1, 1)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    sf.write(output_path, audio, samplerate=config.audio["sample_rate"])
    print(f"已輸出克隆音訊檔 {output_path}")
    
    return output_path

if __name__ == "__main__":
    # 測試用例
    text = "It took me quite a long time to develop a voice and now that I have it I am not going to be silent."
    speaker_path = "app/XTTS-v2/samples/zh-cn-sample.wav"
    xttsv(text, speaker_path)
