"""
文件完整性檢查腳本
用於驗證專案轉移時所有必要文件是否完整
"""

import os
import sys
from pathlib import Path

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def check_file(filepath, required=True):
    """檢查文件是否存在"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return True, format_size(size)
    else:
        return False, "缺失" if required else "選用"

def check_directory(dirpath, required=True):
    """檢查目錄是否存在"""
    if os.path.isdir(dirpath):
        # 計算目錄大小
        total_size = 0
        for dirpath_inner, dirnames, filenames in os.walk(dirpath):
            for filename in filenames:
                filepath = os.path.join(dirpath_inner, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
        return True, format_size(total_size)
    else:
        return False, "缺失" if required else "選用"

def check_project_structure():
    """檢查專案結構完整性"""
    print("=" * 70)
    print("🔍 Deep Video Translation - 文件完整性檢查")
    print("=" * 70)
    
    # 必要文件
    critical_files = {
        'requirements.txt': '依賴套件清單',
        '.env.example': '環境變數範本',
        'TRANSFER_GUIDE.md': '轉移指南',
        'check_dependencies.py': '依賴檢查腳本',
        'test_slide_translation.py': '簡報翻譯測試',
        'test_smtp.py': 'SMTP 測試',
        'app/main.py': '主程式',
        'app/video_processor.py': '影片處理器',
        'app/txtvoice.py': '語音轉文字模組',
        'app/xttsv.py': 'XTTS 語音合成',
        'app/f5ttsv.py': 'F5-TTS 語音合成',
        'app/queue_manager.py': '排隊管理',
        'app/email_service.py': '郵件服務',
        'app/task_processor.py': '任務處理器',
        'app/video_utils.py': '影片工具',
    }
    
    # 字體文件
    font_files = {
        'app/NotoSansCJKjp-Regular.otf': '日文字體',
        'app/NotoSansTC-Regular.ttf': '繁體中文字體',
    }
    
    # 模型目錄
    model_dirs = {
        'app/F5-TTS': 'F5-TTS 模型',
        'app/Wav2Lip': 'Wav2Lip 模型',
        'app/XTTS-v2': 'XTTS-v2 模型',
    }
    
    # 模板文件
    template_files = {
        'app/templates/landing.html': '首頁模板',
        'app/templates/app.html': '應用頁面模板',
    }
    
    # 選用目錄
    optional_dirs = {
        'temp': '暫存目錄 (會自動建立)',
        'output_videos': '輸出影片目錄 (會自動建立)',
    }
    
    # 檢查結果
    all_critical_ok = True
    all_fonts_ok = True
    all_models_ok = True
    all_templates_ok = True
    
    # 檢查必要文件
    print("\n📄 必要文件檢查")
    print("-" * 70)
    for filepath, description in critical_files.items():
        exists, info = check_file(filepath, required=True)
        status = "✅" if exists else "❌"
        print(f"{status} {filepath:40s} {description:20s} {info}")
        if not exists:
            all_critical_ok = False
    
    # 檢查字體文件
    print("\n🔤 字體文件檢查")
    print("-" * 70)
    for filepath, description in font_files.items():
        exists, info = check_file(filepath, required=True)
        status = "✅" if exists else "❌"
        print(f"{status} {filepath:40s} {description:20s} {info}")
        if not exists:
            all_fonts_ok = False
    
    if not all_fonts_ok:
        print("\n⚠️  字體文件缺失！")
        print("   請從原 Mac 複製字體文件，或從以下網址下載：")
        print("   https://fonts.google.com/noto/specimen/Noto+Sans+TC")
        print("   https://fonts.google.com/noto/specimen/Noto+Sans+JP")
    
    # 檢查模型目錄
    print("\n🤖 模型目錄檢查")
    print("-" * 70)
    for dirpath, description in model_dirs.items():
        exists, info = check_directory(dirpath, required=True)
        status = "✅" if exists else "❌"
        print(f"{status} {dirpath:40s} {description:20s} {info}")
        if not exists:
            all_models_ok = False
    
    if not all_models_ok:
        print("\n⚠️  模型目錄缺失！")
        print("   這些模型是專案運行的必要組件")
        print("   請確保從原 Mac 複製完整的模型目錄")
    
    # 檢查模板文件
    print("\n📋 模板文件檢查")
    print("-" * 70)
    for filepath, description in template_files.items():
        exists, info = check_file(filepath, required=True)
        status = "✅" if exists else "❌"
        print(f"{status} {filepath:40s} {description:20s} {info}")
        if not exists:
            all_templates_ok = False
    
    # 檢查選用目錄
    print("\n📁 選用目錄檢查")
    print("-" * 70)
    for dirpath, description in optional_dirs.items():
        exists, info = check_directory(dirpath, required=False)
        status = "✅" if exists else "⚪"
        print(f"{status} {dirpath:40s} {description:20s} {info}")
    
    # 檢查環境變數文件
    print("\n⚙️  環境設定檢查")
    print("-" * 70)
    env_exists, _ = check_file('.env', required=False)
    if env_exists:
        print("✅ .env                                     環境變數已設定")
    else:
        print("⚠️  .env                                     尚未設定")
        print("   請執行: cp .env.example .env")
        print("   然後編輯 .env 填入您的 API 金鑰和 SMTP 設定")
    
    # 檢查虛擬環境
    print("\n🐍 Python 環境檢查")
    print("-" * 70)
    venv_exists, venv_size = check_directory('.venv', required=False)
    if venv_exists:
        print(f"✅ .venv                                    虛擬環境已建立      {venv_size}")
    else:
        print("⚠️  .venv                                    虛擬環境未建立")
        print("   請執行: python3.10 -m venv .venv")
        print("   然後執行: source .venv/bin/activate")
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 檢查結果總結")
    print("=" * 70)
    
    results = [
        ("必要文件", all_critical_ok),
        ("字體文件", all_fonts_ok),
        ("模型目錄", all_models_ok),
        ("模板文件", all_templates_ok),
    ]
    
    for category, status in results:
        emoji = "✅" if status else "❌"
        print(f"{emoji} {category}")
    
    all_ok = all_critical_ok and all_fonts_ok and all_models_ok and all_templates_ok
    
    if all_ok:
        print("\n" + "=" * 70)
        print("🎉 所有必要文件檢查通過！")
        print("=" * 70)
        print("\n下一步:")
        print("1. 設定環境變數: cp .env.example .env && nano .env")
        print("2. 建立虛擬環境: python3.10 -m venv .venv")
        print("3. 啟動虛擬環境: source .venv/bin/activate")
        print("4. 安裝依賴: pip install -r requirements.txt")
        print("5. 檢查依賴: python check_dependencies.py")
        print("6. 啟動應用: python app/main.py")
        return 0
    else:
        print("\n" + "=" * 70)
        print("⚠️  部分文件缺失，請完整複製專案後重試")
        print("=" * 70)
        print("\n請參考 TRANSFER_GUIDE.md 獲取詳細的轉移指南")
        return 1

if __name__ == "__main__":
    sys.exit(check_project_structure())
