#!/usr/bin/env python3
"""
快速測試 Cross-Lingual F5-TTS 語音合成功能
"""

import os
import sys

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from f5ttsv import f5ttsv

def quick_test():
    """快速測試語音合成"""
    
    # 測試用的參考音頻（使用已有的 output.wav）
    speaker_audio = "/Users/raychang/Documents/專案/Deep-Video-Translation/output.wav"
    
    if not os.path.exists(speaker_audio):
        print(f"❌ 參考音頻不存在: {speaker_audio}")
        print("請提供一個有效的音頻文件路徑")
        return False
    
    # 創建輸出目錄
    os.makedirs("temp", exist_ok=True)
    
    # 測試案例
    test_cases = [
        {
            "name": "德文 (Cross-Lingual)",
            "language": "德文",
            "text": "Hallo, guten Tag!",
            "output": "temp/test_german_output.wav"
        },
        {
            "name": "法文 (Cross-Lingual)",
            "language": "法文",
            "text": "Bonjour!",
            "output": "temp/test_french_output.wav"
        },
        {
            "name": "英文 (Standard)",
            "language": "英文",
            "text": "Hello, how are you?",
            "output": "temp/test_english_output.wav"
        }
    ]
    
    print("=" * 70)
    print("🎤 Cross-Lingual F5-TTS 語音合成測試")
    print("=" * 70)
    print(f"📂 參考音頻: {speaker_audio}")
    print()
    
    success_count = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"測試 {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*70}")
        print(f"📝 文本: {test['text']}")
        print(f"🌐 語言: {test['language']}")
        print(f"💾 輸出: {test['output']}")
        print()
        
        try:
            result = f5ttsv(
                text=test['text'],
                speaker_audio_path=speaker_audio,
                output_path=test['output'],
                language=test['language']
            )
            
            if os.path.exists(result):
                size_kb = os.path.getsize(result) / 1024
                print(f"\n✅ 成功！文件大小: {size_kb:.1f} KB")
                success_count += 1
            else:
                print(f"\n❌ 失敗：輸出文件不存在")
                
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print(f"測試完成: {success_count}/{len(test_cases)} 成功")
    print(f"{'='*70}")
    
    return success_count == len(test_cases)


if __name__ == "__main__":
    quick_test()
