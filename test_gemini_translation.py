#!/usr/bin/env python3
"""
診斷 Gemini 翻譯功能
"""

import os
import sys

# 設置環境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

def test_gemini_translation():
    """測試 Gemini 翻譯到不同語言"""
    
    from txtvoice import voice_with_gemini
    
    # 使用中文參考音頻
    chinese_audio = "temp/chinese_reference.wav"
    
    if not os.path.exists(chinese_audio):
        print("❌ 請先運行 test_chinese_ref_f5tts.py 創建中文參考音頻")
        return
    
    # 獲取 API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        api_key = input("\n請輸入 Gemini API Key: ").strip()
    
    if not api_key:
        print("❌ 需要 API Key 才能測試翻譯功能")
        return
    
    print("=" * 80)
    print("🔬 Gemini 翻譯診斷測試")
    print("=" * 80)
    print(f"📂 參考音頻: {chinese_audio}")
    print(f"📝 參考文本: 你好，這是一個測試音頻")
    print("=" * 80)
    
    # 測試不同語言
    test_languages = [
        ("英文", "English"),
        ("中文", "Chinese"),
        ("德文", "German"),
        ("法文", "French"),
        ("韓文", "Korean"),
        ("印地文", "Hindi")
    ]
    
    for i, (zh_name, en_name) in enumerate(test_languages, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(test_languages)}: {zh_name} ({en_name})")
        print(f"{'='*80}")
        
        try:
            result = voice_with_gemini(chinese_audio, api_key, zh_name)
            
            print(f"\n✅ 翻譯成功")
            print(f"📝 翻譯結果: {result}")
            print(f"📊 文本長度: {len(result)} 字符")
            
            # 簡單檢查：如果目標是非中文語言but結果包含大量中文字符，則可能有問題
            if zh_name != "中文":
                chinese_chars = sum(1 for c in result if '\u4e00' <= c <= '\u9fff')
                total_chars = len(result)
                chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
                
                if chinese_ratio > 0.5:
                    print(f"⚠️  警告：結果包含過多中文字符 ({chinese_ratio*100:.1f}%)")
                    print(f"   這可能表示翻譯未能正確轉換到目標語言")
                else:
                    print(f"✅ 語言檢查通過（中文字符占比: {chinese_ratio*100:.1f}%）")
                    
        except Exception as e:
            print(f"❌ 翻譯失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("診斷完成")
    print(f"{'='*80}")
    print("\n💡 如果non-中文語言的翻譯結果包含大量中文字符，")
    print("   則表示 Gemini 提示詞可能需要調整")


if __name__ == "__main__":
    test_gemini_translation()
