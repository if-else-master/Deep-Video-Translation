#!/usr/bin/env python3
"""
測試 Cross-Lingual F5-TTS 跨語言功能（使用中文參考音頻）
"""

import os
import sys
import subprocess

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def create_chinese_reference_audio():
    """創建一個中文參考音頻（使用系統 TTS）"""
    output_path = "temp/chinese_reference.wav"
    os.makedirs("temp", exist_ok=True)
    
    # 在 macOS 上使用 say 命令創建中文音頻
    chinese_text = "你好，這是一個測試音頻"
    
    try:
        # 使用 macOS 的 say 命令生成中文語音並轉換為 WAV
        temp_aiff = "temp/temp_chinese.aiff"
        subprocess.run(['say', '-v', 'Ting-Ting', '-o', temp_aiff, chinese_text], check=True)
        
        # 轉換為 24000Hz WAV
        subprocess.run([
            'ffmpeg', '-y', '-i', temp_aiff, 
            '-ar', '24000', '-ac', '1', 
            output_path
        ], check=True, capture_output=True)
        
        # 刪除臨時文件
        if os.path.exists(temp_aiff):
            os.remove(temp_aiff)
        
        print(f"✅ 創建中文參考音頻: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"⚠️  無法創建中文參考音頻: {e}")
        return None


def test_cross_lingual_with_chinese_ref():
    """使用中文參考音頻測試跨語言語音合成"""
    
    from f5ttsv import f5ttsv
    
    # 創建中文參考音頻
    speaker_audio = create_chinese_reference_audio()
    
    if not speaker_audio:
        print("❌ 無法創建參考音頻，測試終止")
        return False
    
    # 測試案例 - 使用中文參考音頻合成不同語言
    test_cases = [
        {
            "name": "中文 → 中文",
            "language": "中文",
            "text": "這是一個中文測試句子",
            "output": "temp/zh_to_zh.wav",
            "expected": "應該是正常的中文語音"
        },
        {
            "name": "中文 → 英文",
            "language": "英文",
            "text": "Hello, this is a test.",
            "output": "temp/zh_to_en.wav",
            "expected": "應該是英文語音（中文音色）"
        },
        {
            "name": "中文 → 德文 (Cross-Lingual)",
            "language": "德文",
            "text": "Guten Tag, wie geht es Ihnen?",
            "output": "temp/zh_to_de.wav",
            "expected": "應該是德文語音（中文音色）"
        },
        {
            "name": "中文 → 法文 (Cross-Lingual)",
            "language": "法文",
            "text": "Bonjour, comment allez-vous?",
            "output": "temp/zh_to_fr.wav",
            "expected": "應該是法文語音（中文音色）"
        },
        {
            "name": "中文 → 韓文 (Cross-Lingual)",
            "language": "韓文",
            "text": "안녕하세요",
            "output": "temp/zh_to_ko.wav",
            "expected": "應該是韓文語音（中文音色）"
        }
    ]
    
    print("\n" + "=" * 80)
    print("🎤 Cross-Lingual F5-TTS 跨語言測試（中文參考音頻）")
    print("=" * 80)
    print(f"📂 參考音頻: {speaker_audio}")
    print("⚠️  請仔細聽生成的音頻，確認是否為目標語言而非快速中文")
    print("=" * 80)
    
    success_count = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"測試 {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*80}")
        print(f"📝 文本: {test['text']}")
        print(f"🌐 語言: {test['language']}")
        print(f"💾 輸出: {test['output']}")
        print(f"🎯 預期: {test['expected']}")
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
                duration = get_audio_duration(result)
                print(f"\n✅ 生成成功")
                print(f"   📊 文件大小: {size_kb:.1f} KB")
                print(f"   ⏱️  音頻長度: {duration:.2f} 秒")
                print(f"   🎧 請播放並聽取: {result}")
                success_count += 1
            else:
                print(f"\n❌ 失敗：輸出文件不存在")
                
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"測試完成: {success_count}/{len(test_cases)} 成功")
    print(f"{'='*80}")
    print("\n💡 請手動播放生成的音頻文件檢查：")
    for test in test_cases:
        if os.path.exists(test['output']):
            print(f"   🎧 {test['name']}: {test['output']}")
    
    return success_count == len(test_cases)


def get_audio_duration(audio_path):
    """獲取音頻時長"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
             '-show_format', audio_path],
            capture_output=True, text=True
        )
        import json
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        return 0.0


if __name__ == "__main__":
    print("\n🚀 Cross-Lingual F5-TTS 跨語言測試程序\n")
    test_cross_lingual_with_chinese_ref()
