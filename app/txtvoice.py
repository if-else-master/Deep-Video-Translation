"""
語音識別和翻譯模組
支援多種 API：Gemini、OpenAI Whisper
"""

from google import genai
from google.genai import types
import time
import os
import subprocess
import requests
import json

def check_if_file_has_audio(file_path):
    """檢查文件是否包含音頻內容"""
    try:
        # 使用 ffprobe 檢查音頻流
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


def voice(voice_file, api_key, target_language="日文", api_provider="gemini"):
    """
    語音識別並翻譯函數
    
    參數:
        voice_file: 音頻/視頻文件路徑
        api_key: API 密鑰
        target_language: 目標語言
        api_provider: API 提供者 (gemini, openai, claude, local_llm)
    """
    
    # 首先檢查文件是否存在
    if not os.path.exists(voice_file):
        raise Exception(f"音頻文件不存在: {voice_file}")
    
    # 檢查文件是否包含音頻內容
    has_audio = check_if_file_has_audio(voice_file)
    
    if not has_audio:
        print(f"⚠️ 文件 {voice_file} 沒有音頻內容或音頻時長太短")
        return ""  # 返回空字串表示沒有音頻內容
    
    # 根據 API 提供者選擇處理方式
    if api_provider == "openai":
        return voice_with_openai(voice_file, api_key, target_language)
    elif api_provider == "gemini":
        return voice_with_gemini(voice_file, api_key, target_language)
    else:
        # Claude 和本地 LLM 不支援語音識別，退回使用 Gemini
        # 但如果沒有 Gemini API Key，則無法進行語音識別
        print(f"⚠️ {api_provider} 不支援語音識別，嘗試使用 Gemini 備用方案")
        # 這裡先嘗試 Gemini，如果失敗則返回空字串
        try:
            return voice_with_gemini(voice_file, api_key, target_language)
        except Exception as e:
            print(f"⚠️ Gemini 語音識別也失敗: {e}")
            print("💡 建議：對於非 Gemini/OpenAI API，請在設置中額外提供 Gemini API Key 用於語音識別")
            return ""


def voice_with_gemini(voice_file, api_key, target_language="日文"):
    """使用 Gemini API 進行語音識別和翻譯"""
    try:
        client = genai.Client(api_key=api_key)

        print(f"🎵 正在上傳音頻文件: {voice_file}")
        myfile = client.files.upload(file=voice_file)
        
        # 等待文件處理完成
        print("正在等待文件處理完成...")
        max_wait_time = 300  # 最大等待5分鐘
        wait_time = 0
        
        while myfile.state == "PROCESSING" and wait_time < max_wait_time:
            time.sleep(2)
            wait_time += 2
            myfile = client.files.get(name=myfile.name)
            if wait_time % 10 == 0:  # 每10秒顯示一次進度
                print(f"  文件處理中... ({wait_time}秒)")
        
        if myfile.state == "FAILED":
            raise Exception("Gemini 文件處理失敗")
        
        if myfile.state == "PROCESSING":
            raise Exception("文件處理超時，請稍後再試")
        
        print(f"文件狀態: {myfile.state}")

        # 根據目標語言設置提示詞
        language_prompts = {
            "日文": "將音檔內容輸出成逐字稿並翻譯成日文，最後只要輸出翻譯過後的逐字稿",
            "英文": "將音檔內容輸出成逐字稿並翻譯成英文，最後只要輸出翻譯過後的逐字稿", 
            "中文": "將音檔內容輸出成逐字稿，如果原本就是中文就直接輸出逐字稿，如果是其他語言就翻譯成中文，最後只要輸出逐字稿",
            "德文": "將音檔內容輸出成逐字稿並翻譯成德文，最後只要輸出翻譯過後的逐字稿",
            "法文": "將音檔內容輸出成逐字稿並翻譯成法文，最後只要輸出翻譯過後的逐字稿",
            "俄文": "將音檔內容輸出成逐字稿並翻譯成俄文，最後只要輸出翻譯過後的逐字稿",
            "義大利文": "將音檔內容輸出成逐字稿並翻譯成義大利文，最後只要輸出翻譯過後的逐字稿",
            "西班牙文": "將音檔內容輸出成逐字稿並翻譯成西班牙文，最後只要輸出翻譯過後的逐字稿"
        }
        
        prompt = language_prompts.get(target_language, language_prompts["日文"])

        print(f"🔄 正在進行語音識別和翻譯...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite", contents=[prompt, myfile]
        )

        if response and response.text:
            # 清理翻譯結果
            result_text = response.text.strip()
            
            # 移除常見的前綴
            prefixes_to_remove = [
                "Here's the translated transcript:",
                "Here's the English translation:",
                "Here's the Japanese translation:",
                "翻譯結果：",
                "逐字稿：",
                "Transcript:",
                "Translation:"
            ]
            
            for prefix in prefixes_to_remove:
                if result_text.startswith(prefix):
                    result_text = result_text[len(prefix):].strip()
            
            print(f"✅ 語音識別和翻譯完成")
            return result_text
        else:
            print("⚠️ Gemini 沒有返回翻譯結果")
            return ""
            
    except Exception as e:
        print(f"❌ Gemini 語音識別和翻譯失敗: {e}")
        raise Exception(f"語音識別和翻譯失敗: {e}")
    
    finally:
        # 清理上傳的文件
        try:
            if 'myfile' in locals() and myfile:
                client.files.delete(name=myfile.name)
                print(f"🗑️ 已清理上傳的文件")
        except Exception as cleanup_error:
            print(f"⚠️ 清理文件時發生錯誤: {cleanup_error}")


