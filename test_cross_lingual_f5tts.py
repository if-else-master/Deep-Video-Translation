#!/usr/bin/env python3
"""
測試 Cross-Lingual F5-TTS 模型
"""

import os
import sys

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from f5ttsv import f5ttsv

def test_cross_lingual_languages():
    """測試支援的跨語言語音合成"""
    
    # 測試文本（使用不同語言）
    test_cases = [
        {
            "language": "德文",
            "text": "Guten Tag, wie geht es Ihnen?",
            "output": "temp/test_german.wav"
        },
        {
            "language": "法文",
            "text": "Bonjour, comment allez-vous?",
            "output": "temp/test_french.wav"
        },
        {
            "language": "印地文",
            "text": "नमस्ते, आप कैसे हैं?",
            "output": "temp/test_hindi.wav"
        },
        {
            "language": "韓文",
            "text": "안녕하세요, 어떻게 지내세요?",
            "output": "temp/test_korean.wav"
        },
        {
            "language": "英文",
            "text": "Hello, how are you today?",
            "output": "temp/test_english.wav"
        },
        {
            "language": "中文",
            "text": "你好，今天過得怎麼樣？",
            "output": "temp/test_chinese.wav"
        }
    ]
    
    # 創建測試音頻目錄
    os.makedirs("temp", exist_ok=True)
    
    # 需要一個參考音頻文件（這裡使用佔位符）
    # 在實際測試中，您需要提供一個真實的音頻文件
    speaker_audio = "temp/test_speaker.wav"
    
    # 如果沒有測試音頻，創建一個簡單的提示
    if not os.path.exists(speaker_audio):
        print("⚠️  請提供參考音頻文件：temp/test_speaker.wav")
        print("💡 您可以使用任何 WAV 音頻文件作為參考音頻")
        return False
    
    print("=" * 60)
    print("開始測試 Cross-Lingual F5-TTS")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試 {i}/{len(test_cases)}: {test_case['language']}")
        print(f"   文本: {test_case['text']}")
        
        try:
            output_path = f5ttsv(
                text=test_case['text'],
                speaker_audio_path=speaker_audio,
                output_path=test_case['output'],
                language=test_case['language']
            )
            
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / 1024  # KB
                print(f"   ✅ 成功！輸出文件: {output_path} ({file_size:.1f} KB)")
                success_count += 1
            else:
                print(f"   ❌ 失敗：輸出文件不存在")
                fail_count += 1
                
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"測試完成：✅ {success_count} 成功 / ❌ {fail_count} 失敗")
    print("=" * 60)
    
    return fail_count == 0


def test_model_loading():
    """測試模型加載"""
    print("=" * 60)
    print("測試模型加載")
    print("=" * 60)
    
    try:
        from f5ttsv import get_cross_lingual_model, get_f5tts_model
        
        print("\n1️⃣ 測試標準 F5-TTS 模型加載...")
        model1 = get_f5tts_model()
        print("   ✅ 標準 F5-TTS 模型加載成功")
        
        print("\n2️⃣ 測試 Cross-Lingual F5-TTS 模型加載...")
        model2 = get_cross_lingual_model()
        print("   ✅ Cross-Lingual F5-TTS 模型加載成功")
        
        print("\n" + "=" * 60)
        print("✅ 所有模型加載成功！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 模型加載失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Cross-Lingual F5-TTS 測試程序\n")
    
    # 首先測試模型加載
    if not test_model_loading():
        print("\n❌ 模型加載測試失敗，請檢查模型文件")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("模型加載成功！如需測試語音合成，請提供參考音頻文件")
    print("=" * 60)
    
    # 可選：測試語音合成（需要參考音頻）
    # test_cross_lingual_languages()
