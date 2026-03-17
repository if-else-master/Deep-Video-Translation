#!/usr/bin/env python3
"""
簡單測試德文生成
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from f5ttsv import f5ttsv

# 使用現有的中文參考音頻
speaker_audio = "temp/chinese_reference.wav"

if not os.path.exists(speaker_audio):
    print(f"❌ 參考音頻不存在: {speaker_audio}")
    sys.exit(1)

print("測試德文生成...")
try:
    result = f5ttsv(
        text="Hallo",
        speaker_audio_path=speaker_audio,
        output_path="temp/test_de_simple.wav",
        language="德文"
    )
    print(f"✅ 成功: {result}")
except Exception as e:
    print(f"❌ 失敗: {e}")
    import traceback
    traceback.print_exc()
