#!/bin/bash
# 清理臨時處理文件的腳本

echo "🧹 開始清理臨時文件..."

# 清理 faceai 目錄中的所有 _processed 文件
echo "清理 temp/faceai..."
rm -f temp/faceai/*_processed*.mp4
rm -f temp/faceai/*_audio.wav

# 清理 pptai 目錄中的所有 _processed 文件
echo "清理 temp/pptai..."
rm -f temp/pptai/*_processed*.mp4
rm -f temp/pptai/*_audio.wav

# 清理其他臨時文件
echo "清理其他臨時文件..."
rm -f temp/extracted_audio.wav
rm -f temp/result.avi
rm -f temp/segment_list.txt
rm -f temp/faulty_frame.jpg

echo "✅ 清理完成！"
echo ""
echo "保留的文件："
echo "📁 temp/faceai/"
ls -lh temp/faceai/*.mp4 2>/dev/null || echo "  (空)"
echo ""
echo "📁 temp/pptai/"
ls -lh temp/pptai/*.mp4 2>/dev/null || echo "  (空)"
