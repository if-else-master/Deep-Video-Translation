"""
影片合併診斷腳本
檢查段落文件是否存在，並測試合併邏輯
"""

import os
import sys
import json

def check_segments():
    """檢查所有段落文件"""
    print("=" * 70)
    print("🔍 影片段落合併診斷")
    print("=" * 70)
    
    # 檢查段落目錄
    face_dir = "temp/faceai"
    ppt_dir = "temp/pptai"
    
    print(f"\n📁 人臉段落目錄: {face_dir}")
    if os.path.exists(face_dir):
        face_files = [f for f in os.listdir(face_dir) if f.endswith('.mp4')]
        print(f"   找到 {len(face_files)} 個 MP4 文件")
        for f in sorted(face_files):
            size = os.path.getsize(os.path.join(face_dir, f)) / (1024 * 1024)
            print(f"   - {f} ({size:.2f} MB)")
    else:
        print(f"   ⚠️ 目錄不存在")
    
    print(f"\n📁 簡報段落目錄: {ppt_dir}")
    if os.path.exists(ppt_dir):
        ppt_files = [f for f in os.listdir(ppt_dir) if f.endswith('.mp4')]
        print(f"   找到 {len(ppt_files)} 個 MP4 文件")
        for f in sorted(ppt_files):
            size = os.path.getsize(os.path.join(ppt_dir, f)) / (1024 * 1024)
            processed = "✅ 已處理" if "_processed" in f else "⚪ 原始"
            print(f"   {processed} {f} ({size:.2f} MB)")
    else:
        print(f"   ⚠️ 目錄不存在")
    
    # 檢查段落信息文件
    print(f"\n📋 段落信息檢查")
    segments_file = "temp/segments_info.json"
    if os.path.exists(segments_file):
        try:
            with open(segments_file, 'r', encoding='utf-8') as f:
                segments_info = json.load(f)
            
            print(f"   找到 {len(segments_info)} 個段落信息:")
            for i, seg in enumerate(segments_info):
                seg_type = seg.get('type', 'unknown')
                start = seg.get('start_frame', 0)
                end = seg.get('end_frame', 0)
                print(f"   {i+1}. {seg_type:8s} 段落 (幀 {start} - {end})")
        except Exception as e:
            print(f"   ❌ 讀取失敗: {e}")
    else:
        print(f"   ⚠️ 段落信息文件不存在: {segments_file}")
    
    # 模擬合併邏輯
    print(f"\n🔄 模擬段落合併順序")
    if os.path.exists(segments_file):
        with open(segments_file, 'r', encoding='utf-8') as f:
            segments_info = json.load(f)
        
        # 獲取所有處理後的文件
        face_files = []
        ppt_files = []
        
        if os.path.exists(face_dir):
            face_files = sorted([os.path.join(face_dir, f) for f in os.listdir(face_dir) 
                               if f.endswith('.mp4') and not '_audio' in f and not '_temp' in f])
        
        if os.path.exists(ppt_dir):
            ppt_files = sorted([os.path.join(ppt_dir, f) for f in os.listdir(ppt_dir) 
                              if f.endswith('.mp4') and not '_audio' in f and not '_temp' in f])
        
        # 創建映射
        face_map = {}
        ppt_map = {}
        
        for i, f in enumerate(face_files, 1):
            face_map[i] = f
        
        for i, f in enumerate(ppt_files, 1):
            if '_processed' in f:
                ppt_map[i] = f
        
        # 如果沒有找到 _processed 文件，使用原始文件
        if not ppt_map:
            for i, f in enumerate(ppt_files, 1):
                if f.endswith('.mp4') and '_processed' not in f and '_audio' not in f:
                    ppt_map[i] = f
        
        print(f"   人臉段落映射: {len(face_map)} 個")
        for idx, path in face_map.items():
            print(f"     {idx}: {os.path.basename(path)}")
        
        print(f"\n   簡報段落映射: {len(ppt_map)} 個")
        for idx, path in ppt_map.items():
            print(f"     {idx}: {os.path.basename(path)}")
        
        # 按照段落信息順序合併
        print(f"\n   合併順序:")
        face_counter = 1
        ppt_counter = 1
        merge_list = []
        
        for i, seg in enumerate(segments_info):
            seg_type = seg.get('type', 'unknown')
            if seg_type == 'face' and face_counter in face_map:
                path = face_map[face_counter]
                # 優先使用 _processed 版本
                processed_path = path.replace('.mp4', '_processed.mp4')
                if os.path.exists(processed_path):
                    path = processed_path
                    status = "已處理"
                else:
                    status = "原始"
                merge_list.append(path)
                print(f"     {i+1}. 👤 人臉段落 {face_counter} ({status}): {os.path.basename(path)}")
                face_counter += 1
            elif seg_type == 'slide' and ppt_counter in ppt_map:
                path = ppt_map[ppt_counter]
                # 優先使用 _processed 版本
                processed_path = path.replace('.mp4', '_processed.mp4')
                if os.path.exists(processed_path):
                    path = processed_path
                    status = "已處理"
                else:
                    status = "原始"
                merge_list.append(path)
                print(f"     {i+1}. 📊 簡報段落 {ppt_counter} ({status}): {os.path.basename(path)}")
                ppt_counter += 1
            else:
                print(f"     {i+1}. ⚠️  跳過 {seg_type} 段落 (無對應文件)")
        
        # 顯示最終合併列表
        print(f"\n✅ 最終合併列表: {len(merge_list)} 個文件")
        total_size = 0
        for i, path in enumerate(merge_list, 1):
            if os.path.exists(path):
                size = os.path.getsize(path) / (1024 * 1024)
                total_size += size
                print(f"   {i}. {os.path.basename(path):40s} ({size:.2f} MB)")
            else:
                print(f"   {i}. ❌ {path} (文件不存在)")
        
        print(f"\n📊 總大小: {total_size:.2f} MB")
        
        if len(merge_list) > 0:
            print("\n💡 建議:")
            print("   如果合併後的影片缺少簡報翻譯部分，請檢查:")
            print("   1. 簡報段落是否有 _processed.mp4 文件")
            print("   2. segments_info.json 中是否包含簡報段落")
            print("   3. 合併列表是否包含所有簡報段落")
    else:
        print("   ⚠️ 無法模擬，缺少段落信息文件")
    
    # 檢查輸出文件
    print(f"\n📤 輸出文件檢查")
    output_dir = "output_videos"
    if os.path.exists(output_dir):
        output_files = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
        if output_files:
            print(f"   找到 {len(output_files)} 個輸出文件:")
            for f in sorted(output_files):
                path = os.path.join(output_dir, f)
                size = os.path.getsize(path) / (1024 * 1024)
                print(f"   - {f} ({size:.2f} MB)")
        else:
            print(f"   ⚠️ 沒有找到輸出文件")
    else:
        print(f"   ⚠️ 輸出目錄不存在")
    
    print("\n" + "=" * 70)
    print("診斷完成")
    print("=" * 70)

if __name__ == "__main__":
    try:
        check_segments()
    except Exception as e:
        print(f"❌ 診斷過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
