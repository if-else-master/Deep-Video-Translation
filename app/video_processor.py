"""
視頻處理核心邏輯
從原始main.py移植的完整處理功能
"""
import os
import sys
import cv2
import easyocr
import numpy as np
import imagehash
from PIL import Image, ImageDraw, ImageFont
import requests 
import re
import subprocess
from typing import List, Dict, Tuple, Optional, Callable

# 添加 Wav2Lip 目錄到 Python 路徑
wav2lip_path = os.path.join(os.path.dirname(__file__), 'Wav2Lip')
sys.path.append(wav2lip_path)

from txtvoice import voice
from xttsv import xttsv

# 動態導入 Wav2Lip，確保路徑正確
def get_wav2lip_inference():
    try:
        # 切換到 Wav2Lip 目錄再導入
        original_cwd = os.getcwd()
        wav2lip_dir = os.path.join(os.path.dirname(__file__), 'Wav2Lip')
        os.chdir(wav2lip_dir)
        
        # 添加到 sys.path
        if wav2lip_dir not in sys.path:
            sys.path.insert(0, wav2lip_dir)
            
        from inference import run_inference
        os.chdir(original_cwd)
        return run_inference
    except Exception as e:
        print(f"⚠️ Wav2Lip 導入失敗: {e}")
        os.chdir(original_cwd)
        return None


