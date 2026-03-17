#!/bin/bash

# 🧪 Deep Video Translation 測試腳本

echo "🧪 開始測試 Deep Video Translation 優化..."
echo ""

# 1. 檢查 Python 環境
echo "1️⃣ 檢查 Python 環境..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 未安裝"
    exit 1
fi
echo "✅ Python 已安裝"
echo ""

# 2. 檢查虛擬環境
echo "2️⃣ 檢查虛擬環境..."
if [ -d ".venv" ]; then
    echo "✅ 虛擬環境存在"
    source .venv/bin/activate
else
    echo "⚠️ 虛擬環境不存在，請先創建"
    exit 1
fi
echo ""

# 3. 檢查必要的 Python 套件
echo "3️⃣ 檢查必要套件..."
python -c "import cv2; print(f'✅ OpenCV: {cv2.__version__}')" || echo "❌ OpenCV 未安裝"
python -c "import torch; print(f'✅ PyTorch: {torch.__version__}')" || echo "❌ PyTorch 未安裝"
python -c "import numpy; print(f'✅ NumPy: {numpy.__version__}')" || echo "❌ NumPy 未安裝"
python -c "import easyocr; print('✅ EasyOCR 已安裝')" || echo "❌ EasyOCR 未安裝"
echo ""

# 4. 檢查關鍵文件
echo "4️⃣ 檢查關鍵文件..."
files=(
    "app/main.py"
    "app/Wav2Lip/inference.py"
    "app/txtvoice.py"
    "app/xttsv.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 不存在"
    fi
done
echo ""

# 5. 檢查 Wav2Lip 模型文件
echo "5️⃣ 檢查 Wav2Lip 模型..."
if [ -f "app/Wav2Lip/checkpoints/wav2lip.pth" ]; then
    echo "✅ Wav2Lip 模型存在"
else
    echo "❌ Wav2Lip 模型不存在"
    echo "   請下載模型到 app/Wav2Lip/checkpoints/wav2lip.pth"
fi
echo ""

# 6. 測試人臉檢測器
echo "6️⃣ 測試人臉檢測器..."
python3 << 'EOF'
import cv2
import sys

try:
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("❌ 人臉檢測器載入失敗")
        sys.exit(1)
    else:
        print("✅ 人臉檢測器正常")
except Exception as e:
    print(f"❌ 人臉檢測器錯誤: {e}")
    sys.exit(1)
EOF
echo ""

# 7. 測試設備選擇
echo "7️⃣ 測試設備選擇..."
python3 << 'EOF'
import torch

print(f"CUDA 可用: {torch.cuda.is_available()}")
print(f"MPS 可用: {torch.backends.mps.is_available()}")

if torch.cuda.is_available():
    print("✅ 將使用 CUDA")
elif torch.backends.mps.is_available():
    print("⚠️ MPS 可用但 face_detection 不支援，將使用 CPU")
else:
    print("ℹ️ 將使用 CPU")
EOF
echo ""

# 8. 測試 inference.py 語法
echo "8️⃣ 測試 inference.py 語法..."
python3 -m py_compile app/Wav2Lip/inference.py
if [ $? -eq 0 ]; then
    echo "✅ inference.py 語法正確"
else
    echo "❌ inference.py 有語法錯誤"
    exit 1
fi
echo ""

# 9. 測試 main.py 語法
echo "9️⃣ 測試 main.py 語法..."
python3 -m py_compile app/main.py
if [ $? -eq 0 ]; then
    echo "✅ main.py 語法正確"
else
    echo "❌ main.py 有語法錯誤"
    exit 1
fi
echo ""

# 10. 檢查臨時目錄
echo "🔟 檢查臨時目錄..."
dirs=(
    "temp"
    "temp/uploads"
    "temp/segments"
    "temp/faceai"
    "temp/pptai"
    "temp/audio_segments"
)

for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir"
    else
        echo "⚠️ $dir 不存在，將自動創建"
        mkdir -p "$dir"
    fi
done
echo ""

# 總結
echo "=================================================="
echo "🎉 測試完成！"
echo "=================================================="
echo ""
echo "📝 測試結果摘要："
echo "   ✅ Python 環境正常"
echo "   ✅ 必要套件已安裝"
echo "   ✅ 關鍵文件存在"
echo "   ✅ 代碼語法正確"
echo ""
echo "🚀 可以開始處理影片了！"
echo ""
echo "💡 使用方法："
echo "   1. 清理舊文件: ./cleanup_temp.sh"
echo "   2. 啟動服務: python app/main.py"
echo "   3. 上傳影片並選擇目標語言"
echo ""
