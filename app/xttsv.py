import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import soundfile as sf
import numpy as np
import os
import subprocess
import re

def extract_audio_from_video(video_path, output_audio_path):
    """從視頻文件中提取音頻"""
    try:
        command = f'ffmpeg -y -i "{video_path}" -ar 16000 -ac 1 "{output_audio_path}"'
        subprocess.run(command, shell=True, check=True, capture_output=True)
        return output_audio_path
    except subprocess.CalledProcessError as e:
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
    
    # 設置語言代碼和字符限制
    language_configs = {
        "日文": {"code": "ja", "max_length": 80},
        "英文": {"code": "en", "max_length": 100}, 
        "中文": {"code": "zh", "max_length": 82}
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
