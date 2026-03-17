#!/usr/bin/env python3
"""
最終驗證測試：模擬完整用戶場景
使用示例德文/法文/韓文文本直接測試 TTS
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from f5ttsv import f5ttsv

def final_verification_test():
    """最終驗證測試"""
    
    # 使用中文參考音頻
    chinese_audio = "temp/chinese_reference.wav"
    
    if not os.path.exists(chinese_audio):
        print("⚠️  中文參考音頻不存在，正在創建...")
        import subprocess
        os.makedirs("temp", exist_ok=True)
        
        try:
            temp_aiff = "temp/temp_chinese.aiff"
            subprocess.run(['say', '-v', 'Ting-Ting', '-o', temp_aiff, "你好，這是一個測試"], check=True, capture_output=True)
            subprocess.run(['ffmpeg', '-y', '-i', temp_aiff, '-ar', '24000', '-ac', '1', chinese_audio], 
                         check=True, capture_output=True)
            if os.path.exists(temp_aiff):
                os.remove(temp_aiff)
            print(f"✅ 創建參考音頻: {chinese_audio}")
        except Exception as e:
            print(f"❌ 無法創建參考音頻: {e}")
            print("請手動提供一個中文 WAV 音頻文件到 temp/chinese_reference.wav")
            return
    
    print("\n" + "=" * 80)
    print("🎯 最終驗證測試")
    print("=" * 80)
    print("測試目的：驗證 Cross-Lingual F5-TTS 能正確合成非中英文語言")
    print("測試方法：使用中文參考音頻 + 目標語言文本 → 生成目標語言語音")
    print("=" * 80)
    
    # 測試案例：使用真實的德文、法文、韓文句子
    test_cases = [
        {
            "language": "德文",
            "text": "Guten Morgen! Wie geht es Ihnen heute? Ich hoffe, Sie haben einen schönen Tag.",
            "expected": "應該聽到清晰的德文發音",
            "output": "temp/final_test_german.wav"
        },
        {
            "language": "法文",
            "text": "Bonjour! Comment allez-vous aujourd'hui? J'espère que vous passez une bonne journée.",
            "expected": "應該聽到清晰的法文發音",
            "output": "temp/final_test_french.wav"
        },
        {
            "language": "韓文",
            "text": "안녕하세요! 오늘 어떻게 지내세요? 좋은 하루 보내시길 바랍니다.",
            "expected": "應該聽到清晰的韓文發音",
            "output": "temp/final_test_korean.wav"
        },
        {
            "language": "印地文",
            "text": "नमस्ते! आप आज कैसे हैं? मुझे उम्मीद है कि आपका दिन अच्छा गुजर रहा है।",
            "expected": "應該聽到清晰的印地文發音",
            "output": "temp/final_test_hindi.wav"
        },
        {
            "language": "英文",
            "text": "Hello! How are you today? I hope you're having a wonderful day.",
            "expected": "應該聽到清晰的英文發音（對照組）",
            "output": "temp/final_test_english.wav"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(test_cases)}: {test['language']}")
        print(f"{'='*80}")
        print(f"📝 測試文本: {test['text']}")
        print(f"🎯 預期結果: {test['expected']}")
        print()
        
        try:
            result_path = f5ttsv(
                text=test['text'],
                speaker_audio_path=chinese_audio,
                output_path=test['output'],
                language=test['language']
            )
            
            if os.path.exists(result_path):
                size_kb = os.path.getsize(result_path) / 1024
                print(f"\n✅ 生成成功")
                print(f"   文件: {result_path}")
                print(f"   大小: {size_kb:.1f} KB")
                results.append((test['language'], True, result_path))
            else:
                print(f"\n❌ 生成失敗：文件不存在")
                results.append((test['language'], False, None))
                
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            results.append((test['language'], False, None))
    
    # 總結
    print(f"\n{'='*80}")
    print("測試總結")
    print(f"{'='*80}")
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for lang, success, path in results:
        status = "✅" if success else "❌"
        print(f"{status} {lang}: {'成功' if success else '失敗'}")
    
    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 所有測試通過！")
        print("\n📋 下一步：請播放生成的音頻文件並驗證：")
        for lang, success, path in results:
            if success and path:
                print(f"   🎧 {lang}: {path}")
        print("\n⚠️  重要檢查項：")
        print("   1. 音頻是否為正確的目標語言（而非快速中文）")
        print("   2. 發音是否清晰自然")
        print("   3. 語速是否正常（而非過快）")
        print("   4. 音色是否保持參考音頻的特徵")
    else:
        print(f"\n⚠️  有 {total_count - success_count} 個測試失敗")
        print("   請檢查錯誤信息並重試")


if __name__ == "__main__":
    final_verification_test()
