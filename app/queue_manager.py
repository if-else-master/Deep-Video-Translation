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

            # 白名單表（動態，可由管理者新增/移除）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    note TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 黑名單表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 系統設定表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # 建立索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_usage ON email_usage(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_created ON tasks(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_email ON whitelist(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_email ON blacklist(email)')
            
            conn.commit()
    
    def check_email_cooldown(self, email):
        """
        檢查 email 是否在冷卻期內
        返回: (可用, 剩餘時間秒數)
        """
        email_lower = email.lower()

        # 靜態白名單
        if email_lower in [e.lower() for e in self.WHITELIST_EMAILS]:
            return True, 0

        # 動態白名單（資料庫）
        if self._is_whitelisted(email_lower):
            return True, 0

        # 黑名單檢查
        if self._is_blacklisted(email_lower):
            return False, 99999999  # 永久封鎖

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
            cooldown_end = last_used + timedelta(hours=5)
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
                VALUES (?, datetime('now', 'localtime'))
            ''', (email.lower(),))
            conn.commit()

    # ── Whitelist / Blacklist helpers ─────────────────────────────────────────

    def _is_whitelisted(self, email):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM whitelist WHERE email = ?', (email.lower(),))
            return cursor.fetchone() is not None

    def _is_blacklisted(self, email):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM blacklist WHERE email = ?', (email.lower(),))
            return cursor.fetchone() is not None

    def get_whitelist(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, note, added_at FROM whitelist ORDER BY added_at DESC')
            rows = cursor.fetchall()
            return [{'email': r[0], 'note': r[1], 'added_at': r[2]} for r in rows]

    def add_to_whitelist(self, email, note=''):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO whitelist (email, note) VALUES (?, ?)',
                    (email.lower(), note)
                )
                conn.commit()
                return True, '已加入白名單'
            except sqlite3.IntegrityError:
                return False, '此 Email 已在白名單中'

    def remove_from_whitelist(self, email):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM whitelist WHERE email = ?', (email.lower(),))
            conn.commit()
            return cursor.rowcount > 0

    def get_blacklist(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT email, reason, added_at FROM blacklist ORDER BY added_at DESC')
            rows = cursor.fetchall()
            return [{'email': r[0], 'reason': r[1], 'added_at': r[2]} for r in rows]

    def add_to_blacklist(self, email, reason=''):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO blacklist (email, reason) VALUES (?, ?)',
                    (email.lower(), reason)
                )
                conn.commit()
                return True, '已加入黑名單'
            except sqlite3.IntegrityError:
                return False, '此 Email 已在黑名單中'

    def remove_from_blacklist(self, email):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM blacklist WHERE email = ?', (email.lower(),))
            conn.commit()
            return cursor.rowcount > 0

    # ── Service deadline ───────────────────────────────────────────────────────

    def get_service_deadline(self):
        """取得服務截止時間（本地時間字串，格式 YYYY-MM-DD HH:MM:SS）；若未設定則回傳 None"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'service_deadline'")
            row = cursor.fetchone()
            return row[0] if row and row[0] else None

    def set_service_deadline(self, deadline_str):
        """設定服務截止時間（本地時間字串，格式 YYYY-MM-DD HH:MM:SS）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES ('service_deadline', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (deadline_str,)
            )
            conn.commit()

    def is_service_expired(self):
        """回傳目前服務是否已超過截止時間"""
        deadline_str = self.get_service_deadline()
        if not deadline_str:
            return False  # 未設定 deadline 就視為未過期
        try:
            deadline = datetime.fromisoformat(deadline_str)
            return datetime.now() > deadline
        except Exception:
            return False

    # ── Cooldown management ───────────────────────────────────────────────────

    def get_cooldown_list(self):
        """取得目前仍在冷卻期（5小時）內的所有 Email"""
        now = datetime.now()
        cooldown_hours = 5
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 每個 email 取最新一次使用記錄
            cursor.execute('''
                SELECT email, MAX(last_used) as last_used
                FROM email_usage
                GROUP BY email
                ORDER BY last_used DESC
            ''')
            rows = cursor.fetchall()

        result = []
        for email, last_used_str in rows:
            # 跳過靜態及動態白名單帳號
            if email in [e.lower() for e in self.WHITELIST_EMAILS]:
                continue
            if self._is_whitelisted(email):
                continue
            last_used = datetime.fromisoformat(last_used_str)
            cooldown_end = last_used + timedelta(hours=cooldown_hours)
            if now < cooldown_end:
                remaining_sec = (cooldown_end - now).total_seconds()
                remaining_h = int(remaining_sec // 3600)
                remaining_m = int((remaining_sec % 3600) // 60)
                result.append({
                    'email': email,
                    'last_used': last_used_str,
                    'cooldown_end': cooldown_end.strftime('%Y-%m-%d %H:%M:%S'),
                    'remaining_seconds': int(remaining_sec),
                    'remaining_display': f'{remaining_h} 小時 {remaining_m} 分鐘',
                })
        return result

    def remove_cooldown(self, email):
        """移除特定 email 的冷卻記錄（清空 email_usage 中該帳號所有記錄）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM email_usage WHERE email = ?', (email.lower(),))
            conn.commit()
            return cursor.rowcount > 0

    # ── Admin task control ────────────────────────────────────────────────────

    def admin_cancel_task(self, task_id):
        """取消特定任務（queued 或 processing）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE tasks SET status = 'cancelled',
                   error_message = '管理者手動取消',
                   completed_at = CURRENT_TIMESTAMP
                   WHERE task_id = ? AND status IN ('queued', 'processing')''',
                (task_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def admin_cancel_all(self, include_processing=True):
        """取消所有排隊中（及可選的處理中）任務"""
        statuses = ('queued', 'processing') if include_processing else ('queued',)
        placeholders = ','.join('?' * len(statuses))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'''UPDATE tasks SET status = 'cancelled',
                   error_message = '管理者批量取消',
                   completed_at = CURRENT_TIMESTAMP
                   WHERE status IN ({placeholders})''',
                statuses
            )
            conn.commit()
            return cursor.rowcount

    def admin_get_all_tasks(self, limit=100):
        """取得所有任務（管理者用，含完整 email）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, email, video_filename, status,
                       created_at, started_at, completed_at,
                       video_duration, error_message
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                pos = self.get_queue_position(r[0]) if r[3] == 'queued' else 0
                result.append({
                    'task_id': r[0], 'email': r[1], 'video_filename': r[2],
                    'status': r[3], 'created_at': r[4], 'started_at': r[5],
                    'completed_at': r[6], 'video_duration': r[7],
                    'error_message': r[8], 'queue_position': pos,
                })
            return result
    
    def admin_clear_history(self):
        """刪除所有已完成/失敗/取消的歷史記錄"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tasks WHERE status IN ('completed', 'failed', 'cancelled')"
            )
            conn.commit()
            return cursor.rowcount

    def add_task(self, task_id, email, video_filename, video_duration, params):
        """
        添加新任務到隊列
        返回: (成功, 訊息)
        """
        with self.lock:
            # 黑名單直接拒絕
            if self._is_blacklisted(email.lower()):
                return False, "此 Email 已被封鎖，無法使用此服務"

            # 檢查 email 冷卻
            available, remaining = self.check_email_cooldown(email)
            if not available:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                return False, f"此 Email 需等待 {hours} 小時 {minutes} 分鐘後才能再次使用"
            
            # 檢查影片時長（3分鐘 = 180秒）
            if video_duration and video_duration > 180:
                return False, f"影片時長 {video_duration:.1f} 秒超過限制（最多 180 秒）"
            
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
    
    def get_all_tasks(self, limit_completed=20):
        """獲取所有任務供排隊頁面顯示
        
        Returns:
            dict with:
              processing: list of processing tasks (max 1)
              queued: list of queued tasks sorted by created_at asc
              completed: list of recently completed/failed tasks sorted by completed_at desc
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            def mask_email(email):
                """遮蔽 email 中間部分保護隱私"""
                if not email or '@' not in email:
                    return email or ''
                local, domain = email.split('@', 1)
                if len(local) <= 2:
                    masked_local = local[0] + '***'
                else:
                    masked_local = local[:2] + '***'
                return f"{masked_local}@{domain}"

            # 正在處理中的任務
            cursor.execute('''
                SELECT task_id, email, video_filename, status,
                       created_at, started_at, completed_at, video_duration
                FROM tasks
                WHERE status = 'processing'
                ORDER BY started_at ASC
                LIMIT 1
            ''')
            processing_rows = cursor.fetchall()
            processing = [{
                'task_id': r[0],
                'email_masked': mask_email(r[1]),
                'video_filename': r[2],
                'status': r[3],
                'created_at': r[4],
                'started_at': r[5],
                'completed_at': r[6],
                'video_duration': r[7],
                'queue_position': 0,
            } for r in processing_rows]

            # 排隊中的任務（按提交時間升序）
            cursor.execute('''
                SELECT task_id, email, video_filename, status,
                       created_at, started_at, completed_at, video_duration
                FROM tasks
                WHERE status = 'queued'
                ORDER BY priority DESC, created_at ASC
            ''')
            queued_rows = cursor.fetchall()
            queued = [{
                'task_id': r[0],
                'email_masked': mask_email(r[1]),
                'video_filename': r[2],
                'status': r[3],
                'created_at': r[4],
                'started_at': r[5],
                'completed_at': r[6],
                'video_duration': r[7],
                'queue_position': idx + 1,
            } for idx, r in enumerate(queued_rows)]

            # 已完成 / 失敗 / 取消的任務（按完成時間降序）
            cursor.execute('''
                SELECT task_id, email, video_filename, status,
                       created_at, started_at, completed_at, video_duration
                FROM tasks
                WHERE status IN ('completed', 'failed', 'cancelled')
                ORDER BY completed_at DESC
                LIMIT ?
            ''', (limit_completed,))
            done_rows = cursor.fetchall()
            done = [{
                'task_id': r[0],
                'email_masked': mask_email(r[1]),
                'video_filename': r[2],
                'status': r[3],
                'created_at': r[4],
                'started_at': r[5],
                'completed_at': r[6],
                'video_duration': r[7],
                'queue_position': 0,
            } for r in done_rows]

            return {
                'processing': processing,
                'queued': queued,
                'done': done,
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
