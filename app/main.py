import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import urllib.request

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

class DeepVideoTranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deep Video Translation with Smart Segmentation")
        self.root.geometry("1000x800")
        
        # 設置字體路徑
        self.setup_fonts()
        
        # 確保基本目錄存在
        self.ensure_basic_directories()
        
        # 創建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # API Key 輸入
        ttk.Label(main_frame, text="Gemini API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.api_key_var, width=50).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # 輸入影片選擇
        ttk.Label(main_frame, text="輸入影片:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.input_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.input_path_var, width=50).grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_input).grid(row=1, column=2, padx=5)
        
        # 語音翻譯語言選擇
        ttk.Label(main_frame, text="語音翻譯語言:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar(value="日文")
        language_combo = ttk.Combobox(main_frame, textvariable=self.language_var, values=["日文", "英文", "中文"], width=47)
        language_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 投影片翻譯選項
        self.slide_translation_var = tk.BooleanVar(value=True)
        slide_check = tk.Checkbutton(main_frame, text="啟用投影片文字翻譯", variable=self.slide_translation_var, command=self.toggle_slide_options)
        slide_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 投影片翻譯參數框架
        self.slide_frame = ttk.LabelFrame(main_frame, text="投影片翻譯設定", padding="5")
        self.slide_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 投影片翻譯語言
        ttk.Label(self.slide_frame, text="投影片翻譯語言:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.slide_language_var = tk.StringVar(value="Japanese")
        slide_lang_combo = ttk.Combobox(self.slide_frame, textvariable=self.slide_language_var, 
                                       values=["Japanese", "English", "Chinese"], width=20)
        slide_lang_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 分段參數設定
        ttk.Label(self.slide_frame, text="最小段落長度(秒):").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.min_segment_duration_var = tk.StringVar(value="2")
        ttk.Entry(self.slide_frame, textvariable=self.min_segment_duration_var, width=10).grid(row=0, column=3, padx=5)
        
        # Hash 差異門檻
        ttk.Label(self.slide_frame, text="場景切換門檻:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.hash_threshold_var = tk.StringVar(value="5")
        ttk.Entry(self.slide_frame, textvariable=self.hash_threshold_var, width=10).grid(row=1, column=1, padx=5)
        
        # 輸出文件選擇
        ttk.Label(main_frame, text="輸出文件:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_path_var, width=50).grid(row=5, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_output).grid(row=5, column=2, padx=5)
        
        # 進度條
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=3, pady=20)
        
        # 開始按鈕
        ttk.Button(main_frame, text="開始智能分段處理", command=self.process).grid(row=7, column=0, columnspan=3, pady=10)
        
        # 狀態標籤
        self.status_var = tk.StringVar()
        self.status_var.set("準備就緒")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=8, column=0, columnspan=3, pady=5)

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

    def toggle_slide_options(self):
        """切換投影片選項顯示/隱藏"""
        if self.slide_translation_var.get():
            self.slide_frame.grid()
        else:
            self.slide_frame.grid_remove()

    def browse_input(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4")]
        )
        if filename:
            self.input_path_var.set(filename)
            # 自動設置輸出路徑
            base_name = os.path.splitext(filename)[0]
            self.output_path_var.set(f"{base_name}_translated.mp4")

    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")]
        )
        if filename:
            self.output_path_var.set(filename)

    # 投影片翻譯功能
    def translate_with_gemini(self, text, target_lang="Japanese"):
        """使用 Gemini API 翻譯文字"""
        api_key = self.api_key_var.get()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        lang_prompts = {
            "Japanese": "請將以下文字翻譯成日文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "English": "請將以下文字翻譯成英文，只輸出翻譯結果，不要有任何解釋或額外文字：",
            "Chinese": "請將以下文字翻譯成中文，只輸出翻譯結果，不要有任何解釋或額外文字："
        }
        
        prompt = lang_prompts.get(target_lang, lang_prompts["Japanese"]) + text
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

        frame_interval = int(self.frame_interval_var.get())
        hash_threshold = int(self.hash_threshold_var.get())

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
                self.progress['value'] = progress
                self.root.update()

        cap.release()
        print(f"總共處理了 {processed_slides} 張投影片")
        return translated_dir, slide_frame_mapping

    def create_translated_video(self, original_video, translated_slides_dir, slide_frame_mapping, output_path, audio_path):
        """將翻譯後的投影片合成到影片中，並確保音頻正確"""
        frame_interval = int(self.frame_interval_var.get())
        hash_threshold = int(self.hash_threshold_var.get())
        
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
        """分析影片並智能分段，分離人臉和簡報片段"""
        print("🔍 開始分析影片內容並進行智能分段...")
        
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
        
        min_duration = float(self.min_segment_duration_var.get())
        min_frames = int(fps * min_duration)
        hash_threshold = int(self.hash_threshold_var.get())
        
        # 第一步：分析整個影片的內容類型
        print("📊 正在分析影片內容類型...")
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
                progress = int((frame_count / total_frames) * 20)  # 分析階段占20%進度
                self.progress['value'] = progress
                self.root.update()
        
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
        self.extract_segments(video_path, segments, face_dir, ppt_dir)
        
        return segments

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
        print("✂️ 正在提取影片段落...")
        
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
            progress = 20 + int((i / len(segments)) * 20)  # 提取階段占20-40%進度
            self.progress['value'] = progress
            self.root.update()
        
        cap.release()
        print(f"✅ 段落提取完成: {face_count-1} 個人臉段落, {slide_count-1} 個簡報段落")

    def process_face_segments(self, face_dir, language):
        """處理人臉段落：音頻提取、翻譯、嘴形同步"""
        print("👤 開始處理人臉段落...")
        
        # 確保目錄存在
        self.ensure_directory_exists(face_dir)
        
        face_files = sorted([f for f in os.listdir(face_dir) if f.endswith('.mp4')])
        processed_segments = []
        
        for i, filename in enumerate(face_files):
            print(f"🎭 處理人臉段落 {filename}...")
            
            input_path = os.path.join(face_dir, filename)
            base_name = os.path.splitext(filename)[0]
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                print(f"  🎵 正在處理音頻...")
                api_key = self.api_key_var.get()
                
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
                    run_inference(input_path, audio_path, processed_path)
                    print(f"  ✅ 人臉段落 {filename} 處理完成")
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
            
            # 更新進度
            progress = 40 + int((i / len(face_files)) * 30)  # 人臉處理階段占40-70%進度
            self.progress['value'] = progress
            self.root.update()
        
        return processed_segments

    def process_slide_segments(self, ppt_dir, language, slide_language):
        """處理簡報段落：音頻提取、翻譯、OCR翻譯"""
        print("📊 開始處理簡報段落...")
        
        # 確保目錄存在
        self.ensure_directory_exists(ppt_dir)
        
        ppt_files = sorted([f for f in os.listdir(ppt_dir) if f.endswith('.mp4')])
        processed_segments = []
        
        for i, filename in enumerate(ppt_files):
            print(f"📋 處理簡報段落 {filename}...")
            
            input_path = os.path.join(ppt_dir, filename)
            base_name = os.path.splitext(filename)[0]
            
            try:
                # 1. 語音轉文字並翻譯（直接使用段落文件，因為已包含音頻）
                print(f"  🎵 正在處理音頻...")
                api_key = self.api_key_var.get()
                
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
                
                self.process_slide_video(input_path, processed_path, slide_language, temp_audio)
                
                processed_segments.append(processed_path)
                print(f"  ✅ 簡報段落 {filename} 處理完成")
                
            except Exception as e:
                print(f"  ❌ 處理簡報段落 {filename} 時發生錯誤: {e}")
                # 如果處理失敗，使用原始影片
                processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
                import shutil
                shutil.copy(input_path, processed_path)
                processed_segments.append(processed_path)
            
            # 更新進度
            progress = 70 + int((i / len(ppt_files)) * 20)  # 簡報處理階段占70-90%進度
            self.progress['value'] = progress
            self.root.update()
        
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
        hash_threshold = int(self.hash_threshold_var.get())
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

    def process(self):
        # 獲取輸入值
        api_key = self.api_key_var.get()
        input_path = self.input_path_var.get()
        language = self.language_var.get()
        output_path = self.output_path_var.get()
        enable_slide_translation = self.slide_translation_var.get()
        
        # 驗證輸入
        if not all([api_key, input_path, output_path]):
            messagebox.showerror("錯誤", "請填寫所有必要欄位")
            return
            
        if not input_path.lower().endswith('.mp4'):
            messagebox.showerror("錯誤", "請選擇MP4格式的影片文件")
            return
        
        try:
            # 確保所有必要的目錄存在
            self.ensure_basic_directories()
            
            # 更新狀態
            self.status_var.set("正在進行智能分段分析...")
            self.progress['value'] = 0
            self.root.update()
            
            # 步驟1：分析並分段影片
            segments_info = self.analyze_and_segment_video(input_path)
            
            if not segments_info:
                messagebox.showerror("錯誤", "無法分析影片內容，請確認影片格式正確")
                return
            
            # 步驟2：處理人臉段落
            self.status_var.set("正在處理人臉段落...")
            face_segments = self.process_face_segments("temp/faceai", language)
            
            # 步驟3：處理簡報段落
            processed_slide_segments = []
            if enable_slide_translation:
                self.status_var.set("正在處理簡報段落...")
                slide_language = self.slide_language_var.get()
                processed_slide_segments = self.process_slide_segments("temp/pptai", language, slide_language)
            else:
                # 如果不啟用簡報翻譯，直接處理音頻但不翻譯投影片內容
                print("📋 簡報翻譯已停用，僅處理音頻...")
                ppt_dir = "temp/pptai"
                self.ensure_directory_exists(ppt_dir)
                ppt_files = sorted([f for f in os.listdir(ppt_dir) if f.endswith('.mp4')])
                
                for j, filename in enumerate(ppt_files):
                    input_path_seg = os.path.join(ppt_dir, filename)
                    base_name = os.path.splitext(filename)[0]
                    processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
                    
                    try:
                        print(f"📋 處理簡報音頻 {filename}...")
                        # 處理音頻（直接使用段落文件，因為已包含音頻）
                        api_key = self.api_key_var.get()
                        
                        try:
                            translated_text = voice(input_path_seg, api_key, language)
                        except Exception as audio_error:
                            print(f"  ⚠️ 音頻轉文字失敗: {audio_error}")
                            translated_text = ""
                        
                        if translated_text and translated_text.strip():
                            print(f"  📝 翻譯結果: {translated_text}")
                            temp_audio = os.path.join(ppt_dir, f"{base_name}_audio.wav")
                            self.ensure_directory_exists(os.path.dirname(temp_audio))
                            
                            try:
                                # 使用段落文件本身作為參考音頻進行語音克隆
                                xttsv(translated_text, input_path_seg, temp_audio, language)
                                
                                # 合成音頻和視頻（保持原始視頻內容，只替換音頻）
                                command = f'ffmpeg -y -i "{input_path_seg}" -i "{temp_audio}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{processed_path}"'
                                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                                if result.returncode != 0:
                                    print(f"  ⚠️ 音頻合成失敗，使用原始視頻: {result.stderr}")
                                    import shutil
                                    shutil.copy(input_path_seg, processed_path)
                                else:
                                    print(f"  ✅ 音頻替換完成")
                            except Exception as tts_error:
                                print(f"  ⚠️ 語音克隆失敗: {tts_error}")
                                import shutil
                                shutil.copy(input_path_seg, processed_path)
                        else:
                            # 沒有音頻，直接複製
                            print(f"  ⚠️ 沒有檢測到語音內容")
                            import shutil
                            shutil.copy(input_path_seg, processed_path)
                        
                        processed_slide_segments.append(processed_path)
                        
                    except Exception as e:
                        print(f"  ❌ 處理簡報音頻失敗: {e}")
                        import shutil
                        shutil.copy(input_path_seg, processed_path)
                        processed_slide_segments.append(processed_path)
                    
                    # 更新進度
                    progress = 70 + int((j / len(ppt_files)) * 20)
                    self.progress['value'] = progress
                    self.root.update()
            
            # 步驟4：自動剪接
            self.status_var.set("正在進行自動剪接...")
            self.progress['value'] = 90
            self.root.update()
            
            self.auto_edit_segments(face_segments, processed_slide_segments, segments_info, output_path)
            
            self.progress['value'] = 100
            self.status_var.set("處理完成！")
            messagebox.showinfo("完成", f"智能分段處理已完成！\n輸出文件：{output_path}")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"處理過程中發生錯誤：{str(e)}")
            self.status_var.set("處理失敗")
            self.progress['value'] = 0
            print(f"詳細錯誤信息: {e}")
            import traceback
            traceback.print_exc()

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

def main():
    root = tk.Tk()
    app = DeepVideoTranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()