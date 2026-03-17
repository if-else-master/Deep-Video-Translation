"""
後台任務處理器
"""
import threading
import time
import os
from queue_manager import QueueManager
from email_service import EmailService

class TaskProcessor:
    """後台任務處理器"""
    
    def __init__(self, process_function, check_interval=5):
        """
        初始化處理器
        
        Args:
            process_function: 處理任務的函數，接收任務參數並返回 (成功, 輸出路徑, 錯誤訊息)
            check_interval: 檢查隊列的間隔時間（秒）
        """
        self.queue_manager = QueueManager()
        self.email_service = EmailService()
        self.process_function = process_function
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
    def start(self):
        """啟動後台處理器"""
        if self.running:
            print("⚠️  處理器已經在運行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("✅ 後台任務處理器已啟動")
    
    def stop(self):
        """停止後台處理器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("🛑 後台任務處理器已停止")
    
    def _process_loop(self):
        """處理循環"""
        print("🔄 開始監聽任務隊列...")
        
        while self.running:
            try:
                # 獲取下一個任務
                task = self.queue_manager.get_next_task()
                
                if task:
                    print(f"\n📝 開始處理任務: {task['task_id']}")
                    print(f"   Email: {task['email']}")
                    print(f"   影片: {task['video_filename']}")
                    
                    # 處理任務
                    try:
                        success, output_path, error_message = self.process_function(task)
                        
                        if success:
                            # 標記任務完成
                            self.queue_manager.update_task_status(
                                task['task_id'],
                                'completed',
                                output_path=output_path
                            )
                            
                            # 發送成功郵件
                            print(f"📧 發送完成通知給: {task['email']}")
                            self.email_service.send_completion_email(
                                task['email'],
                                task['video_filename'],
                                output_path=output_path
                            )
                            
                            print(f"✅ 任務完成: {task['task_id']}")
                        else:
                            # 標記任務失敗
                            self.queue_manager.update_task_status(
                                task['task_id'],
                                'failed',
                                error_message=error_message
                            )
                            
                            # 發送失敗郵件
                            print(f"📧 發送錯誤通知給: {task['email']}")
                            self.email_service.send_error_email(
                                task['email'],
                                task['video_filename'],
                                error_message
                            )
                            
                            print(f"❌ 任務失敗: {task['task_id']} - {error_message}")
                    
                    except Exception as e:
                        error_msg = f"處理異常: {str(e)}"
                        print(f"❌ {error_msg}")
                        
                        # 標記任務失敗
                        self.queue_manager.update_task_status(
                            task['task_id'],
                            'failed',
                            error_message=error_msg
                        )
                        
                        # 發送失敗郵件
                        try:
                            self.email_service.send_error_email(
                                task['email'],
                                task['video_filename'],
                                error_msg
                            )
                        except:
                            pass
                
                else:
                    # 沒有任務，等待
                    time.sleep(self.check_interval)
                    
            except Exception as e:
                print(f"❌ 處理循環錯誤: {str(e)}")
                time.sleep(self.check_interval)
        
        print("🛑 處理循環已結束")
