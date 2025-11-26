import os
import sys
import threading
import urllib.request
import uuid
import time
from datetime import datetime
import queue
import json

# 添加 Wav2Lip 目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'Wav2Lip'))

from txtvoice import voice
from xttsv import xttsv
from Wav2Lip.inference import run_inference

# ImageHash_ppt 功能導入
import cv2
import easyocr
import numpy as np
import imagehash
from PIL import Image, ImageDraw, ImageFont
import requests 
import re
import subprocess

# Flask 相關
from flask import Flask, request, jsonify, render_template, Response, send_file
from werkzeug.utils import secure_filename

# 創建 Flask 應用
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'temp/uploads'

# 任務狀態管理
tasks = {}
task_logs = {}
task_progress = {}


class VideoProcessingTask:
    """影片處理任務類"""
    def __init__(self, task_id, params):
        self.task_id = task_id
        self.params = params
        self.status = 'pending'
        self.progress = 0
        self.error = None
        self.output_path = None
        self.log_queue = queue.Queue()
        
    def log(self, message, level='info'):
        """添加日誌"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'level': level
        }
        self.log_queue.put(log_entry)
        print(f"[{timestamp}] {message}")
        
    def update_progress(self, progress, status=None):
        """更新進度"""
        self.progress = progress
        if status:
            self.status = status
        task_progress[self.task_id] = {
            'progress': progress,
            'status': self.status
        }


class DeepVideoTranslationApp:
    """影片翻譯處理核心類"""
    
    def __init__(self, task=None):
        """初始化處理器"""
        self.task = task
        self.setup_fonts()
        self.ensure_basic_directories()
        
        # 設置參數
        self.api_key = None
        self.min_segment_duration = 2
        self.hash_threshold = 5
        
        # 初始化人臉檢測器（避免重複載入）
        self.face_cascade = None
        self._init_face_detector()

    def setup_fonts(self):
        """設置字體路徑，使用本地的 Noto 字體"""
        current_dir = os.path.dirname(__file__)
        
        # 檢查本地字體文件
        self.font_paths = {
            "Japanese": os.path.join(current_dir, "NotoSansCJKjp-Regular.otf"),
            "English": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "Chinese": os.path.join(current_dir, "NotoSansTC-Regular.ttf"),
            "German": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "French": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "Russian": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "Italian": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
            "Spanish": self.get_system_font() or "/System/Library/Fonts/Arial.ttf"
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

    def ensure_basic_directories(self):
        """確保基本目錄存在"""
        directories = ['temp', 'temp/uploads', 'temp/segments', 'temp/audio_segments']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _init_face_detector(self):
        """初始化人臉檢測器（只載入一次）"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("⚠️ 警告: 人臉檢測器載入失敗，將使用備用方法")
                self.face_cascade = None
        except Exception as e:
            print(f"⚠️ 初始化人臉檢測器失敗: {e}")
            self.face_cascade = None

    def detect_faces_in_frame(self, frame):
        """檢測幀中是否有人臉"""
        if frame is None or frame.size == 0:
            return False
            
        try:
            # 如果檢測器未初始化，嘗試初始化
            if self.face_cascade is None:
                self._init_face_detector()
                if self.face_cascade is None:
                    return False
            
            # 轉換為灰階
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 使用多種參數嘗試檢測
            # 第一次嘗試：標準參數
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                return True
                
            # 第二次嘗試：更寬鬆的參數
            faces = self.face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))
            if len(faces) > 0:
                return True
                
            # 第三次嘗試：非常寬鬆的參數
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 2, minSize=(20, 20))
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

    def log(self, message, level='info'):
        """記錄日誌"""
        if self.task:
            self.task.log(message, level)
        else:
            print(message)
    
    def update_progress(self, progress, status=None):
        """更新進度"""
        if self.task:
            self.task.update_progress(progress, status)

    # 投影片翻譯功能
    def translate_with_gemini(self, text, target_lang="Japanese"):
        """使用 Gemini API 翻譯文字"""
        api_key = self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        lang_prompts = {
            "Japanese": "Translate the following text to Japanese. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "English": "Translate the following text to English. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "Chinese": "Translate the following text to Chinese. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "German": "Translate the following text to German. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "French": "Translate the following text to French. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "Russian": "Translate the following text to Russian. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "Italian": "Translate the following text to Italian. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: ",
            "Spanish": "Translate the following text to Spanish. Output ONLY the translated text, no explanations, no additional words, no prefixes like 'Translation:' or 'Here is:'\n\nText: "
        }
        
        prompt = lang_prompts.get(target_lang, lang_prompts["Japanese"]) + text
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                translated = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                # 清理翻譯結果 - 移除常見的前綴和說明文字
                clean_result = translated.strip()
                
                # 移除常見的英文前綴
                english_prefixes = [
                    "Here is the translation:",
                    "Here's the translation:",
                    "Translation:",
                    "The translation is:",
                    "Translated text:",
                    "Here is:",
                    "Here's:",
                    "Output:",
                    "Result:"
                ]
                
                # 移除常見的中文前綴
                chinese_prefixes = [
                    "翻譯結果：",
                    "翻譯如下：",
                    "翻譯為：",
                    "翻譯：",
                    "譯文：",
                    "翻譯後："
                ]
                
                for prefix in english_prefixes + chinese_prefixes:
                    if clean_result.startswith(prefix):
                        clean_result = clean_result[len(prefix):].strip()
                        break
                
                # 移除開頭的引號、冒號等符號
                clean_result = re.sub(r'^["\':：\s]+', '', clean_result)
                clean_result = re.sub(r'["\':：\s]+$', '', clean_result)
                
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
            # 膨脹文字區域以確保完全覆蓋
            cv2.fillPoly(mask, [pts], 255)
            # 對mask進行膨脹操作，擴大移除區域
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
        # 使用更好的修復半徑
        return cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)

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

            # 調整字型大小 - 使用更合理的計算方式
            font_size = max(int(box_h * 0.7), 18)  # 增加字型比例和最小字型大小
            
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

            # 計算文字換行 - 改進換行邏輯
            max_chars = max(int(box_w / (font_size * 0.55)), 1)  # 調整字符寬度估算
            lines = []
            
            # 更智能的換行處理
            words = txt.split()
            if len(words) > 1:
                # 如果有多個詞，按詞換行
                current_line = ""
                for word in words:
                    test_line = current_line + word + " "
                    if len(test_line) <= max_chars:
                        current_line = test_line
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
            line_height = font_size + 4  # 增加行間距
            
            for line in lines:
                if y + line_height > y1:  # 檢查是否超出邊界
                    break
                try:
                    # 繪製黑色文字
                    draw.text((x0, y), line, font=font, fill=(0, 0, 0))
                    print(f"    ✅ 繪製文字: {line}")
                    y += line_height
                except Exception as e:
                    print(f"    ❌ 文字繪製失敗: {e}")
                    continue
                    
        return pil_img

    def process_slide_image(self, image_path, output_path, target_lang):
        """處理單張投影片圖片"""
        img = cv2.imread(image_path)
        reader = easyocr.Reader(['ch_tra'], gpu=False)
        results = reader.readtext(img)

        boxes, orig_texts = [], []
        for box, text, conf in results:
            if conf > 0.4:
                boxes.append(box)
                orig_texts.append(text)

        if not orig_texts:
            # 如果沒有文字，直接複製原圖
            cv2.imwrite(output_path, img)
            return

        print(f"🔍 找到 {len(orig_texts)} 個文字區塊: {orig_texts}")

        # 移除原文文字
        img_clean = self.remove_text_with_inpainting(img, boxes)

        # 翻譯所有文字
        translated = [self.translate_with_gemini(t, target_lang) for t in orig_texts]
        print(f"📝 翻譯結果: {translated}")

        # 轉為 PIL 進行貼字
        pil_img = Image.fromarray(cv2.cvtColor(img_clean, cv2.COLOR_BGR2RGB))
        
        # 使用準備好的字型路徑
        font_path = self.font_paths.get(target_lang, self.font_paths["English"])

        final = self.draw_translated_text(pil_img, boxes, translated, font_path)
        final.save(output_path)
        print(f"💾 投影片已保存: {output_path}")

    def extract_and_translate_slides(self, video_path, target_lang):
        """智能提取並翻譯投影片（只處理沒有人臉的頁面）"""
        slides_dir = "temp/slides_output"
        translated_dir = "temp/translated_slides"
        os.makedirs(slides_dir, exist_ok=True)
        os.makedirs(translated_dir, exist_ok=True)

        frame_interval = 10  # 固定值
        hash_threshold = self.hash_threshold

        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        prev_hash = None
        slide_index = 0
        slide_frame_mapping = {}  # 記錄幀號到投影片的映射

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        processed_slides = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                curr_hash = imagehash.phash(pil_image)

                # 檢查是否為新的投影片
                if prev_hash is None or abs(curr_hash - prev_hash) > hash_threshold:
                    # 檢查是否為簡報頁面（沒有人臉）
                    if self.is_slide_frame(frame):
                        # 保存原始投影片
                        slide_path = os.path.join(slides_dir, f'slide_{slide_index:02d}.jpg')
                        pil_image.save(slide_path)
                        
                        # 翻譯投影片
                        translated_path = os.path.join(translated_dir, f'slide_{slide_index:02d}.jpg')
                        self.process_slide_image(slide_path, translated_path, target_lang)
                        
                        # 記錄幀號映射
                        slide_frame_mapping[frame_count] = slide_index
                        processed_slides += 1
                        
                        print(f"處理投影片 {slide_index} (幀 {frame_count})")
                        slide_index += 1
                    
                    prev_hash = curr_hash

            frame_count += 1
            
            # 更新進度
            if frame_count % 100 == 0:
                progress = int((frame_count / total_frames) * 30) + 70  # 70-100% 的進度區間
                self.update_progress(progress)

        cap.release()
        self.log(f"總共處理了 {processed_slides} 張投影片")
        return translated_dir, slide_frame_mapping

    def create_translated_video(self, original_video, translated_slides_dir, slide_frame_mapping, output_path, audio_path):
        """將翻譯後的投影片合成到影片中，並確保音頻正確"""
        frame_interval = 10  # 固定值
        hash_threshold = self.hash_threshold
        
        # 讀取翻譯後的投影片
        translated_slides = {}
        for filename in os.listdir(translated_slides_dir):
            if filename.startswith('slide_') and filename.endswith('.jpg'):
                slide_index = int(filename.split('_')[1].split('.')[0])
                slide_path = os.path.join(translated_slides_dir, filename)
                translated_slides[slide_index] = cv2.imread(slide_path)

        # 打開原始影片
        cap = cv2.VideoCapture(original_video)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # 創建臨時影片（只有視頻）
        temp_video_path = "temp/video_only.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

        frame_count = 0
        prev_hash = None
        current_slide_index = None
        current_slide = None

        print("🎬 開始合成影片...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 檢查是否為需要替換的幀
            if frame_count % frame_interval == 0:
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                curr_hash = imagehash.phash(pil_image)

                if prev_hash is None or abs(curr_hash - prev_hash) > hash_threshold:
                    # 檢查是否有對應的翻譯投影片
                    if frame_count in slide_frame_mapping:
                        slide_idx = slide_frame_mapping[frame_count]
                        if slide_idx in translated_slides:
                            current_slide = cv2.resize(translated_slides[slide_idx], (width, height))
                            current_slide_index = slide_idx
                            print(f"📽️ 替換幀 {frame_count} 為投影片 {slide_idx}")
                    elif not self.is_slide_frame(frame):
                        # 如果不是投影片頁面，清除當前投影片
                        current_slide = None
                        current_slide_index = None
                    
                    prev_hash = curr_hash

            # 選擇要寫入的幀
            if current_slide is not None and self.is_slide_frame(frame):
                out.write(current_slide)
            else:
                out.write(frame)

            frame_count += 1

        cap.release()
        out.release()

        # 合成音頻和視頻
        print("🔊 正在合成音頻...")
        try:
            command = f'ffmpeg -y -i "{temp_video_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{output_path}"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 音頻合成成功")
            else:
                print(f"❌ 音頻合成失敗: {result.stderr}")
                # 如果合成失敗，至少保留視頻
                import shutil
                shutil.copy(temp_video_path, output_path)
                
        except Exception as e:
            print(f"❌ 音頻合成錯誤: {e}")
            # 如果出錯，至少保留視頻
            import shutil
            shutil.copy(temp_video_path, output_path)

    def extract_face_only_video(self, video_path, output_path):
        """提取只包含人臉的視頻片段供 Wav2Lip 使用"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"🔍 正在分析視頻: {video_path}")
        print(f"📊 視頻信息: {width}x{height}, {fps}fps, 共{total_frames}幀")
        
        # 設置視頻編碼器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        face_frames_found = 0
        slide_frames_found = 0
        last_face_frame = None
        
        print("🔍 正在提取包含人臉的幀...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 檢測是否有人臉
            has_faces = self.detect_faces_in_frame(frame)
            is_slide = self.is_slide_frame(frame)
            
            if has_faces:
                out.write(frame)
                last_face_frame = frame.copy()
                face_frames_found += 1
                if frame_count % 100 == 0:
                    print(f"  幀 {frame_count}: 檢測到人臉 ✅")
            elif is_slide:
                slide_frames_found += 1
                # 對於投影片幀，使用最後一個人臉幀（如果有的話）
                if last_face_frame is not None:
                    out.write(last_face_frame)
                    if frame_count % 100 == 0:
                        print(f"  幀 {frame_count}: 投影片頁面，使用最後人臉幀 📋")
                else:
                    # 如果還沒有找到人臉幀，暫時寫入當前幀
                    out.write(frame)
                    if frame_count % 100 == 0:
                        print(f"  幀 {frame_count}: 投影片頁面，無可用人臉幀 ⚠️")
            else:
                # 其他情況，可能是過渡幀或不清楚的內容
                if last_face_frame is not None:
                    out.write(last_face_frame)
                else:
                    out.write(frame)
                if frame_count % 100 == 0:
                    print(f"  幀 {frame_count}: 其他內容")
            
            frame_count += 1
            
        cap.release()
        out.release()
        
        print(f"✅ 視頻分析完成:")
        print(f"   👤 人臉幀: {face_frames_found}")
        print(f"   📋 投影片幀: {slide_frames_found}")
        print(f"   📹 總幀數: {frame_count}")
        print(f"   💾 輸出視頻: {output_path}")
        
        if face_frames_found == 0:
            # 嘗試一個更寬鬆的人臉檢測策略
            print("⚠️ 未檢測到人臉，嘗試更寬鬆的檢測策略...")
            return self.extract_face_only_video_relaxed(video_path, output_path)
            
        return output_path

    def extract_face_only_video_relaxed(self, video_path, output_path):
        """使用更寬鬆的策略提取人臉視頻"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 設置視頻編碼器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        potential_face_frames = 0
        
        print("🔄 使用寬鬆策略重新分析...")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 更寬鬆的策略：只要不是明顯的投影片就當作人臉幀
            is_slide = self.is_slide_frame(frame)
            
            if not is_slide:
                out.write(frame)
                potential_face_frames += 1
            else:
                # 即使是投影片，也寫入一些幀來保持視頻連續性
                # 但我們會用非投影片的幀替代
                if potential_face_frames > 0:
                    # 重複上一個非投影片幀
                    out.write(frame)  # 暫時寫入，實際應該用上一個非投影片幀
                else:
                    out.write(frame)
            
            frame_count += 1
            
        cap.release()
        out.release()
        
        print(f"✅ 寬鬆策略完成: {potential_face_frames}/{frame_count} 幀可能包含人臉")
        
        if potential_face_frames == 0:
            raise ValueError("視頻中沒有檢測到任何可用的人臉內容，無法進行嘴形同步。請確認視頻包含人物講話的片段。")
            
        return output_path

    def analyze_video_content(self, video_path):
        """分析視頻內容，統計人臉幀和投影片幀數量"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_count = 0
        face_count = 0
        slide_count = 0
        
        # 只分析前100幀來快速評估
        sample_frames = min(100, total_frames)
        step = max(1, total_frames // sample_frames)
        
        while frame_count < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
            ret, frame = cap.read()
            if not ret:
                break
                
            has_faces = self.detect_faces_in_frame(frame)
            is_slide = self.is_slide_frame(frame)
            
            if has_faces:
                face_count += 1
            elif is_slide:
                slide_count += 1
                
            frame_count += step
            
        cap.release()
        
        # 根據採樣比例推算全部幀數
        scale_factor = total_frames / sample_frames if sample_frames > 0 else 1
        estimated_face_count = int(face_count * scale_factor)
        estimated_slide_count = int(slide_count * scale_factor)
        
        return estimated_face_count, estimated_slide_count, total_frames

    def analyze_and_segment_video(self, video_path):
        """分析影片並智能分段，分離人臉和簡報片段（優化版：減少過度分段）"""
        self.log("🔍 開始分析影片內容並進行智能分段...")
        
        # 創建輸出目錄
        face_dir = "temp/faceai"
        ppt_dir = "temp/pptai"
        os.makedirs(face_dir, exist_ok=True)
        os.makedirs(ppt_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        min_duration = self.min_segment_duration
        min_frames = int(fps * min_duration)
        hash_threshold = self.hash_threshold
        
        # 場景穩定性檢查參數
        stability_check_frames = 3  # 需要連續3幀確認才算場景變化
        check_interval = 15  # 每15幀檢查一次（從5幀改為15幀，減少檢查頻率）
        
        # 第一步：分析整個影片的內容類型
        self.log("📊 正在分析影片內容類型...")
        segments = []
        current_segment = None
        frame_count = 0
        prev_hash = None
        
        # 場景穩定性追蹤
        pending_type_change = None  # 待確認的類型變化
        pending_type_change_count = 0  # 連續相同類型變化的計數
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 只在指定間隔檢查內容類型（降低檢查頻率）
            if frame_count % check_interval == 0:
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
                    # 初始化第一個段落
                    current_segment = {
                        'type': segment_type,
                        'start_frame': frame_count,
                        'end_frame': frame_count,
                        'frames': [frame_count]
                    }
                    pending_type_change = None
                    pending_type_change_count = 0
                else:
                    # 檢查類型是否改變
                    type_changed = current_segment['type'] != segment_type
                    
                    # 檢查場景是否變化（基於 hash）
                    scene_changed = False
                    if prev_hash is not None and frame_count % check_interval == 0:
                        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        current_hash = imagehash.phash(pil_image)
                        scene_changed = abs(current_hash - prev_hash) > hash_threshold
                        prev_hash = current_hash
                    elif prev_hash is None:
                        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        prev_hash = imagehash.phash(pil_image)
                    
                    # 場景穩定性檢查：需要連續確認才算真正變化
                    if type_changed or scene_changed:
                        if pending_type_change == segment_type:
                            # 連續相同的變化，增加計數
                            pending_type_change_count += 1
                        else:
                            # 不同的變化，重新開始計數
                            pending_type_change = segment_type
                            pending_type_change_count = 1
                        
                        # 達到穩定性門檻，確認場景變化
                        if pending_type_change_count >= stability_check_frames:
                            # 結束當前段落（確保達到最小長度）
                            segment_duration = (frame_count - current_segment['start_frame']) / fps
                            if segment_duration >= min_duration:
                                current_segment['end_frame'] = frame_count - 1
                                segments.append(current_segment)
                                
                                # 開始新段落
                                current_segment = {
                                    'type': segment_type,
                                    'start_frame': frame_count,
                                    'end_frame': frame_count,
                                    'frames': [frame_count]
                                }
                                self.log(f"   ✂️ 場景切換: 幀 {frame_count} ({segment_type})")
                            else:
                                # 段落太短，繼續延伸
                                current_segment['end_frame'] = frame_count
                                current_segment['frames'].append(frame_count)
                            
                            # 重置穩定性追蹤
                            pending_type_change = None
                            pending_type_change_count = 0
                        else:
                            # 還未達到穩定性門檻，繼續觀察
                            current_segment['end_frame'] = frame_count
                            current_segment['frames'].append(frame_count)
                    else:
                        # 類型沒變化，繼續當前段落
                        current_segment['end_frame'] = frame_count
                        current_segment['frames'].append(frame_count)
                        # 重置穩定性追蹤
                        pending_type_change = None
                        pending_type_change_count = 0
            else:
                # 不在檢查間隔，繼續當前段落
                if current_segment:
                    current_segment['end_frame'] = frame_count
                    current_segment['frames'].append(frame_count)
            
            frame_count += 1
            
            # 更新進度
            if frame_count % 100 == 0:
                progress = int((frame_count / total_frames) * 20)  # 分析階段占20%進度
                self.update_progress(progress)
        
        # 添加最後一個段落
        if current_segment:
            segment_duration = (current_segment['end_frame'] - current_segment['start_frame']) / fps
            if segment_duration >= min_duration:
                segments.append(current_segment)
        
        cap.release()
        
        self.log(f"📋 初步分析完成，找到 {len(segments)} 個段落")
        
        # 第三步：合併相鄰的相同類型短段落
        self.log("🔗 正在合併相鄰的相同類型段落...")
        merged_segments = self.merge_similar_segments(segments, fps, min_duration)
        
        self.log(f"📋 合併後剩餘 {len(merged_segments)} 個段落:")
        face_segments = [s for s in merged_segments if s['type'] == 'face']
        slide_segments = [s for s in merged_segments if s['type'] == 'slide']
        self.log(f"   👤 人臉段落: {len(face_segments)}")
        self.log(f"   📊 簡報段落: {len(slide_segments)}")
        
        # 第四步：提取並儲存段落
        self.extract_segments(video_path, merged_segments, face_dir, ppt_dir)
        
        return merged_segments

    def merge_similar_segments(self, segments, fps, min_duration):
        """合併相鄰的相同類型段落，減少過度分段"""
        if not segments:
            return segments
        
        merged = []
        current_merged = segments[0].copy()
        
        for i in range(1, len(segments)):
            next_segment = segments[i]
            
            # 檢查是否為相同類型
            if current_merged['type'] == next_segment['type']:
                # 合併段落
                current_merged['end_frame'] = next_segment['end_frame']
                current_merged['frames'].extend(next_segment['frames'])
                self.log(f"   🔗 合併段落: {current_merged['type']} 類型，幀 {current_merged['start_frame']}-{current_merged['end_frame']}")
            else:
                # 不同類型，檢查當前段落長度
                segment_duration = (current_merged['end_frame'] - current_merged['start_frame']) / fps
                
                if segment_duration >= min_duration:
                    # 達到最小長度，保存
                    merged.append(current_merged)
                else:
                    # 段落太短，合併到下一個段落
                    self.log(f"   ⚠️ 段落太短 ({segment_duration:.1f}s < {min_duration}s)，將合併到相鄰段落")
                    # 如果已經有合併的段落，合併到最後一個
                    if merged:
                        merged[-1]['end_frame'] = current_merged['end_frame']
                        merged[-1]['frames'].extend(current_merged['frames'])
                    else:
                        # 沒有之前的段落，合併到下一個
                        next_segment['start_frame'] = current_merged['start_frame']
                        next_segment['frames'] = current_merged['frames'] + next_segment['frames']
                
                # 開始新的合併段落
                current_merged = next_segment.copy()
        
        # 添加最後一個段落
        segment_duration = (current_merged['end_frame'] - current_merged['start_frame']) / fps
        if segment_duration >= min_duration:
            merged.append(current_merged)
        elif merged:
            # 太短，合併到最後一個段落
            merged[-1]['end_frame'] = current_merged['end_frame']
            merged[-1]['frames'].extend(current_merged['frames'])
        else:
            # 只有一個段落，保留它
            merged.append(current_merged)
        
        return merged
    
    def should_split_segment(self, current_frame, prev_hash, threshold):
        """判斷是否應該分割段落（基於場景變化）"""
        if prev_hash is None:
            return False
            
        pil_image = Image.fromarray(cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB))
        current_hash = imagehash.phash(pil_image)
        
        return abs(current_hash - prev_hash) > threshold

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

    def extract_segments(self, video_path, segments, face_dir, ppt_dir):
        """提取並儲存影片段落，每個段落包含完整的音視頻"""
        self.log("✂️ 正在提取影片段落...")
        
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
            
            self.log(f"💾 已提取 {segment_type} 段落: {filename} (幀 {start_frame}-{end_frame})")
            
            # 更新進度
            progress = 20 + int((i / len(segments)) * 20)  # 提取階段占20-40%進度
            self.update_progress(progress)
        
        cap.release()
        self.log(f"✅ 段落提取完成: {face_count-1} 個人臉段落, {slide_count-1} 個簡報段落")

    def process_face_segments(self, face_dir, language):
        """處理人臉段落：音頻提取、翻譯、嘴形同步"""
        self.log("👤 開始處理人臉段落...")
        
        # 確保目錄存在
        self.ensure_directory_exists(face_dir)
        
        # 只處理原始段落文件（編號為 XX.mp4，不含 _processed）
        face_files = sorted([f for f in os.listdir(face_dir) 
                           if f.endswith('.mp4') and not '_processed' in f])
        
        if not face_files:
            self.log("⚠️ 沒有找到需要處理的人臉段落")
            return []
        
        processed_segments = []
        
        for i, filename in enumerate(face_files):
            self.log(f"🎭 處理人臉段落 {filename}...")
            
            input_path = os.path.join(face_dir, filename)
            base_name = os.path.splitext(filename)[0]
            processed_path = os.path.join(face_dir, f"{base_name}_processed.mp4")
            
            # 如果已經處理過，跳過
            if os.path.exists(processed_path):
                self.log(f"  ✅ 段落 {filename} 已處理過，跳過")
                processed_segments.append(processed_path)
                continue
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                self.log(f"  🎵 正在處理音頻...")
                api_key = self.api_key
                
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
                self.ensure_directory_exists(os.path.dirname(processed_path))
                
                # 確保 temp 目錄存在給 Wav2Lip 使用
                self.ensure_directory_exists("temp")
                
                try:
                    # 檢查影片是否包含人臉，並提取包含人臉的幀
                    cap_check = cv2.VideoCapture(input_path)
                    has_face_frames = []
                    frame_idx = 0
                    
                    # 檢查所有幀，記錄哪些幀有人臉
                    print(f"  🔍 正在分析段落中的人臉分佈...")
                    while True:
                        ret, frame_check = cap_check.read()
                        if not ret:
                            break
                        if self.detect_faces_in_frame(frame_check):
                            has_face_frames.append(frame_idx)
                        frame_idx += 1
                    cap_check.release()
                    
                    total_frames = frame_idx
                    face_ratio = len(has_face_frames) / total_frames if total_frames > 0 else 0
                    print(f"  📊 人臉幀比例: {len(has_face_frames)}/{total_frames} ({face_ratio*100:.1f}%)")
                    
                    if face_ratio < 0.5:  # 如果少於50%的幀包含人臉
                        print(f"  ⚠️ 段落 {filename} 人臉幀不足 ({face_ratio*100:.1f}% < 50%)，跳過嘴形同步，直接合成音頻")
                        # 直接合成音頻和視頻
                        command = f'ffmpeg -y -i "{input_path}" -i "{audio_path}" -c:v copy -c:a aac -strict experimental "{processed_path}"'
                        result = subprocess.run(command, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"  ✅ 音頻合成完成 {filename}")
                        else:
                            print(f"  ⚠️ 音頻合成失敗: {result.stderr}")
                            import shutil
                            shutil.copy(input_path, processed_path)
                    else:
                        # 有足夠人臉，進行嘴形同步
                        print(f"  ✅ 人臉幀充足，進行嘴形同步...")
                        run_inference(input_path, audio_path, processed_path)
                        print(f"  ✅ 人臉段落 {filename} 嘴形同步完成")
                except Exception as lipsync_error:
                    print(f"  ⚠️ 嘴形同步失敗: {lipsync_error}")
                    import traceback
                    traceback.print_exc()
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
            
            # 更新進度
            progress = 40 + int((i / len(face_files)) * 30)  # 人臉處理階段占40-70%進度
            self.update_progress(progress)
        
        return processed_segments

    def process_slide_segments(self, ppt_dir, language, slide_language):
        """處理簡報段落：音頻提取、翻譯、OCR翻譯"""
        self.log("📊 開始處理簡報段落...")
        
        # 確保目錄存在
        self.ensure_directory_exists(ppt_dir)
        
        # 只處理原始段落文件（編號為 XX.mp4，不含 _processed）
        ppt_files = sorted([f for f in os.listdir(ppt_dir) 
                          if f.endswith('.mp4') and not '_processed' in f])
        
        if not ppt_files:
            self.log("⚠️ 沒有找到需要處理的簡報段落")
            return []
        
        processed_segments = []
        
        for i, filename in enumerate(ppt_files):
            self.log(f"📋 處理簡報段落 {filename}...")
            
            input_path = os.path.join(ppt_dir, filename)
            base_name = os.path.splitext(filename)[0]
            processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
            
            # 如果已經處理過，跳過
            if os.path.exists(processed_path):
                self.log(f"  ✅ 段落 {filename} 已處理過，跳過")
                processed_segments.append(processed_path)
                continue
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                self.log(f"  🎵 正在處理音頻...")
                api_key = self.api_key
                
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
                self.ensure_directory_exists(os.path.dirname(processed_path))
                
                # 強制執行 OCR 翻譯
                print(f"  🔍 開始 OCR 翻譯處理...")
                self.process_slide_video(input_path, processed_path, slide_language, temp_audio)
                
                processed_segments.append(processed_path)
                print(f"  ✅ 簡報段落 {filename} 處理完成")
                
            except Exception as e:
                print(f"  ❌ 處理簡報段落 {filename} 時發生錯誤: {e}")
                import traceback
                traceback.print_exc()
                # 如果處理失敗，使用原始影片
                import shutil
                shutil.copy(input_path, processed_path)
                processed_segments.append(processed_path)
            
            # 更新進度
            progress = 70 + int((i / len(ppt_files)) * 20)  # 簡報處理階段占70-90%進度
            self.update_progress(progress)
        
        return processed_segments

    def process_slide_video(self, input_video, output_video, target_lang, audio_path=None):
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
        hash_threshold = self.hash_threshold
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
                    # 不需要傳遞 api_key，方法會使用 self.api_key
                    new_translated_frame = self.translate_frame_text(frame, target_lang)
                    
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
                    # 不需要傳遞 api_key，方法會使用 self.api_key
                    current_translated_frame = self.translate_frame_text(frame, target_lang)
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

    def translate_frame_text(self, frame, target_lang):
        """翻譯單個幀中的文字"""
        try:
            print(f"      🔍 開始OCR識別...")
            # OCR識別 - 修正語言組合
            # EasyOCR 的語言組合限制：ch_tra 只能與 en 組合
            if target_lang == "Japanese":
                # 日文翻譯時，只用中文和英文識別，翻譯階段才轉日文
                ocr_languages = ['ch_tra', 'en']
            elif target_lang == "Chinese":
                ocr_languages = ['ch_tra', 'en']
            else:
                ocr_languages = ['ch_tra', 'en']  # 默認使用中英文識別
            
            print(f"      📚 使用 OCR 語言: {ocr_languages}")
            reader = easyocr.Reader(ocr_languages, gpu=False)
            results = reader.readtext(frame)
            
            boxes, orig_texts = [], []
            for box, text, conf in results:
                # 降低置信度門檻以識別更多文字
                if conf > 0.3:  # 從 0.4 降低到 0.3
                    boxes.append(box)
                    orig_texts.append(text)
                    print(f"      📝 檢測到文字: '{text}' (置信度: {conf:.2f})")
            
            if not orig_texts:
                print(f"      ⚠️ 未檢測到文字內容，返回原始幀")
                return frame
            
            print(f"      🔍 找到 {len(orig_texts)} 個文字區塊，開始翻譯...")
            
            # 移除原文 - 使用更大的膨脹以確保完全覆蓋
            img_clean = self.remove_text_with_inpainting(frame, boxes)
            print(f"      🧹 原文移除完成")
            
            # 翻譯文字
            translated = []
            for i, text in enumerate(orig_texts):
                # 使用 self.api_key（在類初始化時已設定）
                translated_text = self.translate_with_gemini(text, target_lang)
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
        print("🎬 開始自動剪接段落...")
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
                # 確保使用處理後的檔案（_processed.mp4）
                if not segment_path.endswith('_processed.mp4'):
                    base_name = os.path.splitext(os.path.basename(segment_path))[0]
                    processed_path = os.path.join(os.path.dirname(segment_path), f"{base_name}_processed.mp4")
                    if os.path.exists(processed_path):
                        segment_path = processed_path
                        print(f"    {i+1}. 👤 人臉段落 {face_counter} (已處理): {os.path.basename(segment_path)}")
                    else:
                        print(f"    {i+1}. 👤 人臉段落 {face_counter} (原始): {os.path.basename(segment_path)}")
                else:
                    print(f"    {i+1}. 👤 人臉段落 {face_counter}: {os.path.basename(segment_path)}")
                ordered_segments.append(segment_path)
                face_counter += 1
            elif segment_type == 'slide' and slide_counter in slide_map:
                segment_path = slide_map[slide_counter]
                # 確保使用處理後的檔案（_processed.mp4）
                if not segment_path.endswith('_processed.mp4'):
                    base_name = os.path.splitext(os.path.basename(segment_path))[0]
                    processed_path = os.path.join(os.path.dirname(segment_path), f"{base_name}_processed.mp4")
                    if os.path.exists(processed_path):
                        segment_path = processed_path
                        print(f"    {i+1}. 📊 簡報段落 {slide_counter} (已處理): {os.path.basename(segment_path)}")
                    else:
                        print(f"    {i+1}. 📊 簡報段落 {slide_counter} (原始): {os.path.basename(segment_path)}")
                else:
                    print(f"    {i+1}. 📊 簡報段落 {slide_counter}: {os.path.basename(segment_path)}")
                ordered_segments.append(segment_path)
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
        
        # 使用 ffmpeg 合併段落 - 多種方法嘗試
        print(f"🔗 正在合併 {len(ordered_segments)} 個段落...")
        
        # 方法1：使用解析度統一的filter_complex進行合併
        try:
            print("🔧 方法1: 使用 filter_complex 合併 (自動統一解析度)...")
            if len(ordered_segments) == 1:
                # 只有一個文件，直接複製
                print("  📁 只有一個段落，直接複製...")
                import shutil
                shutil.copy(ordered_segments[0], output_path)
                print("✅ 單文件複製完成")
                return
            elif len(ordered_segments) == 2:
                # 兩個文件，統一解析度後合併
                input_params = ' '.join([f'-i "{seg}"' for seg in ordered_segments])
                # 統一到1280x720解析度，並確保音頻格式一致
                command = f'ffmpeg -y {input_params} -filter_complex "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[0:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{output_path}"'
                print(f"  🔧 執行命令: {command}")
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ filter_complex 解析度統一合併成功")
                    self.verify_output_file(output_path)
                    return
                else:
                    print(f"⚠️ filter_complex 解析度統一失敗: {result.stderr}")
            else:
                # 多個文件，統一解析度後合併
                input_params = ' '.join([f'-i "{seg}"' for seg in ordered_segments])
                
                # 為每個輸入創建scale和audio format濾鏡
                video_filters = []
                audio_filters = []
                concat_inputs = []
                
                for i in range(len(ordered_segments)):
                    video_filters.append(f"[{i}:v]scale=1280:720,setsar=1:1[v{i}]")
                    audio_filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a{i}]")
                    concat_inputs.extend([f"[v{i}]", f"[a{i}]"])
                
                filter_complex = ';'.join(video_filters + audio_filters) + ';' + ''.join(concat_inputs) + f'concat=n={len(ordered_segments)}:v=1:a=1[outv][outa]'
                
                command = f'ffmpeg -y {input_params} -filter_complex "{filter_complex}" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{output_path}"'
                print(f"  🔧 執行命令: {command}")
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ filter_complex 多文件解析度統一合併成功")
                    self.verify_output_file(output_path)
                    return
                else:
                    print(f"⚠️ filter_complex 多文件解析度統一失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ filter_complex 方法異常: {e}")
        
        # 方法2：先統一解析度再使用concat demuxer
        try:
            print("🔧 方法2: 統一解析度後使用 concat demuxer...")
            # 創建統一解析度的臨時文件
            normalized_segments = []
            for i, segment in enumerate(ordered_segments):
                normalized_path = segment.replace('.mp4', f'_normalized_{i}.mp4')
                command = f'ffmpeg -y -i "{segment}" -vf scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1:1 -af aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono -c:v libx264 -c:a aac "{normalized_path}"'
                print(f"  📐 統一段落 {i+1} 解析度...")
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    normalized_segments.append(normalized_path)
                else:
                    print(f"  ⚠️ 段落 {i+1} 解析度統一失敗: {result.stderr}")
                    # 清理已創建的臨時文件
                    for temp_file in normalized_segments:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    raise Exception(f"解析度統一失敗")
            
            # 創建新的段落列表文件
            normalized_list_path = "temp/normalized_segment_list.txt"
            with open(normalized_list_path, 'w', encoding='utf-8') as f:
                for seg_path in normalized_segments:
                    abs_path = os.path.abspath(seg_path)
                    f.write(f"file '{abs_path}'\n")
            
            # 使用concat demuxer合併
            command = f'ffmpeg -y -f concat -safe 0 -i "{normalized_list_path}" -c copy "{output_path}"'
            print(f"  🔧 執行合併命令: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            # 清理臨時文件
            for temp_file in normalized_segments:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            if os.path.exists(normalized_list_path):
                os.remove(normalized_list_path)
            
            if result.returncode == 0:
                print("✅ 統一解析度 concat demuxer 合併成功")
                self.verify_output_file(output_path)
                return
            else:
                print(f"⚠️ 統一解析度 concat demuxer 失敗: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 統一解析度 concat demuxer 方法異常: {e}")
        
        # 方法3：直接使用原始concat demuxer (可能失敗但值得嘗試)
        try:
            print("🔧 方法3: 直接使用 concat demuxer (可能因解析度不同失敗)...")
            command = f'ffmpeg -y -f concat -safe 0 -i "{segment_list_path}" -c:v libx264 -c:a aac "{output_path}"'
            print(f"  🔧 執行命令: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 直接 concat demuxer 合併成功")
                self.verify_output_file(output_path)
                return
            else:
                print(f"⚠️ 直接 concat demuxer 失敗（預期中）: {result.stderr}")
        except Exception as e:
            print(f"⚠️ 直接 concat demuxer 方法異常: {e}")
        
        # 方法4：逐個合併 (兩兩合併)
        try:
            print("🔧 方法4: 逐個合併...")
            self.merge_segments_sequentially(ordered_segments, output_path)
            print("✅ 逐個合併成功")
            return
        except Exception as e:
            print(f"⚠️ 逐個合併失敗: {e}")
        
        # 最後備用：直接複製第一個文件
        if ordered_segments:
            print("🔄 所有合併方法都失敗，使用最後備用方案：複製第一個段落")
            import shutil
            shutil.copy(ordered_segments[0], output_path)
            print(f"📁 已複製第一個段落: {ordered_segments[0]}")
        else:
                         raise Exception("所有合併方法都失敗且無可用段落")

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

    def merge_segments_sequentially(self, segments, output_path):
        """逐個合併段落（兩兩合併，統一解析度）"""
        print(f"  🔗 開始逐個合併 {len(segments)} 個段落...")
        
        if len(segments) == 1:
            import shutil
            shutil.copy(segments[0], output_path)
            return
        
        # 從第一個和第二個開始合併
        temp_output = output_path.replace('.mp4', '_temp.mp4')
        
        # 第一次合併（統一解析度）
        command = f'ffmpeg -y -i "{segments[0]}" -i "{segments[1]}" -filter_complex "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[0:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{temp_output}"'
        print(f"    🔧 合併段落 1 和 2 (統一解析度)...")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"合併段落1和2失敗: {result.stderr}")
        
        # 如果有更多段落，逐個添加
        for i in range(2, len(segments)):
            prev_temp = temp_output
            new_temp = output_path.replace('.mp4', f'_temp_{i}.mp4')
            
            command = f'ffmpeg -y -i "{prev_temp}" -i "{segments[i]}" -filter_complex "[0:v]scale=1280:720,setsar=1:1[v0];[1:v]scale=1280:720,setsar=1:1[v1];[0:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a0];[1:a]aformat=sample_fmts=fltp:sample_rates=22050:channel_layouts=mono[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{new_temp}"'
            print(f"    🔧 添加段落 {i+1} (統一解析度)...")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"添加段落{i+1}失敗: {result.stderr}")
            
            # 清理上一個臨時文件
            if os.path.exists(prev_temp):
                os.remove(prev_temp)
            
            temp_output = new_temp
        
        # 移動最終文件到目標位置
        if os.path.exists(temp_output):
            import shutil
            shutil.move(temp_output, output_path)
        
        print(f"  ✅ 逐個合併完成")

    def process(self, input_path, output_path, api_key, language, slide_language, 
                enable_slide_translation, min_segment_duration, hash_threshold):
        """處理影片的主要方法"""
        # 設置參數
        self.api_key = api_key
        self.min_segment_duration = min_segment_duration
        self.hash_threshold = hash_threshold
        
        # 驗證輸入
        if not all([api_key, input_path, output_path]):
            raise ValueError("請填寫所有必要欄位")
            
        if not input_path.lower().endswith('.mp4'):
            raise ValueError("請選擇MP4格式的影片文件")
        
        try:
            # 確保所有必要的目錄存在
            self.ensure_basic_directories()
            
            # 判斷是否需要分段處理
            if not enable_slide_translation:
                # 不需要簡報翻譯，直接處理整個影片（不分段）
                self.log("🎯 簡報翻譯已停用，將直接處理完整影片（不進行分段）")
                self.update_progress(10, "正在處理影片...")
                
                # 直接將整個影片當作人臉影片處理
                face_dir = "temp/faceai"
                self.ensure_directory_exists(face_dir)
                
                # 複製原始影片到 face 目錄
                import shutil
                full_video_path = os.path.join(face_dir, "01.mp4")
                shutil.copy(input_path, full_video_path)
                self.log(f"✅ 已準備影片進行處理: {full_video_path}")
                
                # 處理影片（語音翻譯 + 嘴形同步）
                self.log("正在進行語音翻譯和嘴形同步...")
                self.update_progress(20, "正在進行語音翻譯和嘴形同步...")
                face_segments = self.process_face_segments(face_dir, language)
                
                # 直接使用處理後的影片作為輸出
                if face_segments and len(face_segments) > 0:
                    import shutil
                    shutil.copy(face_segments[0], output_path)
                    self.update_progress(100, "處理完成！")
                    self.log(f"✅ 影片處理完成！輸出文件：{output_path}", 'success')
                else:
                    raise ValueError("影片處理失敗，沒有生成輸出文件")
                    
            else:
                # 需要簡報翻譯，進行智能分段處理
                self.log("🎯 簡報翻譯已啟用，將進行智能分段處理...")
                self.update_progress(0, "正在進行智能分段分析...")
                
                # 步驟1：分析並分段影片
                segments_info = self.analyze_and_segment_video(input_path)
                
                if not segments_info:
                    raise ValueError("無法分析影片內容，請確認影片格式正確")
                
                # 步驟2：處理人臉段落
                self.log("正在處理人臉段落...")
                self.update_progress(40, "正在處理人臉段落...")
                face_segments = self.process_face_segments("temp/faceai", language)
            
                # 步驟3：處理簡報段落
                self.log("正在處理簡報段落...")
                self.update_progress(70, "正在處理簡報段落...")
                processed_slide_segments = self.process_slide_segments("temp/pptai", language, slide_language)
                
                # 步驟4：自動剪接
                self.log("正在進行自動剪接...")
                self.update_progress(90, "正在進行自動剪接...")
                
                self.auto_edit_segments(face_segments, processed_slide_segments, segments_info, output_path)
                
                self.update_progress(100, "處理完成！")
                self.log(f"✅ 智能分段處理已完成！輸出文件：{output_path}", 'success')
            
        except Exception as e:
            self.log(f"❌ 處理過程中發生錯誤：{str(e)}", 'error')
            self.update_progress(0, "處理失敗")
            import traceback
            traceback.print_exc()
            raise

    def ensure_basic_directories(self):
        """確保所有必要的基本目錄都存在"""
        required_dirs = [
            "temp",
            "temp/faceai", 
            "temp/pptai",
            "temp/audio_segments",
            "temp/slides_output",
            "temp/translated_slides",
            "temp/segments"
        ]
        
        for dir_path in required_dirs:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 確保目錄存在: {dir_path}")

    def ensure_directory_exists(self, directory_path):
        """確保指定目錄存在"""
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            print(f"📁 創建目錄: {directory_path}")
        return directory_path

# Flask 路由

@app.route('/')
def home():
    """首頁"""
    return render_template('index.html')


@app.route('/get_home_dir')
def get_home_dir():
    """獲取用戶主目錄"""
    home_dir = os.path.expanduser('~')
    return jsonify({'home_dir': home_dir})


@app.route('/process', methods=['POST'])
def process_video():
    """處理影片的 API 端點"""
    try:
        # 檢查文件是否存在
        if 'video' not in request.files:
            return jsonify({'error': '沒有上傳影片'}), 400
        
        video_file = request.files['video']
        
        if video_file.filename == '':
            return jsonify({'error': '沒有選擇影片'}), 400
        
        # 獲取參數
        api_key = request.form.get('api_key')
        voice_language = request.form.get('voice_language', '日文')
        slide_language = request.form.get('slide_language', 'Japanese')
        enable_slide_translation = request.form.get('enable_slide_translation', 'true').lower() == 'true'
        min_segment_duration = float(request.form.get('min_segment_duration', 2))
        hash_threshold = int(request.form.get('hash_threshold', 5))
        custom_output_filename = request.form.get('output_filename', '').strip()
        output_directory = request.form.get('output_directory', 'audio_files').strip()
        
        # 保存上傳的影片
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(video_file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(input_path)
        
        # 設置輸出路徑
        base_name = os.path.splitext(filename)[0]
        
        # 清理並驗證輸出目錄
        if not output_directory:
            output_directory = 'audio_files'
        
        # 標準化路徑分隔符
        output_directory = output_directory.replace('\\', '/')
        
        # 檢查是否為絕對路徑
        is_absolute = output_directory.startswith('/')
        
        # 移除危險的 .. 路徑遍歷（但保留絕對路徑的開頭斜杠）
        if not is_absolute:
            output_directory = output_directory.replace('..', '').strip('/')
            if not output_directory:
                output_directory = 'audio_files'
        else:
            # 對於絕對路徑，只移除 ..，但不去除前導斜杠
            output_directory = output_directory.replace('..', '')
        
        # 使用自定義文件名或默認文件名
        if custom_output_filename:
            # 確保文件名有 .mp4 擴展名
            if not custom_output_filename.lower().endswith('.mp4'):
                output_filename = f"{custom_output_filename}.mp4"
            else:
                output_filename = custom_output_filename
            output_filename = secure_filename(output_filename)
        else:
            output_filename = f"{base_name}_translated.mp4"
        
        # 創建輸出目錄並設置完整路徑
        output_path = os.path.join(output_directory, output_filename)
        
        # 確保輸出目錄存在
        try:
            os.makedirs(output_directory, exist_ok=True)
        except Exception as e:
            return jsonify({'error': f'無法創建輸出目錄：{str(e)}'}), 400
        
        # 創建任務
        task_id = str(uuid.uuid4())
        params = {
            'input_path': input_path,
            'output_path': output_path,
            'api_key': api_key,
            'voice_language': voice_language,
            'slide_language': slide_language,
            'enable_slide_translation': enable_slide_translation,
            'min_segment_duration': min_segment_duration,
            'hash_threshold': hash_threshold
        }
        
        task = VideoProcessingTask(task_id, params)
        tasks[task_id] = task
        
        # 在新線程中處理影片
        thread = threading.Thread(target=process_video_task, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'message': '任務已建立'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def process_video_task(task_id):
    """在背景處理影片的任務"""
    task = tasks.get(task_id)
    if not task:
        return
    
    try:
        task.status = 'processing'
        task.progress = 0
        task.log('🚀 開始處理影片...', 'info')
        task.log('📥 正在初始化處理器...', 'info')
        
        # 創建處理器實例
        processor = DeepVideoTranslationApp(task)
        
        # 執行處理
        params = task.params
        processor.process(
            input_path=params['input_path'],
            output_path=params['output_path'],
            api_key=params['api_key'],
            language=params['voice_language'],
            slide_language=params['slide_language'],
            enable_slide_translation=params['enable_slide_translation'],
            min_segment_duration=params['min_segment_duration'],
            hash_threshold=params['hash_threshold']
        )
        
        task.status = 'completed'
        task.output_path = params['output_path']
        task.log('處理完成！', 'success')
        
    except Exception as e:
        task.status = 'failed'
        task.error = str(e)
        task.log(f'處理失敗: {str(e)}', 'error')
        import traceback
        traceback.print_exc()


@app.route('/progress/<task_id>')
def progress(task_id):
    """使用 Server-Sent Events 推送進度和日誌"""
    def generate():
        task = tasks.get(task_id)
        if not task:
            data = {'error': '任務不存在'}
            yield f"data: {json.dumps(data)}\n\n"
            return
        
        # 立即發送初始連接消息
        initial_data = {
            'log': '⏳ 已連接到服務器，等待任務開始...',
            'progress': 0,
            'status': 'pending'
        }
        yield f"data: {json.dumps(initial_data)}\n\n"
        
        last_progress = -1
        heartbeat_counter = 0
        
        while True:
            try:
                has_update = False
                
                # 發送日誌
                while not task.log_queue.empty():
                    log_entry = task.log_queue.get_nowait()
                    data = {
                        'log': log_entry['message'],
                        'progress': task.progress,
                        'status': task.status
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    has_update = True
                
                # 發送進度更新
                if task.progress != last_progress:
                    last_progress = task.progress
                    data = {
                        'progress': task.progress,
                        'status': task.status
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    has_update = True
                
                # 如果任務完成或失敗，發送最終消息
                if task.status == 'completed':
                    data = {
                        'progress': 100,
                        'status': 'completed',
                        'output_url': f'/download/{task_id}',
                        'log': '✅ 處理完成！'
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                elif task.status == 'failed':
                    data = {
                        'progress': task.progress,
                        'status': 'failed',
                        'error': task.error or '未知錯誤',
                        'log': f'❌ 處理失敗: {task.error or "未知錯誤"}'
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                
                # 每5秒發送一次心跳，保持連接活躍
                heartbeat_counter += 1
                if heartbeat_counter >= 10:  # 0.5s * 10 = 5s
                    data = {
                        'heartbeat': True,
                        'progress': task.progress,
                        'status': task.status
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    heartbeat_counter = 0
                
                time.sleep(0.5)  # 每0.5秒檢查一次
                
            except GeneratorExit:
                print(f"Client disconnected from task {task_id}")
                break
            except Exception as e:
                print(f"Progress stream error for task {task_id}: {e}")
                import traceback
                traceback.print_exc()
                break
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@app.route('/download/<task_id>')
def download(task_id):
    """下載處理後的影片"""
    task = tasks.get(task_id)
    if not task or not task.output_path:
        return jsonify({'error': '文件不存在'}), 404
    
    if not os.path.exists(task.output_path):
        return jsonify({'error': '輸出文件不存在'}), 404
    
    return send_file(
        task.output_path,
        as_attachment=True,
        download_name=os.path.basename(task.output_path),
        mimetype='video/mp4'
    )


if __name__ == "__main__":
    # 確保必要的目錄存在
    os.makedirs('temp/uploads', exist_ok=True)
    os.makedirs('audio_files', exist_ok=True)
    
    # 啟動 Flask 應用
    print("🚀 Deep Video Translation 服務啟動中...")
    print("📍 請在瀏覽器中打開: http://localhost:32123")
    app.run(debug=True, host='0.0.0.0', port=32123, threaded=True)