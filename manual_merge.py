#!/usr/bin/env python3
"""手动合并 face 和 slide 的 processed 视频"""
import subprocess
import os
import sys

def merge_face_and_slide(face_path, slide_path, output_path):
    """合并人臉和投影片處理後的視頻（按時間軸順序）"""
    
    if not os.path.exists(face_path):
        print(f"❌ 人臉視頻不存在: {face_path}")
        return False
    
    if not os.path.exists(slide_path):
        print(f"❌ 投影片視頻不存在: {slide_path}")
        return False
    
    print(f"📂 人臉視頻: {face_path}")
    print(f"📂 投影片視頻: {slide_path}")
    print(f"📂 輸出路徑: {output_path}")
    
    # 檢查視頻信息
    print("\n🔍 檢查視頻格式...")
    for path, label in [(face_path, "人臉"), (slide_path, "簡報")]:
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,duration -of csv=p=0 "{path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            info = result.stdout.strip().split(',')
            if len(info) >= 3:
                duration = info[3] if len(info) > 3 else "N/A"
                print(f"  {label}: {info[2]} 編碼, {info[0]}x{info[1]}, {duration}秒")
    
    # 創建輸出目錄
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    print("\n🔄 開始合併視頻...")
    print("  策略: 統一格式後按時間軸合併 (人臉 → 簡報)")
    
    # 方法1: 先統一格式再用 concat demuxer (最可靠)
    print("\n  📝 方法1: 先統一格式再用 concat demuxer")
    temp_face = "temp/face_normalized.mp4"
    temp_slide = "temp/slide_normalized.mp4"
    
    try:
        # 統一人臉視頻格式
        print("    🔧 統一人臉視頻格式 (1280x720, h264, 30fps)...")
        cmd_face = f'ffmpeg -y -i "{face_path}" -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -ar 44100 "{temp_face}"'
        result_face = subprocess.run(cmd_face, shell=True, capture_output=True, text=True)
        
        if result_face.returncode != 0:
            print(f"       ⚠️ 失敗")
            raise Exception("人臉視頻格式統一失敗")
        print("       ✅ 完成")
        
        # 統一簡報視頻格式
        print("    🔧 統一簡報視頻格式 (1280x720, h264, 30fps)...")
        cmd_slide = f'ffmpeg -y -i "{slide_path}" -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k -ar 44100 "{temp_slide}"'
        result_slide = subprocess.run(cmd_slide, shell=True, capture_output=True, text=True)
        
        if result_slide.returncode != 0:
            print(f"       ⚠️ 失敗")
            raise Exception("簡報視頻格式統一失敗")
        print("       ✅ 完成")
        
        # 創建合併列表
        list_file = "temp/normalized_merge_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            f.write(f"file '{os.path.abspath(temp_face)}'\n")
            f.write(f"file '{os.path.abspath(temp_slide)}'\n")
        
        # 合併 (使用 copy 因為格式已經統一)
        print("    🔧 合併統一格式的視頻...")
        cmd_merge = f'ffmpeg -y -f concat -safe 0 -i "{list_file}" -c copy "{output_path}"'
        result_merge = subprocess.run(cmd_merge, shell=True, capture_output=True, text=True)
        
        if result_merge.returncode == 0:
            print("  ✅ 方法1合併成功！")
            return True
        else:
            print(f"  ⚠️ 合併失敗")
            raise Exception("合併失敗")
            
    except Exception as e:
        print(f"  ⚠️ 方法1失敗: {e}")
    finally:
        # 清理臨時文件
        for temp_file in [temp_face, temp_slide]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"    🗑️  已清理: {temp_file}")
                except:
                    pass
    
    # 方法2: 使用 filter_complex 一次性處理
    print("\n  📝 方法2: filter_complex 一次性統一並合併")
    command2 = f'''ffmpeg -y -i "{face_path}" -i "{slide_path}" -filter_complex "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v0];[1:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v1];[0:a]aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100[a0];[1:a]aresample=44100,aformat=sample_fmts=fltp:sample_rates=44100[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 192k "{output_path}"'''
    result2 = subprocess.run(command2, shell=True, capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("  ✅ 方法2合併成功！")
        return True
    else:
        print(f"  ⚠️ 方法2失敗")
    
    print("\n❌ 所有合併方法都失敗了")
    return False


if __name__ == "__main__":
    # 預設路徑
    face_path = "temp/faceai/01_processed.mp4"
    slide_path = "temp/pptai/01_processed.mp4"
    output_path = "audio_files/merged_output.mp4"
    
    # 如果提供了命令行參數
    if len(sys.argv) >= 4:
        face_path = sys.argv[1]
        slide_path = sys.argv[2]
        output_path = sys.argv[3]
    elif len(sys.argv) == 2:
        output_path = sys.argv[1]
    
    print("=" * 60)
    print("🎬 手動合併 Face 和 Slide 視頻")
    print("=" * 60)
    
    success = merge_face_and_slide(face_path, slide_path, output_path)
    
    if success:
        print("\n✅ 合併完成！")
        print(f"📁 輸出文件: {output_path}")
        
        # 檢查文件大小
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"📊 文件大小: {size_mb:.2f} MB")
    else:
        print("\n❌ 合併失敗")
        sys.exit(1)
