"""
依賴檢查腳本
檢查 requirements.txt 中的所有套件是否已正確安裝
"""

import sys
import importlib
import subprocess

def check_package_installed(package_name):
    """檢查套件是否已安裝"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def get_installed_packages():
    """獲取已安裝的套件列表"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        packages = {}
        for line in result.stdout.strip().split('\n'):
            if '==' in line:
                name, version = line.split('==')
                packages[name.lower()] = version
        return packages
    except Exception as e:
        print(f"❌ 無法獲取已安裝套件列表: {e}")
        return {}

def parse_requirements(filename='requirements.txt'):
    """解析 requirements.txt 文件"""
    packages = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳過註釋和空行
                if not line or line.startswith('#') or line.startswith('='):
                    continue
                
                # 處理不同的版本指定方式
                if '>=' in line:
                    pkg_name = line.split('>=')[0].strip()
                    version_spec = '>=' + line.split('>=')[1].strip()
                elif '==' in line:
                    pkg_name = line.split('==')[0].strip()
                    version_spec = '==' + line.split('==')[1].strip()
                else:
                    pkg_name = line.strip()
                    version_spec = None
                
                packages.append((pkg_name, version_spec))
        return packages
    except FileNotFoundError:
        print(f"❌ 找不到 {filename} 文件")
        return []

def check_dependencies():
    """檢查所有依賴"""
    print("=" * 70)
    print("🔍 Deep Video Translation - 依賴檢查")
    print("=" * 70)
    
    # 獲取已安裝套件
    installed = get_installed_packages()
    print(f"\n📦 已安裝套件數量: {len(installed)}")
    
    # 解析 requirements.txt
    requirements = parse_requirements()
    print(f"📋 requirements.txt 中的套件數量: {len(requirements)}")
    
    # 檢查每個套件
    print("\n" + "=" * 70)
    print("📊 套件狀態檢查")
    print("=" * 70)
    
    missing = []
    installed_ok = []
    version_mismatch = []
    
    for pkg_name, version_spec in requirements:
        pkg_lower = pkg_name.lower()
        
        if pkg_lower in installed:
            installed_version = installed[pkg_lower]
            
            if version_spec and '==' in version_spec:
                required_version = version_spec.split('==')[1]
                if installed_version == required_version:
                    installed_ok.append((pkg_name, installed_version))
                    print(f"✅ {pkg_name:30s} {installed_version}")
                else:
                    version_mismatch.append((pkg_name, required_version, installed_version))
                    print(f"⚠️  {pkg_name:30s} {installed_version} (需要 {required_version})")
            else:
                installed_ok.append((pkg_name, installed_version))
                print(f"✅ {pkg_name:30s} {installed_version}")
        else:
            missing.append(pkg_name)
            print(f"❌ {pkg_name:30s} 未安裝")
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 檢查結果總結")
    print("=" * 70)
    print(f"✅ 正確安裝: {len(installed_ok)} 個套件")
    print(f"⚠️  版本不符: {len(version_mismatch)} 個套件")
    print(f"❌ 缺少安裝: {len(missing)} 個套件")
    
    if version_mismatch:
        print("\n⚠️  版本不符的套件:")
        for pkg, required, installed in version_mismatch:
            print(f"   • {pkg}: 已安裝 {installed}，需要 {required}")
    
    if missing:
        print("\n❌ 缺少的套件:")
        for pkg in missing:
            print(f"   • {pkg}")
        print("\n💡 安裝缺少的套件:")
        print("   pip install -r requirements.txt")
    
    # 檢查關鍵功能模組
    print("\n" + "=" * 70)
    print("🔍 關鍵功能模組檢查")
    print("=" * 70)
    
    critical_modules = {
        'cv2': 'OpenCV (影像處理)',
        'easyocr': 'EasyOCR (文字識別)',
        'torch': 'PyTorch (深度學習)',
        'flask': 'Flask (Web框架)',
        'imagehash': 'ImageHash (場景偵測)',
        'PIL': 'Pillow (圖像處理)',
        'numpy': 'NumPy (數值計算)',
        'librosa': 'Librosa (音訊處理)',
        'TTS': 'Coqui-TTS (語音合成)',
    }
    
    all_critical_ok = True
    for module, description in critical_modules.items():
        try:
            importlib.import_module(module)
            print(f"✅ {description:30s} ({module})")
        except ImportError:
            print(f"❌ {description:30s} ({module}) - 導入失敗")
            all_critical_ok = False
    
    # 最終結果
    print("\n" + "=" * 70)
    if not missing and not version_mismatch and all_critical_ok:
        print("🎉 所有依賴檢查通過！專案可以正常運行")
        print("=" * 70)
        print("\n✨ 下一步:")
        print("   1. 設定環境變數: cp .env.example .env")
        print("   2. 編輯 .env 填入 API 金鑰和 SMTP 設定")
        print("   3. 確保字體文件存在於 app/ 目錄")
        print("   4. 確保已安裝 FFmpeg: brew install ffmpeg (Mac)")
        print("   5. 啟動應用: python app/main.py")
        return 0
    else:
        print("⚠️  發現問題，請解決後重試")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(check_dependencies())
