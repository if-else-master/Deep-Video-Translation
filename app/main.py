import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys

# 添加 Wav2Lip 目錄到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'Wav2Lip'))

from txtvoice import voice
from xttsv import xttsv
from Wav2Lip.inference import run_inference

class DeepVideoTranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deep Video Translation")
        self.root.geometry("900x700")
        
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
        
        # 語言選擇
        ttk.Label(main_frame, text="翻譯語言:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.language_var = tk.StringVar(value="日文")
        language_combo = ttk.Combobox(main_frame, textvariable=self.language_var, values=["日文", "英文", "中文"], width=47)
        language_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 嘴形目標選擇
        ttk.Label(main_frame, text="嘴形目標視頻:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.face_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.face_path_var, width=50).grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_face).grid(row=3, column=2, padx=5)
        
        # 輸出文件選擇
        ttk.Label(main_frame, text="輸出文件:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.output_path_var, width=50).grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Button(main_frame, text="瀏覽", command=self.browse_output).grid(row=4, column=2, padx=5)
        
        # 進度條
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, pady=20)
        
        # 開始按鈕
        ttk.Button(main_frame, text="開始處理", command=self.process).grid(row=6, column=0, columnspan=3, pady=10)
        
        # 狀態標籤
        self.status_var = tk.StringVar()
        self.status_var.set("準備就緒")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=7, column=0, columnspan=3, pady=5)

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

    def process(self):
        # 獲取輸入值
        api_key = self.api_key_var.get()
        input_path = self.input_path_var.get()
        language = self.language_var.get()
        face_path = self.face_path_var.get()
        output_path = self.output_path_var.get()
        
        # 驗證輸入
        if not all([api_key, input_path, output_path]):
            messagebox.showerror("錯誤", "請填寫所有必要欄位")
            return
            
        # 檢查是否需要嘴形同步
        if not face_path:
            if not messagebox.askyesno("確認", "沒有選擇嘴形目標視頻，將只進行語音克隆和翻譯。是否繼續？"):
                return
        
        try:
            # 更新狀態
            self.status_var.set("正在處理中...")
            self.progress['value'] = 0
            self.root.update()
            
            # 步驟1：語音轉文字並翻譯
            self.status_var.set("正在進行語音識別和翻譯...")
            translated_text = voice(input_path, api_key, language)
            print(f"翻譯結果: {translated_text}")
            self.progress['value'] = 25
            self.root.update()
            
            # 步驟2：語音克隆
            self.status_var.set("正在進行語音克隆...")
            temp_audio = "temp/cloned_audio.wav"
            os.makedirs("temp", exist_ok=True)
            audio_path = xttsv(translated_text, input_path, temp_audio, language)
            self.progress['value'] = 60
            self.root.update()
            
            # 步驟3：嘴形同步（如果有嘴形目標）
            if face_path:
                self.status_var.set("正在進行嘴形同步...")
                run_inference(face_path, audio_path, output_path)
                self.progress['value'] = 100
            else:
                # 如果沒有嘴形目標，直接複製音檔到輸出位置
                import shutil
                audio_output = output_path.replace('.mp4', '.wav')
                shutil.copy(audio_path, audio_output)
                self.progress['value'] = 100
                messagebox.showinfo("完成", f"語音克隆完成！音檔已保存到：{audio_output}")
                self.status_var.set("處理完成！")
                return
            
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