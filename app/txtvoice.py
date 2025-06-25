from google import genai
from google.genai import types
import time
import os
import subprocess

def check_if_file_has_audio(file_path):
    """檢查文件是否包含音頻內容"""
    try:
        # 使用 ffprobe 檢查音頻流
        command = f'ffprobe -v quiet -print_format json -show_streams "{file_path}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
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

def voice(voice_file, api_key, target_language="日文"):
    """語音識別並翻譯函數，支援處理沒有音頻的文件"""
    
    # 首先檢查文件是否存在
    if not os.path.exists(voice_file):
        raise Exception(f"音頻文件不存在: {voice_file}")
    
    # 檢查文件是否包含音頻內容
    has_audio = check_if_file_has_audio(voice_file)
    
    if not has_audio:
        print(f"⚠️ 文件 {voice_file} 沒有音頻內容或音頻時長太短")
        return ""  # 返回空字串表示沒有音頻內容
    
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
            "中文": "將音檔內容輸出成逐字稿，如果原本就是中文就直接輸出逐字稿，如果是其他語言就翻譯成中文，最後只要輸出逐字稿"
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
        print(f"❌ 語音識別和翻譯失敗: {e}")
        raise Exception(f"語音識別和翻譯失敗: {e}")
    
    finally:
        # 清理上傳的文件
        try:
            if 'myfile' in locals() and myfile:
                client.files.delete(name=myfile.name)
                print(f"🗑️ 已清理上傳的文件")
        except Exception as cleanup_error:
            print(f"⚠️ 清理文件時發生錯誤: {cleanup_error}")