def voice_with_openai(voice_file, api_key, target_language="日文"):
    """使用 OpenAI Whisper API 進行語音識別，然後翻譯"""
    
    # 首先需要將音頻提取為 WAV 格式
    temp_audio_path = "temp/whisper_temp_audio.wav"
    os.makedirs("temp", exist_ok=True)
    
    audio_path = extract_audio_to_wav(voice_file, temp_audio_path)
    if not audio_path:
        raise Exception("無法提取音頻文件")
    
    try:
        # 步驟 1: 使用 Whisper API 進行語音識別
        print(f"🎵 正在使用 OpenAI Whisper 進行語音識別...")
        
        with open(audio_path, 'rb') as audio_file:
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            files = {
                'file': ('audio.wav', audio_file, 'audio/wav'),
                'model': (None, 'whisper-1'),
            }
            
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                timeout=120
            )
        
        if response.status_code != 200:
            raise Exception(f"Whisper API 錯誤: {response.text}")
        
        transcript = response.json().get("text", "")
        print(f"📝 語音識別結果: {transcript[:100]}...")
        
        if not transcript:
            print("⚠️ Whisper 沒有識別到任何文字")
            return ""
        
        # 步驟 2: 使用 GPT 進行翻譯
        print(f"🔄 正在翻譯至 {target_language}...")
        
        language_map = {
            "日文": "Japanese",
            "英文": "English",
            "中文": "Chinese",
            "德文": "German",
            "法文": "French",
            "俄文": "Russian",
            "義大利文": "Italian",
            "西班牙文": "Spanish"
        }
        
        target_lang_en = language_map.get(target_language, "Japanese")
        
        translate_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        translate_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_lang_en}. Output ONLY the translation, nothing else."},
                {"role": "user", "content": transcript}
            ],
            "temperature": 0.3
        }
        
        translate_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=translate_headers,
            json=translate_payload,
            timeout=60
        )
        
        if translate_response.status_code != 200:
            raise Exception(f"翻譯 API 錯誤: {translate_response.text}")
        
        translated_text = translate_response.json()["choices"][0]["message"]["content"].strip()
        print(f"✅ 翻譯完成")
        
        return translated_text
        
    except Exception as e:
        print(f"❌ OpenAI 語音識別/翻譯失敗: {e}")
        raise Exception(f"語音識別和翻譯失敗: {e}")
    
    finally:
        # 清理臨時音頻文件
        if os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except:
                pass
