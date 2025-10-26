"""
Mesop 網頁版 GUI
- 保持與 tkinter 版相同的欄位與流程順序
- 唯一不同：影片上傳框放大且置中，支援拖拽上傳
- 不修改 main.py 的運作邏輯；此檔僅負責 GUI。

啟動方式（任選其一）：
- 在專案根目錄執行: ./start_mesop.sh
- 或在 app 目錄執行: python -m mesop mesopgui.py --port 32123 --host 0.0.0.0
- 或直接執行: python mesopgui.py
"""

from __future__ import annotations

import os
import threading
import datetime
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import time

import mesop as me

# 依需求「import from main.py 中」，僅導入以符合要求（不改 main 的邏輯）
try:
    import main as tk_main  # noqa: F401
except Exception:
    # 若直接執行時的工作目錄不同，嘗試相對導入
    try:
        from . import main as tk_main  # type: ignore # noqa: F401
    except Exception:
        tk_main = None  # 僅為滿足導入要求，實際不使用

# 使用已抽離的核心處理邏輯
try:
    from video_processor import VideoProcessor
except ImportError:
    # 如果找不到 video_processor，創建一個簡單的替代品
    class VideoProcessor:
        def __init__(self, progress_callback=None):
            self.progress_callback = progress_callback
        
        def process_complete_video(self, **kwargs):
            if self.progress_callback:
                self.progress_callback("處理中...", 50)
            # 這裡應該是實際的處理邏輯
            raise NotImplementedError("VideoProcessor 模塊未找到")


# ---- 全局共享數據（線程安全） ----
class ProcessingState:
    """線程安全的處理狀態類"""
    def __init__(self):
        self.lock = threading.Lock()
        self.logs = deque(maxlen=100)  # 最多保留100條日誌
        self.progress = 0
        self.status = "準備就緒"
        self.is_running = False
        self.error = None
        self.session_id = None  # 用於區分不同的處理會話
    
    def add_log(self, message: str):
        with self.lock:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            self.logs.append(log_entry)
    
    def update_progress(self, progress: int, status: str = None):
        with self.lock:
            self.progress = max(0, min(100, progress))
            if status:
                self.status = status
    
    def get_state(self):
        with self.lock:
            return {
                'logs': list(self.logs),
                'progress': self.progress,
                'status': self.status,
                'is_running': self.is_running,
                'error': self.error,
                'session_id': self.session_id
            }
    
    def start_session(self, session_id: str):
        with self.lock:
            self.logs.clear()
            self.progress = 0
            self.status = "正在準備..."
            self.is_running = True
            self.error = None
            self.session_id = session_id
    
    def end_session(self, success: bool, message: str = None):
        with self.lock:
            self.is_running = False
            if not success:
                self.error = message
                self.progress = 0
            else:
                self.progress = 100
            if message:
                self.status = message

# 全局處理狀態實例
processing_state = ProcessingState()


# ---- UI 狀態 ----
@me.stateclass
class AppState:
    api_key: str = ""
    input_path: str = ""
    language: str = "日文"  # 與 tkinter 預設一致
    slide_enabled: bool = True
    slide_language: str = "Japanese"
    min_segment_duration: str = "2"
    hash_threshold: str = "5"
    output_path: str = ""

    uploaded_file_name: Optional[str] = None
    # 完成提示狀態
    show_done: bool = False
    done_message: str = "處理完成！"
    # 會話ID（用於追蹤當前處理）
    session_id: str = ""
    # 最後更新時間（用於觸發UI刷新）
    last_update: float = 0.0


# ---- 風格樣式 ----
def page_container_style() -> me.Style:
    return me.Style(
        max_width="1200px",
        margin=me.Margin(top="0", right="auto", bottom="0", left="auto"),
        padding=me.Padding(top="24px", right="24px", bottom="24px", left="24px"),
        text_align="center",
    )


def form_label_style() -> me.Style:
    return me.Style(
        font_weight="1000",
        margin=me.Margin(top="0", right="0", bottom="6px", left="0"),
    )


