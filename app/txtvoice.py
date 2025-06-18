from google import genai
from google.genai import types
import time

def voice(voice_file, api_key, target_language="日文"):
    client = genai.Client(api_key=api_key)

    myfile = client.files.upload(file=voice_file)
    
    # 等待文件處理完成
    print("正在等待文件處理完成...")
    while myfile.state == "PROCESSING":
        time.sleep(2)
        myfile = client.files.get(name=myfile.name)
    
    if myfile.state == "FAILED":
        raise Exception("文件處理失敗")
    
    print(f"文件狀態: {myfile.state}")

    # 根據目標語言設置提示詞
    language_prompts = {
        "日文": "將音檔內容輸出成逐字稿並翻譯成日文，最後只要輸出翻譯過後的逐字稿",
        "英文": "將音檔內容輸出成逐字稿並翻譯成英文，最後只要輸出翻譯過後的逐字稿", 
        "中文": "將音檔內容輸出成逐字稿，如果原本就是中文就直接輸出逐字稿，如果是其他語言就翻譯成中文，最後只要輸出逐字稿"
    }
    
    prompt = language_prompts.get(target_language, language_prompts["日文"])

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite", contents=[prompt, myfile]
    )

    return response.text