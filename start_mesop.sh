#!/bin/bash

# Deep Video Translation - Mesop GUI 啟動腳本

echo "🚀 啟動Deep Video Translation Mesop應用..."
echo "📱 應用將在瀏覽器中打開"
echo "🔗 默認地址: http://localhost:32123"
echo "⏹️  按 Ctrl+C 停止應用"

# 激活虛擬環境
echo "🔧 激活虛擬環境..."
source .venv/bin/activate

# 檢查Mesop是否安裝
if ! python -c "import mesop" 2>/dev/null; then
    echo "❌ Mesop未安裝，正在安裝..."
    pip install mesop
fi

# 進入app目錄
cd app

# 啟動Mesop應用（優先使用CLI）
APP_FILE="mesopgui.py"
echo "🎬 正在啟動應用 (${APP_FILE})..."

if command -v mesop >/dev/null 2>&1; then
    mesop "${APP_FILE}" --port 32123 --host 0.0.0.0
else
    echo "⚠️ 找不到 'mesop' CLI，嘗試使用 Python 模組方式啟動（部分版本不支援）..."
    python -m mesop "${APP_FILE}" --port 32123 --host 0.0.0.0 || {
        echo "❌ 啟動失敗：當前 mesop 版本不支援 'python -m mesop'。";
        echo "👉 請執行以下步驟重試：";
        echo "   1) source .venv/bin/activate";
        echo "   2) pip install --upgrade mesop";
        echo "   3) mesop ${APP_FILE} --port 32123 --host 0.0.0.0";
        exit 1;
    }
fi

echo "👋 應用已停止"