def input_style(width: str = "100%") -> me.Style:
    return me.Style(width=width)


def upload_box_style() -> me.Style:
    # 大、置中、可拖拽，圓角與虛線邊框
    side = me.BorderSide(width="2px", color="#9aa0a6", style="dashed")
    return me.Style(
        width="600px",
        height="200px",
        border=me.Border(top=side, right=side, bottom=side, left=side),
        border_radius="20px",
        display="flex",
        align_items="center",
        justify_content="center",
        margin=me.Margin(top="12px", right="auto", bottom="12px", left="auto"),
        background="rgba(0,0,0,0.02)",
        color="#5f6368",
        text_align="center",
        cursor="pointer",
    )


def row_gap_style() -> me.Style:
    return me.Style(margin=me.Margin(top="12px", right="0", bottom="0", left="0"))


def slide_frame_style() -> me.Style:
    side = me.BorderSide(width="1px", color="#e0e0e0", style="solid")
    return me.Style(
        padding=me.Padding(top="12px", right="12px", bottom="12px", left="12px"),
        border=me.Border(top=side, right=side, bottom=side, left=side),
        border_radius="8px",
        margin=me.Margin(top="8px", right="0", bottom="0", left="0"),
    )


def terminal_style() -> me.Style:
    """終端風格的日誌顯示區域"""
    side = me.BorderSide(width="2px", color="#2d2d2d", style="solid")
    return me.Style(
        background="#1e1e1e",
        color="#d4d4d4",
        font_family="'Menlo', 'Monaco', 'Courier New', monospace",
        font_size="12px",
        padding=me.Padding(top="16px", right="16px", bottom="16px", left="16px"),
        border=me.Border(top=side, right=side, bottom=side, left=side),
        border_radius="8px",
        height="350px",
        max_height="350px",
        overflow_y="auto",
        overflow_x="hidden",
        margin=me.Margin(top="0", right="0", bottom="0", left="0"),
        white_space="pre-wrap",
        # word_break="normal",
        box_shadow="0 4px 12px rgba(0,0,0,0.15)",
    )


# ---- 事件處理 ----
def _ensure_dirs():
    os.makedirs("temp/uploads", exist_ok=True)


def on_upload(e: me.UploadEvent):
    state = me.state(AppState)
    if not e.files:
        return

    try:
        _ensure_dirs()
        f = e.files[0]
        filename = f.name or "uploaded.mp4"
        # 僅允許 mp4（與 tkinter 規則一致）
        if not filename.lower().endswith(".mp4"):
            state.status = "請上傳 MP4 格式的影片"
            return

        save_path = os.path.abspath(os.path.join("temp", "uploads", filename))
        # 修正文件讀取方式
        file_content = f.read() if hasattr(f, 'read') else f.getvalue() if hasattr(f, 'getvalue') else f.bytes
        with open(save_path, "wb") as out:
            out.write(file_content)

        state.input_path = save_path
        state.uploaded_file_name = filename

        # 自動設定輸出路徑
        base, _ = os.path.splitext(save_path)
        state.output_path = base + "_translated.mp4"
        state.status = f"已上傳：{filename}"
    except Exception as ex:
        state.status = f"上傳失敗：{str(ex)}"


def on_api_key_change(e: me.InputEvent):
    state = me.state(AppState)
    state.api_key = e.value


def on_language_change(e: me.SelectSelectionChangeEvent):
    state = me.state(AppState)
    state.language = e.value


def on_slide_enabled_change(e: me.CheckboxChangeEvent):
    state = me.state(AppState)
    state.slide_enabled = e.checked


def on_slide_language_change(e: me.SelectSelectionChangeEvent):
    state = me.state(AppState)
    state.slide_language = e.value


def on_min_segment_change(e: me.InputEvent):
    state = me.state(AppState)
    state.min_segment_duration = e.value


def on_hash_threshold_change(e: me.InputEvent):
    state = me.state(AppState)
    state.hash_threshold = e.value


def on_output_path_change(e: me.InputEvent):
    state = me.state(AppState)
    state.output_path = e.value


