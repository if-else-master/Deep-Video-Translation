from google import genai
from google.genai import types

def voice(voice_file):
    client = genai.Client(api_key="xxxxx")

    myfile = client.files.upload(file=voice_file)

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite", contents=["將音檔內容輸出成逐字稿並翻譯成日文，最後只要輸出翻譯過後的逐字稿", myfile]
    )

    return response.text