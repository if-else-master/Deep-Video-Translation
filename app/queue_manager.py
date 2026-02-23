"""
任務隊列管理系統
"""
import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import os

class QueueManager:
    """管理影片處理任務隊列"""
    
    # 測試郵件白名單（不受冷卻限制）
    WHITELIST_EMAILS = ['rayc57429@gmail.com']
    
    def __init__(self, db_path='queue.db'):
        """初始化隊列管理器"""
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """初始化資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 任務表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    video_filename TEXT NOT NULL,
                    video_duration REAL,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    params TEXT,
                    output_path TEXT,
                    error_message TEXT
                )
            ''')
            
            # Email 使用記錄表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 1
                )
            ''')
            
            # 建立索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_usage ON email_usage(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_created ON tasks(created_at)')
            
            conn.commit()
    
    def check_email_cooldown(self, email):
        """
        檢查 email 是否在冷卻期內
        返回: (可用, 剩餘時間秒數)
        """
        # 白名單郵件不受限制
        if email.lower() in [e.lower() for e in self.WHITELIST_EMAILS]:
            return True, 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT last_used FROM email_usage
                WHERE email = ?
                ORDER BY last_used DESC
                LIMIT 1
            ''', (email.lower(),))
            
            result = cursor.fetchone()
            if not result:
                return True, 0
            
            last_used = datetime.fromisoformat(result[0])
            cooldown_end = last_used + timedelta(days=5)
            now = datetime.now()
            
            if now < cooldown_end:
                remaining = (cooldown_end - now).total_seconds()
                return False, remaining
            
            return True, 0
    
    def record_email_usage(self, email):
        """記錄 email 使用"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO email_usage (email, last_used)
                VALUES (?, CURRENT_TIMESTAMP)
            ''', (email.lower(),))
            conn.commit()
    
    def add_task(self, task_id, email, video_filename, video_duration, params):
        """
        添加新任務到隊列
        返回: (成功, 訊息)
        """
        with self.lock:
            # 檢查 email 冷卻
            available, remaining = self.check_email_cooldown(email)
            if not available:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                return False, f"此 Email 需等待 {hours} 小時 {minutes} 分鐘後才能再次使用"
            
            # 檢查影片時長（1分鐘 = 60秒）
            if video_duration and video_duration > 60:
                return False, f"影片時長 {video_duration:.1f} 秒超過限制（最多 60 秒）"
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO tasks (
                            task_id, email, video_filename, video_duration,
                            status, params
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        task_id,
                        email.lower(),
                        video_filename,
                        video_duration,
                        'queued',
                        json.dumps(params)
                    ))
                    conn.commit()
                
                # 記錄 email 使用
                self.record_email_usage(email)
                
                # 獲取隊列位置
                position = self.get_queue_position(task_id)
                
                return True, f"任務已加入隊列，您的位置是第 {position} 位"
            except sqlite3.IntegrityError:
                return False, "任務 ID 已存在"
            except Exception as e:
                return False, f"添加任務失敗: {str(e)}"
    
    def get_queue_position(self, task_id):
        """獲取任務在隊列中的位置"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM tasks
                WHERE status = 'queued'
                AND created_at <= (
                    SELECT created_at FROM tasks WHERE task_id = ?
                )
            ''', (task_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_next_task(self):
        """獲取下一個待處理的任務"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT task_id, email, video_filename, params
                    FROM tasks
                    WHERE status = 'queued'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                
                if result:
                    task_id = result[0]
                    # 標記為處理中
                    cursor.execute('''
                        UPDATE tasks
                        SET status = 'processing', started_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (task_id,))
                    conn.commit()
                    
                    return {
                        'task_id': result[0],
                        'email': result[1],
                        'video_filename': result[2],
                        'params': json.loads(result[3]) if result[3] else {}
                    }
                
                return None
    
    def update_task_status(self, task_id, status, output_path=None, error_message=None):
        """更新任務狀態"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute('''
                    UPDATE tasks
                    SET status = ?, output_path = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (status, output_path, task_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE tasks
                    SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (status, error_message, task_id))
            else:
                cursor.execute('''
                    UPDATE tasks
                    SET status = ?
                    WHERE task_id = ?
                ''', (status, task_id))
            
            conn.commit()
    
    def get_task_info(self, task_id):
        """獲取任務信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, email, video_filename, status, created_at,
                       started_at, completed_at, output_path, error_message,
                       video_duration
                FROM tasks
                WHERE task_id = ?
            ''', (task_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'task_id': result[0],
                    'email': result[1],
                    'video_filename': result[2],
                    'status': result[3],
                    'created_at': result[4],
                    'started_at': result[5],
                    'completed_at': result[6],
                    'output_path': result[7],
                    'error_message': result[8],
                    'video_duration': result[9],
                    'queue_position': self.get_queue_position(task_id) if result[3] == 'queued' else 0
                }
            
            return None
    
    def get_queue_stats(self):
        """獲取隊列統計信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "queued"')
            queued = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "processing"')
            processing = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
            completed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "failed"')
            failed = cursor.fetchone()[0]
            
            return {
                'queued': queued,
                'processing': processing,
                'completed': completed,
                'failed': failed,
                'total': queued + processing + completed + failed
            }
    
    def cleanup_old_tasks(self, days=30):
        """清理舊任務（超過指定天數）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute('''
                DELETE FROM tasks
                WHERE completed_at < ?
                AND status IN ('completed', 'failed')
            ''', (cutoff_date.isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            
            return deleted
