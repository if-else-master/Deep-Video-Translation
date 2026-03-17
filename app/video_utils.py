"""
影片工具函數
"""
import subprocess
import json

def get_video_duration(video_path):
    """
    獲取影片時長（秒）
    
    Args:
        video_path: 影片檔案路徑
        
    Returns:
        時長（秒），失敗返回 None
    """
    try:
        # 使用 ffprobe 獲取影片資訊
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # 嘗試從 format 獲取時長
            if 'format' in data and 'duration' in data['format']:
                return float(data['format']['duration'])
            
            # 嘗試從視頻流獲取時長
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video' and 'duration' in stream:
                        return float(stream['duration'])
        
        return None
        
    except Exception as e:
        print(f"❌ 獲取影片時長失敗: {str(e)}")
        return None


def format_duration(seconds):
    """
    格式化時長為可讀字串
    
    Args:
        seconds: 秒數
        
    Returns:
        格式化的字串，如 "1:30" 或 "2:15:30"
    """
    if seconds is None:
        return "未知"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"