def _on_progress(message: str, progress: Optional[int] = None):
    """背景任務進度回調 → 更新全局狀態（線程安全）"""
    # 添加日誌
    processing_state.add_log(message)
    
    # 更新進度
    if progress is not None:
        processing_state.update_progress(progress, message)
    else:
        # 只更新狀態消息
        with processing_state.lock:
            processing_state.status = message


def refresh_logs(e: me.ClickEvent):
    """刷新日誌顯示（觸發頁面重新渲染）"""
    state = me.state(AppState)
    # 更新時間戳以觸發重新渲染
    state.last_update = time.time()


def start_processing(e: me.ClickEvent):
    state = me.state(AppState)
    
    # 檢查是否已經在運行
    if processing_state.is_running:
        return

    # 驗證
    if not state.api_key or not state.input_path:
        processing_state.add_log("❌ 請填寫 API Key 並上傳影片")
        return
    if not state.input_path.lower().endswith(".mp4"):
        processing_state.add_log("❌ 請選擇 MP4 格式的影片")
        return

    # 解析參數
    try:
        min_seg = float(state.min_segment_duration or "2")
    except Exception:
        min_seg = 2.0
    try:
        hash_th = int(state.hash_threshold or "5")
    except Exception:
        hash_th = 5

    # 創建新的會話ID
    session_id = f"session_{int(time.time())}"
    state.session_id = session_id
    state.show_done = False
    
    # 設置初始狀態
    processing_state.start_session(session_id)

    # 背景執行，避免阻塞 UI
    def run_task():
        # 包裝 print 函數來捕獲輸出
        import builtins
        import subprocess
        original_print = builtins.print
        
        def custom_print(*args, **kwargs):
            message = ' '.join(str(arg) for arg in args)
            _on_progress(message)
            original_print(*args, **kwargs)
        
        builtins.print = custom_print
        
        try:
            _on_progress("🚀 初始化處理系統...", 0)
            
            # 導入必要的模組和函數
            from txtvoice import voice
            from xttsv import xttsv
            import cv2
            import easyocr
            import numpy as np
            import imagehash
            from PIL import Image, ImageDraw, ImageFont
            import shutil
            
            # 獲取參數
            api_key = state.api_key
            input_path = state.input_path
            language = state.language
            output_path = state.output_path or (os.path.splitext(input_path)[0] + "_translated.mp4")
            enable_slide_translation = state.slide_enabled
            slide_language = state.slide_language
            
            
            # 創建輔助類（不使用 tkinter）
            class ProcessorHelper:
                def __init__(self):
                    self.font_paths = self.setup_fonts()
                
                def setup_fonts(self):
                    """設置字體路徑"""
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    return {
                        "Japanese": os.path.join(current_dir, "NotoSansCJKjp-Regular.otf"),
                        "English": self.get_system_font() or "/System/Library/Fonts/Arial.ttf",
                        "Chinese": os.path.join(current_dir, "NotoSansTC-Regular.ttf")
                    }
                
                def get_system_font(self):
                    """獲取系統可用字體"""
                    possible_fonts = [
                        "/System/Library/Fonts/PingFang.ttc",
                        "/System/Library/Fonts/Arial.ttf",
                        "/System/Library/Fonts/Hiragino Sans GB.ttc",
                        "C:/Windows/Fonts/msyh.ttc",
                        "C:/Windows/Fonts/arial.ttf",
                        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                    ]
                    for font_path in possible_fonts:
                        if os.path.exists(font_path):
                            print(f"✅ {font_path} 字體已找到")
                            return font_path
                    print("❌ 字體未找到")
                    return None
                
                def ensure_directory_exists(self, directory_path):
                    """確保指定目錄存在"""
                    if not os.path.exists(directory_path):
                        os.makedirs(directory_path, exist_ok=True)
                    return directory_path
                
                def ensure_basic_directories(self):
                    """確保所有必要的基本目錄都存在"""
                    required_dirs = [
                        "temp", "temp/faceai", "temp/pptai",
                        "temp/audio_segments", "temp/slides_output",
                        "temp/translated_slides", "temp/segments"
                    ]
                    for dir_path in required_dirs:
                        os.makedirs(dir_path, exist_ok=True)
                    print(f"✅ 確保目錄存在: {dir_path}")
            
            helper = ProcessorHelper()
            helper.ensure_basic_directories()
            
            _on_progress("📹 開始處理影片...", 5)
            
            # 導入 main.py 中的處理類但只使用其方法
            # 我們需要創建一個不依賴 tkinter 的版本
            import importlib.util
            spec = importlib.util.spec_from_file_location("main_module", os.path.join(os.path.dirname(__file__), "main.py"))
            main_module = importlib.util.module_from_spec(spec)
            
            # 暫時替換 tkinter 以避免導入問題
            import sys
            original_modules = {}
            for mod in ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox']:
                if mod in sys.modules:
                    original_modules[mod] = sys.modules[mod]
            
            # 創建一個假的 tkinter 模組
            class FakeTk:
                class Tk:
                    def __init__(self): pass
                    def withdraw(self): pass
                    def update(self): pass
                    def destroy(self): pass
                    def mainloop(self): pass
                    def title(self, t): pass
                    def geometry(self, g): pass
                
                class StringVar:
                    def __init__(self, *args, **kwargs):
                        self.value = kwargs.get('value', '')
                    def get(self): return self.value
                    def set(self, v): self.value = v
                
                class BooleanVar:
                    def __init__(self, *args, **kwargs):
                        self.value = kwargs.get('value', False)
                    def get(self): return self.value
                    def set(self, v): self.value = v
                
                class Checkbutton:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                
                W = E = N = S = 0
            
            class FakeTtk:
                class Frame:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                    def grid_remove(self, *args, **kwargs): pass
                
                class Label:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                
                class Entry:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                
                class Button:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                
                class Combobox:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                
                class Progressbar:
                    def __init__(self, *args, **kwargs): 
                        self.data = {'value': 0}
                    def __setitem__(self, k, v):
                        self.data[k] = v
                        if k == 'value':
                            _on_progress("", int(v))
                    def __getitem__(self, k): return self.data.get(k, 0)
                    def grid(self, *args, **kwargs): pass
                
                class LabelFrame:
                    def __init__(self, *args, **kwargs): pass
                    def grid(self, *args, **kwargs): pass
                    def grid_remove(self, *args, **kwargs): pass
            
            # 創建假的 messagebox 和 filedialog
            class FakeMessagebox:
                @staticmethod
                def showerror(title, message):
                    _on_progress(f"❌ {title}: {message}")
                @staticmethod
                def showinfo(title, message):
                    _on_progress(f"ℹ️ {title}: {message}")
                @staticmethod
                def showwarning(title, message):
                    _on_progress(f"⚠️ {title}: {message}")
            
            class FakeFiledialog:
                @staticmethod
                def askopenfilename(**kwargs):
                    return ""
                @staticmethod
                def asksaveasfilename(**kwargs):
                    return ""
            
            sys.modules['tkinter'] = FakeTk
            sys.modules['tkinter.ttk'] = FakeTtk
            sys.modules['tkinter.messagebox'] = FakeMessagebox
            sys.modules['tkinter.filedialog'] = FakeFiledialog
            
            try:
                spec.loader.exec_module(main_module)
                
                # 創建處理器實例（使用假的 root）
                fake_root = FakeTk.Tk()
                app = main_module.DeepVideoTranslationApp(fake_root)
                
                # 設定參數
                app.api_key_var.set(api_key)
                app.input_path_var.set(input_path)
                app.language_var.set(language)
                app.output_path_var.set(output_path)
                app.slide_translation_var.set(enable_slide_translation)
                app.slide_language_var.set(slide_language)
                app.min_segment_duration_var.set(str(min_seg))
                app.hash_threshold_var.set(str(hash_th))
                
                # 執行處理流程
                _on_progress("🔍 正在進行智能分段分析...", 10)
                segments_info = app.analyze_and_segment_video(input_path)
                
                if not segments_info:
                    raise Exception("無法分析影片內容，請確認影片格式正確")
                
                _on_progress("👤 正在處理人臉段落...", 40)
                face_segments = app.process_face_segments("temp/faceai", language)
                
                processed_slide_segments = []
                if enable_slide_translation:
                    _on_progress("📊 正在處理簡報段落...", 70)
                    processed_slide_segments = app.process_slide_segments("temp/pptai", language, slide_language)
                else:
                    _on_progress("📋 簡報翻譯已停用，僅處理音頻...", 70)
                    ppt_dir = "temp/pptai"
                    helper.ensure_directory_exists(ppt_dir)
                    ppt_files = sorted([f for f in os.listdir(ppt_dir) if f.endswith('.mp4')])
                    
                    for j, filename in enumerate(ppt_files):
                        input_path_seg = os.path.join(ppt_dir, filename)
                        base_name = os.path.splitext(filename)[0]
                        processed_path = os.path.join(ppt_dir, f"{base_name}_processed.mp4")
                        
                        try:
                            _on_progress(f"📋 處理簡報音頻 {filename}...", 70 + int((j / len(ppt_files)) * 20))
                            
                            try:
                                translated_text = voice(input_path_seg, api_key, language)
                            except Exception as audio_error:
                                _on_progress(f"⚠️ 音頻轉文字失敗: {audio_error}")
                                translated_text = ""
                            
                            if translated_text and translated_text.strip():
                                temp_audio = os.path.join(ppt_dir, f"{base_name}_audio.wav")
                                helper.ensure_directory_exists(os.path.dirname(temp_audio))
                                
                                try:
                                    xttsv(translated_text, input_path_seg, temp_audio, language)
                                    command = f'ffmpeg -y -i "{input_path_seg}" -i "{temp_audio}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{processed_path}"'
                                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                                    if result.returncode != 0:
                                        shutil.copy(input_path_seg, processed_path)
                                except Exception as tts_error:
                                    _on_progress(f"⚠️ 語音克隆失敗: {tts_error}")
                                    shutil.copy(input_path_seg, processed_path)
                            else:
                                shutil.copy(input_path_seg, processed_path)
                            
                            processed_slide_segments.append(processed_path)
                        except Exception as e:
                            _on_progress(f"❌ 處理簡報音頻失敗: {e}")
                            shutil.copy(input_path_seg, processed_path)
                            processed_slide_segments.append(processed_path)
                
                _on_progress("🎬 正在進行自動剪接...", 90)
                app.auto_edit_segments(face_segments, processed_slide_segments, segments_info, output_path)
                
                _on_progress("✅ 處理完成！", 100)
                processing_state.end_session(True, f"處理完成：{output_path}")
                
            finally:
                # 恢復原始模組
                for mod, orig in original_modules.items():
                    sys.modules[mod] = orig
            
        except Exception as ex:
            _on_progress(f"❌ 處理失敗：{ex}", 0)
            import traceback
            error_details = traceback.format_exc()
            _on_progress(f"錯誤詳情：\n{error_details}")
            processing_state.end_session(False, f"處理失敗：{ex}")
        finally:
            # 恢復原始 print 函數
            builtins.print = original_print

    # 在實際應用中，可能需要使用任務隊列如 Celery
    # 這裡為了簡化，仍使用線程
    threading.Thread(target=run_task, daemon=True).start()


