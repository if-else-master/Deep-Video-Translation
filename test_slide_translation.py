"""
簡報翻譯功能測試腳本
"""
import os
import sys

def test_imports():
    """測試所有必要的導入"""
    print("=" * 60)
    print("🧪 測試模組導入")
    print("=" * 60)
    
    modules = {
        'cv2': 'OpenCV',
        'easyocr': 'EasyOCR',
        'numpy': 'NumPy',
        'imagehash': 'ImageHash',
        'PIL': 'Pillow',
        'requests': 'Requests'
    }
    
    failed = []
    for module, name in modules.items():
        try:
            __import__(module)
            print(f"✅ {name} ({module})")
        except ImportError as e:
            print(f"❌ {name} ({module}) - {e}")
            failed.append(module)
    
    if failed:
        print(f"\n❌ 缺少模組: {', '.join(failed)}")
        print("請執行: pip install -r requirements.txt")
        return False
    
    print("\n✅ 所有模組導入成功")
    return True

def test_fonts():
    """測試字體文件"""
    print("\n" + "=" * 60)
    print("🔍 檢查字體文件")
    print("=" * 60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(current_dir, 'app')
    
    fonts = {
        'Japanese': 'NotoSansCJKjp-Regular.otf',
        'Chinese': 'NotoSansTC-Regular.ttf'
    }
    
    all_found = True
    for lang, font_name in fonts.items():
        font_path = os.path.join(app_dir, font_name)
        if os.path.exists(font_path):
            size = os.path.getsize(font_path)
            print(f"✅ {lang} 字體: {font_name} ({size:,} bytes)")
        else:
            print(f"❌ {lang} 字體未找到: {font_path}")
            all_found = False
    
    if all_found:
        print("\n✅ 所有字體文件存在")
    else:
        print("\n⚠️ 部分字體文件缺失，將使用系統字體")
    
    return all_found

def test_easyocr():
    """測試 EasyOCR 功能"""
    print("\n" + "=" * 60)
    print("🔍 測試 EasyOCR 功能")
    print("=" * 60)
    
    try:
        import easyocr
        print("✅ EasyOCR 已安裝")
        
        print("\n正在初始化 EasyOCR Reader（可能需要下載模型）...")
        print("支援的語言組合: ['ch_tra', 'en']")
        
        try:
            reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
            print("✅ EasyOCR Reader 初始化成功")
            print(f"   語言: 繁體中文 (ch_tra), 英文 (en)")
            print(f"   GPU: 關閉")
            return True
        except Exception as e:
            print(f"❌ EasyOCR Reader 初始化失敗: {e}")
            print("\n💡 可能的解決方案:")
            print("   1. 檢查網路連線（首次使用需下載模型）")
            print("   2. 確保有足夠的磁碟空間")
            print("   3. 嘗試手動下載模型：")
            print("      python -m easyocr.download --lang ch_tra en")
            return False
            
    except ImportError:
        print("❌ EasyOCR 未安裝")
        print("請執行: pip install easyocr")
        return False

def test_opencv():
    """測試 OpenCV 功能"""
    print("\n" + "=" * 60)
    print("🔍 測試 OpenCV 功能")
    print("=" * 60)
    
    try:
        import cv2
        import numpy as np
        
        print(f"✅ OpenCV 版本: {cv2.__version__}")
        
        # 測試基本功能
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        print("✅ 顏色轉換功能正常")
        
        # 測試 Inpainting
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[25:75, 25:75] = 255
        inpainted = cv2.inpaint(test_img, mask, 7, cv2.INPAINT_TELEA)
        print("✅ Inpainting 功能正常")
        
        return True
    except Exception as e:
        print(f"❌ OpenCV 測試失敗: {e}")
        return False

def test_processor_class():
    """測試 VideoProcessor 類別"""
    print("\n" + "=" * 60)
    print("🔍 測試 VideoProcessor 類別")
    print("=" * 60)
    
    try:
        # 添加 app 目錄到路徑
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.join(current_dir, 'app')
        sys.path.insert(0, app_dir)
        
        from video_processor import VideoProcessor
        print("✅ VideoProcessor 導入成功")
        
        processor = VideoProcessor()
        print("✅ VideoProcessor 實例化成功")
        
        # 檢查關鍵方法
        methods = [
            'process_slide_image',
            'translate_frame_text',
            'remove_text_with_inpainting',
            'draw_translated_text',
            'translate'
        ]
        
        for method in methods:
            if hasattr(processor, method):
                print(f"✅ 方法存在: {method}()")
            else:
                print(f"❌ 方法缺失: {method}()")
        
        # 檢查字體設置
        if hasattr(processor, 'font_paths'):
            print(f"\n字體設置:")
            for lang, path in processor.font_paths.items():
                exists = "✅" if os.path.exists(path) else "❌"
                print(f"  {exists} {lang}: {path}")
        
        return True
    except Exception as e:
        print(f"❌ VideoProcessor 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """測試其他依賴"""
    print("\n" + "=" * 60)
    print("🔍 檢查其他依賴文件")
    print("=" * 60)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    files_to_check = {
        'app/txtvoice.py': '語音轉文字模組',
        'app/xttsv.py': 'XTTS 語音合成',
        'app/f5ttsv.py': 'F5-TTS 語音合成',
        'app/video_processor.py': '影片處理器'
    }
    
    for file_path, description in files_to_check.items():
        full_path = os.path.join(current_dir, file_path)
        if os.path.exists(full_path):
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description} 缺失: {file_path}")

def main():
    """主測試函數"""
    print("\n" + "=" * 60)
    print("🚀 Deep Video Translation - 簡報翻譯功能診斷")
    print("=" * 60 + "\n")
    
    results = {
        '模組導入': test_imports(),
        '字體文件': test_fonts(),
        'OpenCV': test_opencv(),
        'EasyOCR': test_easyocr(),
        'VideoProcessor': test_processor_class()
    }
    
    test_dependencies()
    
    # 總結
    print("\n" + "=" * 60)
    print("📊 診斷結果總結")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 60)
        print("🎉 所有測試通過！簡報翻譯功能應該可以正常運作")
        print("=" * 60)
        print("\n💡 如果仍然有問題，請提供以下資訊：")
        print("   1. 完整的錯誤訊息")
        print("   2. 正在處理的影片類型")
        print("   3. 選擇的語言設定")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ 部分測試失敗，請解決上述問題後重試")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
