from google import genai
from google.genai import types
import time

def voice(voice_file, api_key):
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

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite", contents=["將音檔內容輸出成逐字稿並翻譯成日文，最後只要輸出翻譯過後的逐字稿", myfile]
    )

    return response.text