# ---- 頁面 ----
@me.page(path="/", title="Deep Video Translation (Mesop)")
def page():
    state = me.state(AppState)
    
    # 從全局狀態獲取處理信息
    proc_state = processing_state.get_state()
    current_logs = proc_state['logs']
    current_progress = proc_state['progress']
    current_status = proc_state['status']
    is_running = proc_state['is_running']
    
    # 如果處理完成且會話ID匹配，顯示完成消息
    if not is_running and state.session_id == proc_state['session_id'] and proc_state['session_id']:
        if proc_state['error']:
            state.show_done = False  # 錯誤時不顯示完成提示
        elif current_progress == 100 and not state.show_done:
            state.show_done = True
            state.done_message = f"已完成處理，輸出：{state.output_path}"
    
    # 主題與密度（輕量美化）
    try:
        me.set_theme_mode("light")
        me.set_theme_density("comfortable")
    except Exception:
        pass
    with me.box(style=page_container_style()):
        me.text("Deep Video Translation", type="headline-5")      

        # API Key
        with me.box(style=row_gap_style()):
            me.text("Gemini API Key:", style=form_label_style())
            me.input(
                value=state.api_key, 
                on_input=on_api_key_change, 
                style=input_style(),
                type="password"
            )

        # 影片上傳（大、置中、可拖拽）
        with me.box(style=row_gap_style()):
            me.text("輸入影片:", style=form_label_style())
            with me.box(style=upload_box_style()):
                me.uploader(
                    label="拖拽或點擊上傳 MP4", 
                    on_upload=on_upload, 
                    multiple=False,
                    accepted_file_types=[".mp4","video/mp4"]
                )
            if state.input_path:
                me.text(f"已選擇：{state.uploaded_file_name}", type="body-2")

        # 語音/投影片/段落/門檻 一排設計
        with me.box(style=me.Style(
            display="flex",
            flex_direction="row",
            gap="24px",
            align_items="center",
            justify_content="center",
            margin=me.Margin(top="16px", right="0", bottom="0", left="0"),
            padding=me.Padding(top="16px", right="16px", bottom="16px", left="16px"),
            background="#f7f7fa",
            border_radius="12px",
            box_shadow="0 2px 8px rgba(0,0,0,0.04)"
        )):
            # 語音翻譯語言
            with me.box(style=me.Style(min_width="160px")):
                me.text("語音翻譯語言", style=form_label_style())
                options = [
                    me.SelectOption(label="日文", value="日文"),
                    me.SelectOption(label="英文", value="英文"),
                    me.SelectOption(label="中文", value="中文"),
                ]
                me.select(
                    value=state.language,
                    options=options,
                    on_selection_change=on_language_change,
                )
            # 投影片翻譯語言
            if state.slide_enabled:
                with me.box(style=me.Style(min_width="160px")):
                    me.text("投影片翻譯語言", style=form_label_style())
                    slide_options = [
                        me.SelectOption(label="Japanese", value="Japanese"),
                        me.SelectOption(label="English", value="English"),
                        me.SelectOption(label="Chinese", value="Chinese"),
                    ]
                    me.select(
                        value=state.slide_language,
                        options=slide_options,
                        on_selection_change=on_slide_language_change,
                    )
            # 最小段落長度(秒)
            with me.box(style=me.Style(min_width="140px")):
                me.text("最小段落長度(秒)", style=form_label_style())
                me.input(
                    value=state.min_segment_duration,
                    on_input=on_min_segment_change,
                    type="number",
                    style=me.Style(width="100px")
                )
            # 場景切換門檻
            with me.box(style=me.Style(min_width="140px")):
                me.text("場景切換門檻", style=form_label_style())
                me.input(
                    value=state.hash_threshold,
                    on_input=on_hash_threshold_change,
                    type="number",
                    style=me.Style(width="100px")
                )
        # 投影片翻譯開關
        with me.box(style=row_gap_style()):
            me.checkbox(
                label="啟用投影片文字翻譯",
                checked=state.slide_enabled,
                on_change=on_slide_enabled_change,
            )

        # 輸出文件
        with me.box(style=row_gap_style()):
            me.text("輸出文件:", style=form_label_style())
            me.input(
                value=state.output_path, 
                on_input=on_output_path_change, 
                style=input_style()
            )

        # 進度條
        with me.box(style=row_gap_style()):
            me.progress_bar(mode="determinate", value=float(current_progress))
            me.text(f"{current_progress}%", type="body-2")

        # 開始按鈕
        with me.box(style=row_gap_style()):
            me.button("開始", on_click=start_processing, disabled=is_running, type="raised")

        # 狀態
        with me.box(style=row_gap_style()):
            me.text(current_status, style=me.Style(color="#666666"))
        
        # 終端風格的日誌顯示區域
        if current_logs or is_running:
            with me.box(style=me.Style(
                margin=me.Margin(top="24px", right="0", bottom="0", left="0"),
                text_align="left"
            )):
                # 標題和刷新按鈕
                with me.box(style=me.Style(
                    display="flex",
                    flex_direction="row",
                    justify_content="space-between",
                    align_items="center",
                    margin=me.Margin(top="0", right="0", bottom="12px", left="0")
                )):
                    me.text("🖥️ 處理日誌 (即時更新)", style=me.Style(
                        font_weight="bold",
                        font_size="16px",
                        text_align="left"
                    ))
                    if is_running:
                        me.button(
                            "🔄 刷新", 
                            on_click=refresh_logs,
                            type="flat",
                            style=me.Style(
                                font_size="12px",
                                color="#666666"
                            )
                        )
                
                with me.box(style=terminal_style()):
                    if current_logs:
                        log_text = '\n'.join(current_logs)
                        me.text(log_text, style=me.Style(
                            white_space="pre-wrap",
                            font_family="'Menlo', 'Monaco', 'Courier New', monospace",
                            font_size="12px",
                            line_height="1.6",
                            color="#d4d4d4"
                        ))
                    else:
                        me.text("等待處理開始...", style=me.Style(
                            color="#888888",
                            font_style="italic",
                            font_family="'Menlo', 'Monaco', 'Courier New', monospace"
                        ))
                
                # 如果正在處理中，顯示提示
                if is_running:
                    me.text("💡 提示：點擊「刷新」按鈕或重新載入頁面以查看最新日誌", style=me.Style(
                        font_size="12px",
                        color="#888888",
                        margin=me.Margin(top="8px", right="0", bottom="0", left="0"),
                        font_style="italic"
                    ))

        # 完成提示（Toast）
        if state.show_done:
            with me.box(style=me.Style(
                position="fixed",
                top="20px",
                right="20px",
                z_index="1000",
                background="#111827",
                color="#ffffff",
                border_radius="10px",
                box_shadow="0 10px 20px rgba(0,0,0,0.25)",
                padding=me.Padding(top="12px", right="16px", bottom="12px", left="16px"),
            )):
                me.text("✅ 處理完成", type="subtitle-2")
                me.text(state.done_message, type="body-2")
                me.button("關閉", on_click=_close_done, type="stroked")