class VideoProcessor:
    """完整的視頻處理類，包含所有原有功能"""
    
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self.progress_callback = progress_callback
        self.setup_fonts()
        self.ensure_basic_directories()
    
    def update_progress(self, message: str, progress: int = None):
        """更新進度回調"""
        if self.progress_callback:
            self.progress_callback(message, progress)
        print(f"🔄 {message} {f'({progress}%)' if progress is not None else ''}")

    def setup_fonts(self):
        """設置字體路徑，使用本地的 Noto 字體"""
        current_dir = os.path.dirname(__file__)
        
        # 檢查本地字體文件
        self.font_paths = {
            "Japanese": os.path.join(current_dir, "NotoSansCJKjp-Regular.otf"),
            "English": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "Chinese": os.path.join(current_dir, "NotoSansTC-Regular.ttf")
        }
        
        # 檢查字體文件是否存在
        for lang, font_path in self.font_paths.items():
            if os.path.exists(font_path):
                print(f"✅ {lang} 字體已找到: {font_path}")
            else:
                print(f"❌ {lang} 字體未找到: {font_path}")
                # 使用系統字體作為備用
                self.font_paths[lang] = self.get_system_font()

    def get_system_font(self):
        """獲取系統可用字體"""
        possible_fonts = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS 中文
            "/System/Library/Fonts/Arial.ttf",     # macOS 英文
            "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS 日文
            "C:/Windows/Fonts/msyh.ttc",           # Windows
            "C:/Windows/Fonts/arial.ttf",          # Windows
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
        ]
        
        for font_path in possible_fonts:
            if os.path.exists(font_path):
                return font_path
        return None

    def detect_faces_in_frame(self, frame):
        """檢測幀中是否有人臉"""
        try:
            # 使用 OpenCV 的人臉檢測器
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 使用多種參數嘗試檢測
            # 第一次嘗試：標準參數
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                return True
                
            # 第二次嘗試：更寬鬆的參數
            faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
            if len(faces) > 0:
                return True
                
            # 第三次嘗試：非常寬鬆的參數
            faces = face_cascade.detectMultiScale(gray, 1.3, 2, minSize=(20, 20))
            return len(faces) > 0
            
        except Exception as e:
            print(f"人臉檢測錯誤: {e}")
            # 如果人臉檢測失敗，假設沒有人臉
            return False

    def is_slide_frame(self, frame):
        """判斷是否為簡報頁面（沒有人臉且有文字內容）"""
        # 檢查是否有人臉
        has_faces = self.detect_faces_in_frame(frame)
        
        if has_faces:
            return False  # 有人臉，不是簡報
        
        # 使用簡單的方法檢測是否有文字內容
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 計算圖像的對比度和邊緣
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size
        
        # 如果邊緣比例在合理範圍內，可能是簡報
        # 太少邊緣可能是空白，太多邊緣可能是雜亂背景
        return 0.01 < edge_ratio < 0.3

    def translate_with_gemini(self, text, target_lang="Japanese", api_key=None):
        """使用 Gemini API 翻譯文字"""
        if not api_key:
            return text
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        lang_prompts = {
            "English": "請將以下文字翻譯成英文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "Chinese": "請將以下文字翻譯成中文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "German": "請將以下文字翻譯成德文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "French": "請將以下文字翻譯成法文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "Hindi": "請將以下文字翻譯成印地文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "Korean": "請將以下文字翻譯成韓文，只輸出翻譯結果，不要有任何解釋或額外文字："
        }
        
        prompt = lang_prompts.get(target_lang, lang_prompts["English"]) + text
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                translated = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                clean_result = re.sub(r'^[^a-zA-Z\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF]+', '', translated).strip()
                return clean_result
            else:
                print("翻譯失敗:", r.text)
                return text
        except Exception as e:
            print(f"翻譯錯誤: {e}")
            return text

    def remove_text_with_inpainting(self, img, boxes):
        """根據 OCR 回傳的 boxes 四點座標，製作 mask 並 inpaint"""
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        for box in boxes:
            pts = np.array(box, dtype=np.int32)
            cv2.fillPoly(mask, [pts], 255)
        return cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)

    def draw_translated_text(self, pil_img, boxes, texts, font_path):
        """在 PIL Image 上貼回翻譯後的文本"""
        draw = ImageDraw.Draw(pil_img)
        
        print(f"🎯 正在使用字體: {font_path}")
        print(f"📝 需要繪製 {len(texts)} 個文字區塊")
        
        for i, (box, txt) in enumerate(zip(boxes, texts)):
            print(f"  處理文字 {i+1}: {txt}")
            
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, y0 = min(xs), min(ys)
            x1, y1 = max(xs), max(ys)
            box_w, box_h = x1 - x0, y1 - y0

            # 調整字型大小
            font_size = max(int(box_h * 0.6), 16)  # 增加最小字型大小
            
            try:
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    print(f"  ✅ 成功載入字體: {font_path}, 大小: {font_size}")
                else:
                    font = ImageFont.load_default()
                    print(f"  ⚠️ 使用預設字體")
            except Exception as e:
                print(f"  ❌ 字體載入失敗: {e}")
                try:
                    font = ImageFont.load_default()
                except:
                    continue

            # 計算文字換行
            max_chars = max(int(box_w / (font_size * 0.5)), 1)  # 調整字符寬度估算
            lines = []
            
            # 更智能的換行處理
            words = txt.split()
            if len(words) > 1:
                # 如果有多個詞，按詞換行
                current_line = ""
                for word in words:
                    if len(current_line + word) <= max_chars:
                        current_line += word + " "
                    else:
                        if current_line:
                            lines.append(current_line.strip())
                        current_line = word + " "
                if current_line:
                    lines.append(current_line.strip())
            else:
                # 單個長詞或句子，按字符換行
                lines = [txt[i:i+max_chars] for i in range(0, len(txt), max_chars)]

            # 繪製文字
            y = y0
            line_height = font_size + 2  # 增加行間距
            
            for line in lines:
                if y + line_height > y1:  # 檢查是否超出邊界
                    break
                try:
                    # 使用黑色文字，白色背景
                    draw.text((x0, y), line, font=font, fill=(0, 0, 0))
                    print(f"    ✅ 繪製文字: {line}")
                    y += line_height
                except Exception as e:
                    print(f"    ❌ 文字繪製失敗: {e}")
                    continue
                    
        return pil_img

    def analyze_and_segment_video(self, video_path, min_segment_duration=2, hash_threshold=5):
        """分析影片並智能分段，分離人臉和簡報片段"""
        self.update_progress("🔍 開始分析影片內容並進行智能分段...", 5)
        
        # 創建輸出目錄 - 使用絕對路徑確保正確性
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 項目根目錄
        face_dir = os.path.join(base_dir, "temp", "faceai")
        ppt_dir = os.path.join(base_dir, "temp", "pptai")
        os.makedirs(face_dir, exist_ok=True)
        os.makedirs(ppt_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        min_frames = int(fps * min_segment_duration)
        
        # 第一步：分析整個影片的內容類型
        self.update_progress("📊 正在分析影片內容類型...", 10)
        segments = []
        current_segment = None
        frame_count = 0
        prev_hash = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 檢測內容類型
            has_faces = self.detect_faces_in_frame(frame)
            is_slide = self.is_slide_frame(frame)
            
            # 決定段落類型
            if has_faces:
                segment_type = "face"
            elif is_slide:
                segment_type = "slide"
            else:
                segment_type = "unknown"
            
            # 檢查是否需要開始新段落
            if current_segment is None:
                current_segment = {
                    'type': segment_type,
                    'start_frame': frame_count,
                    'end_frame': frame_count,
                    'frames': [frame_count]
                }
            elif current_segment['type'] != segment_type or self.should_split_segment(frame, prev_hash, hash_threshold):
                # 結束當前段落（如果足夠長）
                if len(current_segment['frames']) >= min_frames:
                    current_segment['end_frame'] = frame_count - 1
                    segments.append(current_segment)
                
                # 開始新段落
                current_segment = {
                    'type': segment_type,
                    'start_frame': frame_count,
                    'end_frame': frame_count,
                    'frames': [frame_count]
                }
            else:
                # 繼續當前段落
                current_segment['end_frame'] = frame_count
                current_segment['frames'].append(frame_count)
            
            # 儲存當前幀的hash用於場景切換檢測
            if frame_count % 5 == 0:  # 每5幀檢查一次
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                prev_hash = imagehash.phash(pil_image)
            
            frame_count += 1
            
            # 更新進度
            if frame_count % 100 == 0:
                progress = 10 + int((frame_count / total_frames) * 10)  # 分析階段占10-20%進度
                self.update_progress(f"分析進度: {frame_count}/{total_frames} 幀", progress)
        
        # 添加最後一個段落
        if current_segment and len(current_segment['frames']) >= min_frames:
            segments.append(current_segment)
        
        cap.release()
        
        print(f"📋 分析完成，找到 {len(segments)} 個段落:")
        face_segments = [s for s in segments if s['type'] == 'face']
        slide_segments = [s for s in segments if s['type'] == 'slide']
        print(f"   👤 人臉段落: {len(face_segments)}")
        print(f"   📊 簡報段落: {len(slide_segments)}")
        
        # 第二步：提取並儲存段落
        self.update_progress("✂️ 正在提取影片段落...", 20)
        self.extract_segments(video_path, segments, face_dir, ppt_dir)
        
        return segments

    def should_split_segment(self, current_frame, prev_hash, threshold):
        """判斷是否應該分割段落（基於場景變化）"""
        if prev_hash is None:
            return False
            
        pil_image = Image.fromarray(cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB))
        current_hash = imagehash.phash(pil_image)
        
        return abs(current_hash - prev_hash) > threshold

    def extract_segments(self, video_path, segments, face_dir, ppt_dir):
        """提取並儲存影片段落，每個段落包含完整的音視頻"""
        self.update_progress("✂️ 正在提取影片段落...", 25)
        
        # 獲取視頻信息
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        face_count = 1
        slide_count = 1
        
        for i, segment in enumerate(segments):
            segment_type = segment['type']
            start_frame = segment['start_frame']
            end_frame = segment['end_frame']
            
            if segment_type == 'face':
                filename = f"{face_count:02d}.mp4"
                output_path = os.path.join(face_dir, filename)
                face_count += 1
            elif segment_type == 'slide':
                filename = f"{slide_count:02d}.mp4"
                output_path = os.path.join(ppt_dir, filename)
                slide_count += 1
            else:
                continue  # 跳過未知類型
            
            # 提取段落（包含音視頻）
            self.extract_video_segment(cap, start_frame, end_frame, output_path, fps, width, height, video_path)
            
            print(f"💾 已提取 {segment_type} 段落: {filename} (幀 {start_frame}-{end_frame})")
            
            # 更新進度
            progress = 25 + int((i / len(segments)) * 15)  # 提取階段占25-40%進度
            self.update_progress(f"提取段落: {i+1}/{len(segments)}", progress)
        
        cap.release()
        print(f"✅ 段落提取完成: {face_count-1} 個人臉段落, {slide_count-1} 個簡報段落")

    def extract_video_segment(self, cap, start_frame, end_frame, output_path, fps, width, height, original_video_path):
        """提取單個影片段落，包含音頻和視頻"""
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        self.ensure_directory_exists(output_dir)
        
        # 計算時間戳
        start_time = start_frame / fps
        duration = (end_frame - start_frame + 1) / fps
        
        print(f"  📹 提取段落: {start_time:.2f}s - {start_time + duration:.2f}s (時長: {duration:.2f}s)")
        
        try:
            # 使用 FFmpeg 直接提取包含音頻的視頻段落
            command = f'ffmpeg -y -i "{original_video_path}" -ss {start_time} -t {duration} -c:v libx264 -c:a aac "{output_path}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ 段落提取成功: {output_path}")
            else:
                print(f"  ⚠️ FFmpeg 提取失敗，使用備用方法: {result.stderr}")
                # 備用方法：只提取視頻，然後添加靜音音頻
                self.extract_video_only_segment(cap, start_frame, end_frame, output_path, fps, width, height, duration)
                
        except Exception as e:
            print(f"  ❌ 段落提取失敗: {e}")
            # 備用方法
            self.extract_video_only_segment(cap, start_frame, end_frame, output_path, fps, width, height, duration)

    def extract_video_only_segment(self, cap, start_frame, end_frame, output_path, fps, width, height, duration):
        """備用方法：只提取視頻然後添加靜音音頻"""
        temp_video_path = output_path.replace('.mp4', '_temp_video.mp4')
        
        # 提取視頻部分
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
        
        # 定位到開始幀
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        for frame_num in range(start_frame, end_frame + 1):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        out.release()
        
        # 創建靜音音頻並合成
        try:
            from xttsv import create_silent_audio
            temp_audio_path = output_path.replace('.mp4', '_temp_audio.wav')
            create_silent_audio(duration, temp_audio_path)
            
            # 合成視頻和音頻
            command = f'ffmpeg -y -i "{temp_video_path}" -i "{temp_audio_path}" -c:v copy -c:a aac "{output_path}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 清理臨時文件
                os.remove(temp_video_path)
                os.remove(temp_audio_path)
            else:
                # 如果合成失敗，至少保留視頻
                import shutil
                shutil.move(temp_video_path, output_path)
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                    
        except Exception as e:
            print(f"  ⚠️ 音頻合成失敗，僅保留視頻: {e}")
            import shutil
            shutil.move(temp_video_path, output_path)

    def process_face_segments(self, face_dir, language, api_key):
        """處理人臉段落：音頻提取、翻譯、嘴形同步"""
        self.update_progress("👤 開始處理人臉段落...", 40)
        
        # 確保目錄存在
        self.ensure_directory_exists(face_dir)
        
        # 只處理原始段落文件，不處理已經處理過的文件
        face_files = sorted([f for f in os.listdir(face_dir) 
                           if f.endswith('.mp4') and not f.endswith('_processed.mp4')])
        processed_segments = []
        
        for i, filename in enumerate(face_files):
            self.update_progress(f"🎭 處理人臉段落 {filename}...", 40 + int((i / len(face_files)) * 25))
            
            input_path = os.path.join(face_dir, filename)
            base_name = os.path.splitext(filename)[0]
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                print(f"  🎵 正在處理音頻...")
                
                try:
                    translated_text = voice(input_path, api_key, language)
                except Exception as audio_error:
                    print(f"  ⚠️ 音頻轉文字失敗: {audio_error}")
                    translated_text = ""
                
                if not translated_text or translated_text.strip() == "":
                    print(f"  ⚠️ 段落 {filename} 沒有檢測到語音或翻譯失敗，跳過語音處理")
                    # 直接複製原始影片
                    processed_path = os.path.join(face_dir, f"{base_name}_processed.mp4")
                    import shutil
                    shutil.copy(input_path, processed_path)
                    processed_segments.append(processed_path)
                    continue
                
                print(f"  📝 翻譯結果: {translated_text}")
                
                # 2. 語音克隆（使用段落文件作為參考音頻）
                print(f"  🔊 正在進行語音克隆...")
                temp_audio_dir = os.path.dirname(os.path.join(face_dir, f"{base_name}_audio.wav"))
                self.ensure_directory_exists(temp_audio_dir)
                temp_audio = os.path.join(face_dir, f"{base_name}_audio.wav")
                
                try:
                    # 使用段落文件本身作為參考音頻進行語音克隆
                    audio_path = xttsv(translated_text, input_path, temp_audio, language)
                except Exception as tts_error:
                    print(f"  ⚠️ 語音克隆失敗: {tts_error}")
                    # 如果語音克隆失敗，直接複製原始影片
                    processed_path = os.path.join(face_dir, f"{base_name}_processed.mp4")
                    import shutil
                    shutil.copy(input_path, processed_path)
                    processed_segments.append(processed_path)
                    continue
                
                # 3. 嘴形同步
                print(f"  👄 正在進行嘴形同步...")
                processed_path = os.path.join(face_dir, f"{base_name}_processed.mp4")
                processed_dir = os.path.dirname(processed_path)
                self.ensure_directory_exists(processed_dir)
                
                # 確保 temp 目錄存在給 Wav2Lip 使用
                self.ensure_directory_exists("temp")
                
                try:
                    # 動態獲取 run_inference 函數
                    run_inference = get_wav2lip_inference()
                    if run_inference:
                        run_inference(input_path, audio_path, processed_path)
                        print(f"  ✅ 人臉段落 {filename} 處理完成")
                    else:
                        print(f"  ⚠️ Wav2Lip 不可用，使用音頻合成代替")
                        # 直接合成音頻和視頻
                        command = f'ffmpeg -y -i "{input_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{processed_path}"'
                        result = subprocess.run(command, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"  ✅ 使用音頻合成完成 {filename}")
                        else:
                            raise Exception(f"音頻合成失敗: {result.stderr}")
                except Exception as lipsync_error:
                    print(f"  ⚠️ 嘴形同步失敗: {lipsync_error}")
                    # 如果嘴形同步失敗，嘗試直接合成音頻和視頻
                    try:
                        command = f'ffmpeg -y -i "{input_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{processed_path}"'
                        result = subprocess.run(command, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"  ✅ 使用音頻合成完成 {filename}")
                        else:
                            print(f"  ⚠️ 音頻合成失敗，使用原始影片: {result.stderr}")
                            import shutil
                            shutil.copy(input_path, processed_path)
                    except Exception as merge_error:
                        print(f"  ⚠️ 音頻合成也失敗: {merge_error}")
                        import shutil
                        shutil.copy(input_path, processed_path)
                
                processed_segments.append(processed_path)
                
            except Exception as e:
                print(f"  ❌ 處理人臉段落 {filename} 時發生未預期錯誤: {e}")
                # 如果處理失敗，使用原始影片
                processed_path = os.path.join(face_dir, f"{base_name}_processed.mp4")
                import shutil
                shutil.copy(input_path, processed_path)
                processed_segments.append(processed_path)
        
        return processed_segments

    def process_slide_segments(self, ppt_dir, language, slide_language, api_key):
        """處理簡報段落：音頻提取、翻譯、OCR翻譯"""
        self.update_progress("📊 開始處理簡報段落...", 65)
        
        # 確保目錄存在
        self.ensure_directory_exists(ppt_dir)
        
        # 只處理原始段落文件，不處理已經處理過的文件
        ppt_files = sorted([f for f in os.listdir(ppt_dir) 
                          if f.endswith('.mp4') and not f.endswith('_processed.mp4')])
        processed_segments = []
        
        for i, filename in enumerate(ppt_files):
            self.update_progress(f"📋 處理簡報段落 {filename}...", 65 + int((i / len(ppt_files)) * 20))
            
            input_path = os.path.join(ppt_dir, filename)
            base_name = os.path.splitext(filename)[0]
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                print(f"  🎵 正在處理音頻...")
                
                try:
                    translated_text = voice(input_path, api_key, language)
                except Exception as audio_error:
                    print(f"  ⚠️ 音頻轉文字失敗: {audio_error}")
                    translated_text = ""
                
                # 2. 語音克隆（如果有翻譯文字）
                temp_audio = None
                if translated_text and translated_text.strip():
                    print(f"  📝 翻譯結果: {translated_text}")
                    print(f"  🔊 正在進行語音克隆...")
                    temp_audio_dir = os.path.dirname(os.path.join(ppt_dir, f"{base_name}_audio.wav"))
                    self.ensure_directory_exists(temp_audio_dir)
                    temp_audio = os.path.join(ppt_dir, f"{base_name}_audio.wav")
                    
                    try:
                        # 使用段落文件本身作為參考音頻進行語音克隆
                        xttsv(translated_text, input_path, temp_audio, language)
                    except Exception as tts_error:
                        print(f"  ⚠️ 語音克隆失敗: {tts_error}")
                        temp_audio = None
                else:
                    print(f"  ⚠️ 段落 {filename} 沒有檢測到語音或翻譯失敗")
                
                # 3. 投影片OCR翻譯
                print(f"  📖 正在進行投影片OCR翻譯...")
                processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
                processed_dir = os.path.dirname(processed_path)
                self.ensure_directory_exists(processed_dir)
                
                self.process_slide_video(input_path, processed_path, slide_language, temp_audio, api_key)
                
                processed_segments.append(processed_path)
                print(f"  ✅ 簡報段落 {filename} 處理完成")
                
            except Exception as e:
                print(f"  ❌ 處理簡報段落 {filename} 時發生錯誤: {e}")
                # 如果處理失敗，使用原始影片
                processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
                import shutil
                shutil.copy(input_path, processed_path)
                processed_segments.append(processed_path)
        
        return processed_segments

    def process_slide_video(self, input_video, output_video, target_lang, audio_path=None, api_key=None):
        """處理簡報影片，進行OCR翻譯"""
        print(f"  📖 開始處理簡報視頻: {input_video}")
        
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_video)
        self.ensure_directory_exists(output_dir)
        
        cap = cv2.VideoCapture(input_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"  📊 視頻信息: {width}x{height}, {fps}fps, 共{total_frames}幀")
        
        # 創建臨時視頻輸出
        temp_video_path = output_video.replace('.mp4', '_temp.mp4')
        temp_dir = os.path.dirname(temp_video_path)
        self.ensure_directory_exists(temp_dir)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
        
        frame_count = 0
        prev_hash = None
        current_translated_frame = None
        hash_threshold = 5  # 使用默認值
        translated_frame_count = 0
        
        print(f"  🔍 開始逐幀處理OCR翻譯...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 每10幀檢查一次是否需要重新翻譯（更頻繁檢查）
            if frame_count % 10 == 0:
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                curr_hash = imagehash.phash(pil_image)
                
                if prev_hash is None or abs(curr_hash - prev_hash) > hash_threshold:
                    # 場景改變或首次處理，進行OCR翻譯
                    print(f"    🔄 幀 {frame_count}: 檢測到場景變化，進行OCR翻譯...")
                    new_translated_frame = self.translate_frame_text(frame, target_lang, api_key)
                    
                    # 檢查翻譯是否成功
                    if new_translated_frame is not None:
                        current_translated_frame = new_translated_frame
                        translated_frame_count += 1
                        print(f"    ✅ 幀 {frame_count}: OCR翻譯成功")
                    else:
                        print(f"    ⚠️ 幀 {frame_count}: OCR翻譯失敗，使用原始幀")
                        current_translated_frame = frame
                    
                    prev_hash = curr_hash
                elif current_translated_frame is None:
                    # 如果還沒有翻譯幀，至少嘗試一次翻譯
                    print(f"    🔍 幀 {frame_count}: 首次嘗試OCR翻譯...")
                    current_translated_frame = self.translate_frame_text(frame, target_lang, api_key)
                    if current_translated_frame is not None:
                        translated_frame_count += 1
                        print(f"    ✅ 幀 {frame_count}: 首次OCR翻譯成功")
                    else:
                        current_translated_frame = frame
                        print(f"    ⚠️ 幀 {frame_count}: 首次OCR翻譯失敗，使用原始幀")
            
            # 確保有可用的幀來輸出
            output_frame = current_translated_frame if current_translated_frame is not None else frame
            out.write(output_frame)
            
            frame_count += 1
            
            # 每100幀報告一次進度
            if frame_count % 100 == 0:
                print(f"    📊 已處理 {frame_count}/{total_frames} 幀 (已翻譯場景: {translated_frame_count})")
        
        cap.release()
        out.release()
        
        print(f"  ✅ 視頻處理完成: 共{frame_count}幀，翻譯場景{translated_frame_count}個")
        print(f"  💾 臨時視頻已保存: {temp_video_path}")
        
        # 如果有音頻，合成音頻和視頻
        if audio_path and os.path.exists(audio_path):
            try:
                print(f"  🔊 開始合成音頻: {audio_path}")
                command = f'ffmpeg -y -i "{temp_video_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{output_video}"'
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    os.remove(temp_video_path)
                    print(f"  ✅ 音頻視頻合成成功: {output_video}")
                else:
                    print(f"  ⚠️ 音頻合成失敗，使用純視頻版本: {result.stderr}")
                    os.rename(temp_video_path, output_video)
            except Exception as e:
                print(f"  ⚠️ 音頻合成異常，使用純視頻版本: {e}")
                os.rename(temp_video_path, output_video)
        else:
            # 沒有音頻，直接使用視頻
            print(f"  📹 沒有音頻文件，使用純視頻版本")
            os.rename(temp_video_path, output_video)
        
        print(f"  🎯 簡報視頻處理完成: {output_video}")

    def translate_frame_text(self, frame, target_lang, api_key):
        """翻譯單個幀中的文字"""
        try:
            print(f"      🔍 開始OCR識別...")
            # OCR識別
            reader = easyocr.Reader(['ch_tra'], gpu=False)
            results = reader.readtext(frame)
            
            boxes, orig_texts = [], []
            for box, text, conf in results:
                if conf > 0.4:  # 置信度門檻
                    boxes.append(box)
                    orig_texts.append(text)
                    print(f"      📝 檢測到文字: '{text}' (置信度: {conf:.2f})")
            
            if not orig_texts:
                print(f"      ⚠️ 未檢測到文字內容，返回原始幀")
                return frame
            
            print(f"      🔍 找到 {len(orig_texts)} 個文字區塊，開始翻譯...")
            
            # 移除原文
            img_clean = self.remove_text_with_inpainting(frame, boxes)
            print(f"      🧹 原文移除完成")
            
            # 翻譯文字
            translated = []
            for i, text in enumerate(orig_texts):
                translated_text = self.translate_with_gemini(text, target_lang, api_key)
                translated.append(translated_text)
                print(f"      📝 翻譯 {i+1}: '{text}' -> '{translated_text}'")
            
            # 添加翻譯文字
            pil_img = Image.fromarray(cv2.cvtColor(img_clean, cv2.COLOR_BGR2RGB))
            font_path = self.font_paths.get(target_lang, self.font_paths["English"])
            print(f"      🎨 使用字體: {font_path}")
            
            final = self.draw_translated_text(pil_img, boxes, translated, font_path)
            result_frame = cv2.cvtColor(np.array(final), cv2.COLOR_RGB2BGR)
            
            print(f"      ✅ 文字翻譯完成，返回翻譯後的幀")
            return result_frame
            
        except Exception as e:
            print(f"      ❌ 幀文字翻譯失敗: {e}")
            import traceback
            traceback.print_exc()
            print(f"      🔄 返回原始幀作為備用")
            return frame

    def auto_edit_segments(self, face_segments, slide_segments, segments_info, output_path):
        """根據原始順序自動剪接所有段落"""
        self.update_progress("🎬 開始自動剪接段落...", 85)
        print(f"  👤 人臉段落數量: {len(face_segments)}")
        print(f"  📊 簡報段落數量: {len(slide_segments)}")
        print(f"  📋 段落信息數量: {len(segments_info)}")
        
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        self.ensure_directory_exists(output_dir)
        
        # 創建段落映射並檢查文件存在性
        face_map = {}
        slide_map = {}
        
        face_idx = 1
        slide_idx = 1
        
        print("  📁 檢查人臉段落文件:")
        for segment_path in face_segments:
            if os.path.exists(segment_path):
                face_map[face_idx] = segment_path
                print(f"    ✅ 人臉段落 {face_idx}: {segment_path}")
            else:
                print(f"    ❌ 人臉段落 {face_idx} 文件不存在: {segment_path}")
            face_idx += 1
            
        print("  📁 檢查簡報段落文件:")
        for segment_path in slide_segments:
            if os.path.exists(segment_path):
                slide_map[slide_idx] = segment_path
                print(f"    ✅ 簡報段落 {slide_idx}: {segment_path}")
            else:
                print(f"    ❌ 簡報段落 {slide_idx} 文件不存在: {segment_path}")
            slide_idx += 1
        
        # 按原始順序排列段落
        ordered_segments = []
        face_counter = 1
        slide_counter = 1
        
        print("  🔄 按原始順序排列段落:")
        for i, segment in enumerate(segments_info):
            segment_type = segment['type']
            if segment_type == 'face' and face_counter in face_map:
                segment_path = face_map[face_counter]
                ordered_segments.append(segment_path)
                print(f"    {i+1}. 人臉段落 {face_counter}: {os.path.basename(segment_path)}")
                face_counter += 1
            elif segment_type == 'slide' and slide_counter in slide_map:
                segment_path = slide_map[slide_counter]
                ordered_segments.append(segment_path)
                print(f"    {i+1}. 簡報段落 {slide_counter}: {os.path.basename(segment_path)}")
                slide_counter += 1
            else:
                print(f"    {i+1}. ⚠️ 跳過段落: {segment_type} (無對應文件)")
        
        if not ordered_segments:
            raise ValueError("沒有找到可以剪接的段落")
        
        print(f"  📝 最終剪接列表共 {len(ordered_segments)} 個段落")
        
        # 創建段落列表文件
        segment_list_path = "temp/segment_list.txt"
        self.ensure_directory_exists(os.path.dirname(segment_list_path))
        
        print(f"  📄 創建段落列表文件: {segment_list_path}")
        with open(segment_list_path, 'w', encoding='utf-8') as f:
            for i, segment_path in enumerate(ordered_segments):
                # 使用絕對路徑確保 ffmpeg 能找到文件
                abs_path = os.path.abspath(segment_path)
                f.write(f"file '{abs_path}'\n")
                print(f"    {i+1}. {abs_path}")
        
        # 使用 ffmpeg 合併段落
        self.update_progress("🔗 正在合併段落...", 90)
        print(f"🔗 正在合併 {len(ordered_segments)} 個段落...")
        
        try:
            if len(ordered_segments) == 1:
                # 只有一個文件，直接複製
                print("  📁 只有一個段落，直接複製...")
                import shutil
                shutil.copy(ordered_segments[0], output_path)
                print("✅ 單文件複製完成")
                return
            
            # 使用統一解析度的filter_complex進行合併
            self.merge_segments_with_normalization(ordered_segments, output_path)
            
        except Exception as e:
            print(f"⚠️ 合併失敗: {e}")
            # 最後備用：直接複製第一個文件
            if ordered_segments:
                print("🔄 使用最終備用方案：複製第一個段落")
                try:
                    import shutil
                    shutil.copy(ordered_segments[0], output_path)
                    print(f"📁 已複製第一個段落: {ordered_segments[0]}")
                    print("⚠️ 注意：只有第一個段落被保存，其他段落被跳過")
                except Exception as copy_error:
                    print(f"❌ 連備用方案都失敗了: {copy_error}")
                    raise Exception(f"所有方法都失敗: 原錯誤={e}, 複製錯誤={copy_error}")
            else:
                raise Exception("所有合併方法都失敗且無可用段落")

    def has_audio_stream(self, video_path):
        """檢查視頻文件是否有音頻流"""
        try:
            import subprocess
            command = f'ffprobe -v quiet -select_streams a -show_entries stream=index -of csv=p=0 "{video_path}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return bool(result.stdout.strip())
        except Exception as e:
            print(f"檢查音頻流失敗: {e}")
            return False

    def merge_segments_with_normalization(self, segments, output_path):
        """使用統一解析度合併段落"""
        try:
            # 首先嘗試簡單合併，如果失敗再用複雜方法
            print("  🔄 優先嘗試簡單合併方法...")
            try:
                self.merge_segments_simple_concat(segments, output_path)
                return
            except Exception as simple_error:
                print(f"  ⚠️ 簡單合併失敗: {simple_error}")
                print("  🔄 嘗試智能合併方法...")
            
            if len(segments) == 2:
                # 檢查每個文件是否有音頻流
                has_audio = [self.has_audio_stream(seg) for seg in segments]
                print(f"  🔍 音頻流檢查: {[f'{seg}: {has}' for seg, has in zip(segments, has_audio)]}")
                
                input_params = ' '.join([f'-i "{seg}"' for seg in segments])
                
                # 根據音頻流情況選擇不同的合併策略
                if all(has_audio):
                    # 兩個文件都有音頻
                    filter_complex = "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[0:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
                    map_params = '-map "[outv]" -map "[outa]" -c:v libx264 -c:a aac'
                elif has_audio[0] and not has_audio[1]:
                    # 只有第一個文件有音頻，使用更簡單的策略
                    filter_complex = "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[v0][v1]concat=n=2:v=1:a=0[outv]"
                    map_params = '-map "[outv]" -map 0:a -c:v libx264 -c:a aac'
                elif not has_audio[0] and has_audio[1]:
                    # 只有第二個文件有音頻
                    filter_complex = "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[1:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a1];[v0][v1]concat=n=2:v=1:a=0[outv];[a1]apad[outa]"
                    map_params = '-map "[outv]" -map "[outa]" -c:v libx264 -c:a aac'
                else:
                    # 兩個文件都沒有音頻
                    filter_complex = "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[v0][v1]concat=n=2:v=1:a=0[outv]"
                    map_params = '-map "[outv]" -c:v libx264'
                
                command = f'ffmpeg -y {input_params} -filter_complex "{filter_complex}" {map_params} "{output_path}"'
                print(f"  🔧 執行命令: {command}")
                
                try:
                    # 添加超時機制，最多等待300秒（5分鐘）
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print("✅ filter_complex 智能合併成功")
                        self.verify_output_file(output_path)
                        return
                    else:
                        print(f"⚠️ filter_complex 智能合併失敗: {result.stderr}")
                        raise Exception("智能合併失敗")
                        
                except subprocess.TimeoutExpired:
                    print("⚠️ FFmpeg 合併超時，嘗試簡單方法")
                    raise Exception("合併超時")
                except Exception as e:
                    print(f"⚠️ FFmpeg 合併異常: {e}")
                    raise Exception("合併異常")
                    
                # 如果到這裡說明出錯了，嘗試簡單的concat方法
                print("  🔄 嘗試簡單合併方法...")
                self.merge_segments_simple_concat(segments, output_path)
            else:
                # 多個文件，統一解析度後合併
                input_params = ' '.join([f'-i "{seg}"' for seg in segments])
                
                # 為每個輸入創建scale和audio format濾鏡
                video_filters = []
                audio_filters = []
                concat_inputs = []
                
                for i in range(len(segments)):
                    video_filters.append(f"[{i}:v]scale=1280:720,setsar=1:1[v{i}]")
                    audio_filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a{i}]")
                    concat_inputs.extend([f"[v{i}]", f"[a{i}]"])
                
                filter_complex = ';'.join(video_filters + audio_filters) + ';' + ''.join(concat_inputs) + f'concat=n={len(segments)}:v=1:a=1[outv][outa]'
                
                command = f'ffmpeg -y {input_params} -filter_complex "{filter_complex}" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{output_path}"'
                print(f"  🔧 執行命令: {command}")
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ filter_complex 多文件解析度統一合併成功")
                    self.verify_output_file(output_path)
                    return
                else:
                    print(f"⚠️ filter_complex 多文件解析度統一失敗: {result.stderr}")
                    raise Exception("多文件合併失敗")
        except Exception as e:
            print(f"⚠️ 合併段落失敗: {e}")
            raise

    def merge_segments_simple_concat(self, segments, output_path):
        """簡單的段落合併方法"""
        temp_list_path = None
        try:
            print("  🔄 執行簡單合併方法...")
            
            # 創建臨時文件列表
            temp_list_path = "temp/simple_concat_list.txt"
            with open(temp_list_path, 'w', encoding='utf-8') as f:
                for segment in segments:
                    abs_path = os.path.abspath(segment)
                    f.write(f"file '{abs_path}'\n")
            
            # 方法1: 嘗試直接 concat
            command1 = f'ffmpeg -y -f concat -safe 0 -i "{temp_list_path}" -c copy "{output_path}"'
            print(f"  🔧 嘗試方法1 (copy): {command1}")
            
            try:
                result = subprocess.run(command1, shell=True, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    print("✅ 簡單合併(copy)成功")
                    self.verify_output_file(output_path)
                    return
                else:
                    print(f"  ⚠️ 方法1失敗: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("  ⚠️ 方法1超時")
            
            # 方法2: 重新編碼合併
            command2 = f'ffmpeg -y -f concat -safe 0 -i "{temp_list_path}" -c:v libx264 -c:a aac "{output_path}"'
            print(f"  🔧 嘗試方法2 (re-encode): {command2}")
            
            try:
                result = subprocess.run(command2, shell=True, capture_output=True, text=True, timeout=180)
                if result.returncode == 0:
                    print("✅ 簡單合併(re-encode)成功")
                    self.verify_output_file(output_path)
                    return
                else:
                    print(f"  ⚠️ 方法2失敗: {result.stderr}")
                    raise Exception(f"重新編碼合併失敗: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("  ⚠️ 方法2超時")
                raise Exception("重新編碼合併超時")
                
        except Exception as e:
            print(f"⚠️ 簡單合併異常: {e}")
            raise
        finally:
            # 清理臨時文件
            if temp_list_path and os.path.exists(temp_list_path):
                try:
                    os.remove(temp_list_path)
                except:
                    pass

    def verify_output_file(self, output_path):
        """驗證輸出文件"""
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📹 輸出文件: {output_path}")
            print(f"📊 輸出文件大小: {file_size/1024/1024:.2f} MB")
            
            # 檢查文件是否有效（大小大於1KB）
            if file_size < 1024:
                print("⚠️ 輸出文件太小，可能有問題")
            else:
                print("✅ 輸出文件驗證通過")
        else:
            print("❌ 輸出文件創建失敗")

    def ensure_basic_directories(self):
        """確保所有必要的基本目錄都存在"""
        required_dirs = [
            "temp",
            "temp/faceai", 
            "temp/pptai",
            "temp/audio_segments",
            "temp/slides_output",
            "temp/translated_slides",
            "temp/segments",
            "temp/uploads"
        ]
        
        for dir_path in required_dirs:
            os.makedirs(dir_path, exist_ok=True)

    def ensure_directory_exists(self, directory_path):
        """確保指定目錄存在"""
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            print(f"📁 創建目錄: {directory_path}")
        return directory_path

    def process_complete_video(self, input_path, output_path, language, slide_language, 
                             api_key, enable_slide_translation=True, min_segment_duration=2, 
                             hash_threshold=5):
        """完整的視頻處理流程"""
        try:
            # 確保所有必要的目錄存在
            self.ensure_basic_directories()
            
            # 步驟1：分析並分段影片
            self.update_progress("正在進行智能分段分析...", 5)
            segments_info = self.analyze_and_segment_video(input_path, min_segment_duration, hash_threshold)
            
            if not segments_info:
                raise ValueError("無法分析影片內容，請確認影片格式正確")
            
            # 步驟2：處理人臉段落
            self.update_progress("正在處理人臉段落...", 40)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 項目根目錄
            face_dir = os.path.join(base_dir, "temp", "faceai")
            ppt_dir = os.path.join(base_dir, "temp", "pptai")
            
            face_segments = self.process_face_segments(face_dir, language, api_key)
            
            # 步驟3：處理簡報段落
            if enable_slide_translation:
                self.update_progress("正在處理簡報段落...", 65)
                processed_slide_segments = self.process_slide_segments(ppt_dir, language, slide_language, api_key)
            else:
                # 如果不啟用簡報翻譯，直接處理音頻但不翻譯投影片內容
                self.update_progress("正在處理簡報音頻...", 65)
                processed_slide_segments = self.process_slide_audio_only(ppt_dir, language, api_key)
            
            # 步驟4：自動剪接
            self.update_progress("正在進行自動剪接...", 85)
            self.auto_edit_segments(face_segments, processed_slide_segments, segments_info, output_path)
            
            self.update_progress("處理完成！", 100)
            
        except Exception as e:
            self.update_progress(f"處理過程中發生錯誤：{str(e)}", 0)
            raise

    def process_slide_audio_only(self, ppt_dir, language, api_key):
        """僅處理簡報段落的音頻，不進行OCR翻譯"""
        self.update_progress("📋 正在處理簡報音頻（跳過OCR翻譯）...", 65)
        
        # 確保目錄存在
        self.ensure_directory_exists(ppt_dir)
        
        # 只處理原始段落文件，不處理已經處理過的文件
        ppt_files = sorted([f for f in os.listdir(ppt_dir) 
                          if f.endswith('.mp4') and not f.endswith('_processed.mp4')])
        processed_segments = []
        
        for j, filename in enumerate(ppt_files):
            input_path = os.path.join(ppt_dir, filename)
            base_name = os.path.splitext(filename)[0]
            processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
            
            try:
                print(f"📋 處理簡報音頻 {filename}...")
                
                try:
                    translated_text = voice(input_path, api_key, language)
                except Exception as audio_error:
                    print(f"  ⚠️ 音頻轉文字失敗: {audio_error}")
                    translated_text = ""
                
                if translated_text and translated_text.strip():
                    print(f"  📝 翻譯結果: {translated_text}")
                    temp_audio = os.path.join(ppt_dir, f"{base_name}_audio.wav")
                    self.ensure_directory_exists(os.path.dirname(temp_audio))
                    
                    try:
                        # 使用段落文件本身作為參考音頻進行語音克隆
                        xttsv(translated_text, input_path, temp_audio, language)
                        
                        # 合成音頻和視頻（保持原始視頻內容，只替換音頻）
                        command = f'ffmpeg -y -i "{input_path}" -i "{temp_audio}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{processed_path}"'
                        result = subprocess.run(command, shell=True, capture_output=True, text=True)
                        if result.returncode != 0:
                            print(f"  ⚠️ 音頻合成失敗，使用原始視頻: {result.stderr}")
                            import shutil
                            shutil.copy(input_path, processed_path)
                        else:
                            print(f"  ✅ 音頻替換完成")
                    except Exception as tts_error:
                        print(f"  ⚠️ 語音克隆失敗: {tts_error}")
                        import shutil
                        shutil.copy(input_path, processed_path)
                else:
                    # 沒有音頻，直接複製
                    print(f"  ⚠️ 沒有檢測到語音內容")
                    import shutil
                    shutil.copy(input_path, processed_path)
                
                processed_segments.append(processed_path)
                
            except Exception as e:
                print(f"  ❌ 處理簡報音頻失敗: {e}")
                import shutil
                shutil.copy(input_path, processed_path)
                processed_segments.append(processed_path)
            
            # 更新進度
            progress = 65 + int((j / len(ppt_files)) * 20)
            self.update_progress(f"處理簡報音頻: {j+1}/{len(ppt_files)}", progress)
        
        return processed_segments
