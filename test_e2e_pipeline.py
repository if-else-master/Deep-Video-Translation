#!/usr/bin/env python3
"""
完整端到端測試：模擬實際應用場景
中文音頻 → Gemini 翻譯 → F5-TTS 語音合成
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from txtvoice import voice
from f5ttsv import f5ttsv

def test_full_pipeline():
    """測試完整流程"""
    
    # 使用中文參考音頻
    chinese_audio = "temp/chinese_reference.wav"
    
    if not os.path.exists(chinese_audio):
        print("❌ 請先運行 test_chinese_ref_f5tts.py 創建中文參考音頻")
        return False
    
    # 測試語言
    test_languages = [
        {"name": "英文", "english_name": "English"},
        {"name": "德文", "english_name": "German"},
        {"name": "法文", "english_name": "French"},
        {"name": "韓文", "english_name": "Korean"}
    ]
    
    print("=" * 80)
    print("🔬 完整端到端測試")
    print("=" * 80)
    print("⚠️  此測試需要有效的 Gemini API Key")
    print("📝 測試流程：中文音頻 → Gemini 翻譯 → F5-TTS 語音合成")
    print("=" * 80)
    
    # 獲取 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        api_key = input("\n請輸入 Gemini API Key（或按 Enter 跳過翻譯測試）: ").strip()
    
    if not api_key:
        print("\n⚠️  沒有 API Key，跳過翻譯測試")
        print("💡 將直接使用示例文本測試 TTS 功能\n")
        test_tts_only(chinese_audio, test_languages)
        return
    
    # 完整測試
    for i, lang_config in enumerate(test_languages, 1):
        lang = lang_config["name"]
        eng_name = lang_config["english_name"]
        
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(test_languages)}: {lang} ({eng_name})")
        print(f"{'='*80}")
        
        # 步驟 1: 語音識別和翻譯
        print(f"\n📍 步驟 1: 使用 Gemini 進行語音識別和翻譯")
        print(f"   目標語言: {lang}")
        
        try:
            translated_text = voice(chinese_audio, api_key, lang, "gemini")
            print(f"   ✅ 翻譯完成")
            print(f"   📝 翻譯結果: {translated_text}")
            print(f"   📊 文本長度: {len(translated_text)} 字符")
            
            # 檢查翻譯結果是否合理
            if len(translated_text) == 0:
                print(f"   ⚠️  警告：翻譯結果為空")
                continue
            
        except Exception as e:
            print(f"   ❌ 翻譯失敗: {e}")
            continue
        
        # 步驟 2: 語音合成
        print(f"\n📍 步驟 2: 使用 F5-TTS 進行語音合成")
        output_path = f"temp/e2e_test_{lang}.wav"
        
        try:
            result = f5ttsv(
                text=translated_text,
                speaker_audio_path=chinese_audio,
                output_path=output_path,
                language=lang
            )
            
            if os.path.exists(result):
                size_kb = os.path.getsize(result) / 1024
                print(f"   ✅ 語音合成成功")
                print(f"   📊 文件大小: {size_kb:.1f} KB")
                print(f"   🎧 輸出文件: {result}")
            else:
                print(f"   ❌ 輸出文件不存在")
                
        except Exception as e:
            print(f"   ❌ 語音合成失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✅ 完整端到端測試完成")
    print(f"{'='*80}")
    print("\n💡 請播放生成的音頻文件並檢查：")
    print("   1. 音頻是否為正確的語言（而非快速中文）")
    print("   2. 音色是否保持參考音頻的特徵")
    print("   3. 發音是否清晰自然")


def test_tts_only(chinese_audio, test_languages):
    """僅測試 TTS 功能（無翻譯）"""
    
    # 示例文本
    example_texts = {
        "英文": "Hello, this is a test sentence in English.",
        "德文": "Guten Tag, das ist ein Testsatz auf Deutsch.",
        "法文": "Bonjour, c'est une phrase de test en français.",
        "韓文": "안녕하세요, 이것은 한국어 테스트 문장입니다."
    }
    
    print("\n🔬 F5-TTS 語音合成測試（跳過翻譯）")
    print("=" * 80)
    
    for i, lang_config in enumerate(test_languages, 1):
        lang = lang_config["name"]
        text = example_texts.get(lang, "Test")
        
        print(f"\n測試 {i}/{len(test_languages)}: {lang}")
        print(f"   文本: {text}")
        
        output_path = f"temp/tts_only_{lang}.wav"
        
        try:
            result = f5ttsv(
                text=text,
                speaker_audio_path=chinese_audio,
                output_path=output_path,
                language=lang
            )
            
            if os.path.exists(result):
                size_kb = os.path.getsize(result) / 1024
                print(f"   ✅ 成功: {size_kb:.1f} KB")
            else:
                print(f"   ❌ 失敗")
                
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")


if __name__ == "__main__":
    test_full_pipeline()
