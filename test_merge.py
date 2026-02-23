"""
測試影片合併功能
創建模擬的段落信息文件並測試合併邏輯
"""

import os
import json
import sys

def create_test_segments_info():
    """創建測試用的段落信息文件"""
    print("=" * 70)
    print("🧪 創建測試段落信息")
    print("=" * 70)
    
    # 檢查現有段落
    face_dir = "temp/faceai"
    ppt_dir = "temp/pptai"
    
    segments_info = []
    
    # 檢查人臉段落
    if os.path.exists(face_dir):
        face_files = sorted([f for f in os.listdir(face_dir) 
                           if f.endswith('.mp4') and not '_processed' in f 
                           and not '_audio' in f and not '_temp' in f])
        print(f"\n找到 {len(face_files)} 個人臉段落:")
        for i, f in enumerate(face_files, 1):
            print(f"  {i}. {f}")
            segments_info.append({
                'type': 'face',
                'start_frame': (i-1) * 1000,
                'end_frame': i * 1000 - 1,
                'frames': list(range((i-1) * 1000, i * 1000))
            })
    
    # 檢查簡報段落
    if os.path.exists(ppt_dir):
        ppt_files = sorted([f for f in os.listdir(ppt_dir) 
                          if f.endswith('.mp4') and not '_processed' in f 
                          and not '_audio' in f and not '_temp' in f])
        print(f"\n找到 {len(ppt_files)} 個簡報段落:")
        for i, f in enumerate(ppt_files, 1):
            print(f"  {i}. {f}")
            segments_info.append({
                'type': 'slide',
                'start_frame': len(segments_info) * 1000,
                'end_frame': (len(segments_info) + 1) * 1000 - 1,
                'frames': list(range(len(segments_info) * 1000, (len(segments_info) + 1) * 1000))
            })
    
    # 保存段落信息
    segments_info_path = "temp/segments_info.json"
    os.makedirs(os.path.dirname(segments_info_path), exist_ok=True)
    
    try:
        with open(segments_info_path, 'w', encoding='utf-8') as f:
            json.dump(segments_info, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 段落信息已保存: {segments_info_path}")
        print(f"   總共 {len(segments_info)} 個段落")
        
        # 顯示段落順序
        print(f"\n📋 段落順序:")
        for i, seg in enumerate(segments_info, 1):
            seg_type = seg['type']
            emoji = "👤" if seg_type == "face" else "📊"
            print(f"   {i}. {emoji} {seg_type} 段落 (幀 {seg['start_frame']}-{seg['end_frame']})")
        
        return True
    except Exception as e:
        print(f"\n❌ 保存失敗: {e}")
        return False

def test_merge_logic():
    """測試合併邏輯"""
    print("\n" + "=" * 70)
    print("🧪 測試合併邏輯")
    print("=" * 70)
    
    segments_info_path = "temp/segments_info.json"
    if not os.path.exists(segments_info_path):
        print("❌ 段落信息文件不存在")
        return False
    
    # 讀取段落信息
    with open(segments_info_path, 'r', encoding='utf-8') as f:
        segments_info = json.load(f)
    
    print(f"\n讀取到 {len(segments_info)} 個段落")
    
    # 檢查文件映射
    face_dir = "temp/faceai"
    ppt_dir = "temp/pptai"
    
    face_files = []
    ppt_files = []
    
    if os.path.exists(face_dir):
        face_files = sorted([os.path.join(face_dir, f) for f in os.listdir(face_dir) 
                           if f.endswith('_processed.mp4')])
        if not face_files:
            face_files = sorted([os.path.join(face_dir, f) for f in os.listdir(face_dir) 
                               if f.endswith('.mp4') and not '_audio' in f and not '_temp' in f])
    
    if os.path.exists(ppt_dir):
        ppt_files = sorted([os.path.join(ppt_dir, f) for f in os.listdir(ppt_dir) 
                          if f.endswith('_processed.mp4')])
        if not ppt_files:
            ppt_files = sorted([os.path.join(ppt_dir, f) for f in os.listdir(ppt_dir) 
                              if f.endswith('.mp4') and not '_audio' in f and not '_temp' in f])
    
    print(f"\n文件映射:")
    print(f"  人臉段落: {len(face_files)} 個")
    for i, f in enumerate(face_files, 1):
        print(f"    {i}. {os.path.basename(f)}")
    
    print(f"  簡報段落: {len(ppt_files)} 個")
    for i, f in enumerate(ppt_files, 1):
        print(f"    {i}. {os.path.basename(f)}")
    
    # 構建映射
    face_map = {i: f for i, f in enumerate(face_files, 1)}
    ppt_map = {i: f for i, f in enumerate(ppt_files, 1)}
    
    # 按順序排列
    ordered_segments = []
    face_counter = 1
    ppt_counter = 1
    
    print(f"\n合併順序:")
    for i, seg in enumerate(segments_info, 1):
        seg_type = seg['type']
        if seg_type == 'face' and face_counter in face_map:
            path = face_map[face_counter]
            ordered_segments.append(path)
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  {i}. 👤 人臉段落 {face_counter}: {os.path.basename(path)} ({size:.2f} MB)")
            face_counter += 1
        elif seg_type == 'slide' and ppt_counter in ppt_map:
            path = ppt_map[ppt_counter]
            ordered_segments.append(path)
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  {i}. 📊 簡報段落 {ppt_counter}: {os.path.basename(path)} ({size:.2f} MB)")
            ppt_counter += 1
        else:
            print(f"  {i}. ⚠️  跳過段落: {seg_type} (無對應文件)")
    
    print(f"\n✅ 最終合併列表: {len(ordered_segments)} 個文件")
    total_size = sum(os.path.getsize(p) / (1024 * 1024) for p in ordered_segments)
    print(f"📊 預計輸出大小: {total_size:.2f} MB")
    
    if len(ordered_segments) == len(segments_info):
        print("\n✅ 所有段落都能正確映射")
        return True
    else:
        print(f"\n⚠️  警告: 段落信息數量 ({len(segments_info)}) 與映射文件數量 ({len(ordered_segments)}) 不符")
        return False

if __name__ == "__main__":
    print("\n🚀 影片合併功能測試\n")
    
    # 步驟 1: 創建測試段落信息
    if not create_test_segments_info():
        sys.exit(1)
    
    # 步驟 2: 測試合併邏輯
    if not test_merge_logic():
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🎉 測試完成！")
    print("=" * 70)
    print("\n💡 下一步:")
    print("   1. 使用 Web 界面上傳影片進行測試")
    print("   2. 確認輸出影片包含所有段落（人臉 + 簡報）")
    print("   3. 檢查合併後的影片長度和大小是否正確\n")