def _close_done(e: me.ClickEvent):
    state = me.state(AppState)
    state.show_done = False


# 允許直接以 `python mesopgui.py` 啟動（不依賴 `python -m mesop` 或 shell 腳本）
if __name__ == "__main__":
    import argparse
    
    try:
        from werkzeug.serving import run_simple
    except ImportError:
        print("❌ 缺少 werkzeug 依賴，請安裝：pip install werkzeug")
        exit(1)
    
    parser = argparse.ArgumentParser(description="Run Mesop GUI server")
    parser.add_argument("--port", type=int, default=32123, help="伺服器埠號")
    parser.add_argument("--host", default="127.0.0.1", help="伺服器主機")
    parser.add_argument("--debug", action="store_true", help="啟用 Debug 模式")
    args = parser.parse_args()

    print(f"🚀 Mesop 伺服器啟動中：http://{args.host}:{args.port}")
    print("⏹️  按 Ctrl+C 可停止伺服器")
    
    # 使用 Mesop 正確的 WSGI 啟動方式
    try:
        # 修正：create_wsgi_app 不接受 debug 參數
        wsgi_app = me.create_wsgi_app()
        run_simple(
            args.host, 
            args.port, 
            wsgi_app, 
            use_reloader=args.debug,
            use_debugger=args.debug,
            threaded=True  # 支援多線程處理
        )
    except Exception as e:
        print(f"❌ 啟動失敗：{e}")
        print("💡 請嘗試使用命令：python -m mesop mesopgui.py --port 32123")
        print("💡 或確保 Mesop 和 werkzeug 已正確安裝")