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
        self.root.title("Deep Video Translation with Slide Translation")
        self.root.geometry("1000x800")
        
        # 設置字體路徑
        self.setup_fonts()
        
        # 創建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # API Key 輸入
        ttk.Label(main_frame, text="Gemini API Key:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.api_key_var, width=50).grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # 輸入音檔選擇
        ttk.Label(main_frame, text="輸入音檔:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.input_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.input_path_var, width=50).grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_input).grid(row=1, column=2, padx=5)
        
        # 語音翻譯語言選擇
        ttk.Label(main_frame, text="語音翻譯語言:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar(value="日文")
        language_combo = ttk.Combobox(main_frame, textvariable=self.language_var, values=["日文", "英文", "中文"], width=47)
        language_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 投影片翻譯選項
        self.slide_translation_var = tk.BooleanVar()
        slide_check = tk.Checkbutton(main_frame, text="啟用投影片文字翻譯", variable=self.slide_translation_var, command=self.toggle_slide_options)
        slide_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 投影片翻譯參數框架
        self.slide_frame = ttk.LabelFrame(main_frame, text="投影片翻譯設定", padding="5")
        self.slide_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.slide_frame.grid_remove()  # 初始隱藏
        
        # 投影片翻譯語言
        ttk.Label(self.slide_frame, text="投影片翻譯語言:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.slide_language_var = tk.StringVar(value="Japanese")
        slide_lang_combo = ttk.Combobox(self.slide_frame, textvariable=self.slide_language_var, 
                                       values=["Japanese", "English", "Chinese"], width=20)
        slide_lang_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 幀間隔設定
        ttk.Label(self.slide_frame, text="幀間隔:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.frame_interval_var = tk.StringVar(value="15")
        ttk.Entry(self.slide_frame, textvariable=self.frame_interval_var, width=10).grid(row=0, column=3, padx=5)
        
        # Hash 差異門檻
        ttk.Label(self.slide_frame, text="差異門檻:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.hash_threshold_var = tk.StringVar(value="5")
        ttk.Entry(self.slide_frame, textvariable=self.hash_threshold_var, width=10).grid(row=1, column=1, padx=5)
        
        # 嘴形目標選擇
        ttk.Label(main_frame, text="嘴形目標視頻:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.face_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.face_path_var, width=50).grid(row=5, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_face).grid(row=5, column=2, padx=5)
        
        # 輸出文件選擇
        ttk.Label(main_frame, text="輸出文件:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_path_var, width=50).grid(row=6, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_output).grid(row=6, column=2, padx=5)
        
        # 進度條
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=3, pady=20)
        
        # 開始按鈕
        ttk.Button(main_frame, text="開始處理", command=self.process).grid(row=8, column=0, columnspan=3, pady=10)
        
        # 狀態標籤
        self.status_var = tk.StringVar()
        self.status_var.set("準備就緒")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=9, column=0, columnspan=3, pady=5)

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
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            return len(faces) > 0
        except:
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
            filetypes=[("Audio/Video files", "*.mp4 *.wav *.mp3 *.m4a")]
        )
        if filename:
            self.input_path_var.set(filename)
            # 自動設置輸出路徑
            base_name = os.path.splitext(filename)[0]
            self.output_path_var.set(f"{base_name}_translated.mp4")

    def browse_face(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4")]
        )
        if filename:
            self.face_path_var.set(filename)

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

    def process(self):
        # 獲取輸入值
        api_key = self.api_key_var.get()
        input_path = self.input_path_var.get()
        language = self.language_var.get()
        face_path = self.face_path_var.get()
        output_path = self.output_path_var.get()
        enable_slide_translation = self.slide_translation_var.get()
        
        # 驗證輸入
        if not all([api_key, input_path, output_path]):
            messagebox.showerror("錯誤", "請填寫所有必要欄位")
            return
            
        # 檢查是否需要嘴形同步
        if not face_path:
            if not messagebox.askyesno("確認", "沒有選擇嘴形目標視頻，將只進行語音克隆和翻譯。是否繼續？"):
                return
        
        try:
            # 創建必要的目錄
            os.makedirs("temp", exist_ok=True)
            
            # 更新狀態
            self.status_var.set("正在處理中...")
            self.progress['value'] = 0
            self.root.update()
            
            # 步驟1：語音轉文字並翻譯
            self.status_var.set("正在進行語音識別和翻譯...")
            translated_text = voice(input_path, api_key, language)
            print(f"翻譯結果: {translated_text}")
            self.progress['value'] = 20
            self.root.update()
            
            # 步驟2：語音克隆
            self.status_var.set("正在進行語音克隆...")
            temp_audio = "temp/cloned_audio.wav"
            audio_path = xttsv(translated_text, input_path, temp_audio, language)
            self.progress['value'] = 40
            self.root.update()
            
            # 步驟3：嘴形同步（先進行）
            video_for_slide_translation = input_path
            if face_path:
                self.status_var.set("正在進行嘴形同步...")
                temp_lipsync_video = "temp/lipsync_video.mp4"
                run_inference(face_path, audio_path, temp_lipsync_video)
                video_for_slide_translation = temp_lipsync_video
                self.progress['value'] = 70
                self.root.update()
            
            # 步驟4：投影片翻譯（在嘴形同步之後）
            if enable_slide_translation:
                self.status_var.set("正在智能識別和翻譯投影片...")
                slide_language = self.slide_language_var.get()
                translated_slides_dir, slide_frame_mapping = self.extract_and_translate_slides(video_for_slide_translation, slide_language)
                print(f"翻譯了 {len(slide_frame_mapping)} 張投影片")
                
                # 創建最終影片（包含音頻）
                self.create_translated_video(video_for_slide_translation, translated_slides_dir, slide_frame_mapping, output_path, audio_path)
                self.progress['value'] = 100
                self.root.update()
            else:
                # 如果沒有投影片翻譯，確保音頻正確合成
                if face_path:
                    # 已經有嘴形同步的影片，直接複製
                    import shutil
                    shutil.copy(video_for_slide_translation, output_path)
                else:
                    # 只有語音，保存音檔
                    audio_output = output_path.replace('.mp4', '.wav')
                    import shutil
                    shutil.copy(audio_path, audio_output)
                    messagebox.showinfo("完成", f"語音克隆完成！音檔已保存到：{audio_output}")
                    self.status_var.set("處理完成！")
                    return
                self.progress['value'] = 100
            
            self.status_var.set("處理完成！")
            messagebox.showinfo("完成", "處理已完成！")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"處理過程中發生錯誤：{str(e)}")
            self.status_var.set("處理失敗")
            self.progress['value'] = 0

def main():
    root = tk.Tk()
    app = DeepVideoTranslationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()