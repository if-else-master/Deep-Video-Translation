#!/bin/bash

# Deep Video Translation 啟動腳本

echo "🚀 Deep Video Translation 啟動中..."
echo ""

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "❌ 找不到虛擬環境 .venv"
    echo "請先執行: python -m venv .venv"
    exit 1
fi

# 啟動虛擬環境
echo "📦 啟動虛擬環境..."
source .venv/bin/activate

# 檢查 requirements
echo "📋 檢查依賴套件..."
pip list | grep -q "python-dotenv" || {
    echo "⚠️  發現缺少依賴，正在安裝..."
    pip install python-dotenv
}

# 檢查 .env 文件
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  警告：找不到 .env 文件"
    echo "   Email 通知功能需要 SMTP 設定"
    echo "   請複製 .env.example 為 .env 並填入您的設定"
    echo ""
    read -p "是否繼續啟動？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 創建必要目錄
echo "📁 創建必要目錄..."
mkdir -p temp/uploads
mkdir -p audio_files
mkdir -p output_videos

# 啟動服務
cd app
echo ""
echo "🌐 啟動 Web 服務..."
echo "📍 訪問: http://localhost:32123"
echo ""
python main.py
