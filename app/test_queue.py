#!/usr/bin/env python3
"""
排隊系統測試腳本
"""
from queue_manager import QueueManager
from email_service import EmailService
import uuid

def test_queue_system():
    """測試排隊系統基本功能"""
    print("🧪 開始測試排隊系統...\n")
    
    qm = QueueManager()
    
    # 測試 1: Email 冷卻期檢查
    print("📧 測試 1: Email 冷卻期檢查")
    test_email = "test@example.com"
    available, remaining = qm.check_email_cooldown(test_email)
    print(f"   Email: {test_email}")
    print(f"   可用: {available}")
    print(f"   剩餘冷卻時間: {remaining} 秒")
    print()
    
    # 測試 2: 添加任務
    print("📝 測試 2: 添加任務到隊列")
    task_id = str(uuid.uuid4())
    params = {
        'input_path': 'test_video.mp4',
        'output_path': 'test_output.mp4',
        'api_key': 'test_key',
        'voice_language': '日文'
    }
    
    success, message = qm.add_task(
        task_id,
        test_email,
        'test_video.mp4',
        120.0,  # 2 分鐘
        params
    )
    
    print(f"   結果: {'成功' if success else '失敗'}")
    print(f"   訊息: {message}")
    print()
    
    # 測試 3: 查詢任務信息
    print("🔍 測試 3: 查詢任務信息")
    task_info = qm.get_task_info(task_id)
    if task_info:
        print(f"   任務 ID: {task_info['task_id']}")
        print(f"   Email: {task_info['email']}")
        print(f"   狀態: {task_info['status']}")
        print(f"   隊列位置: {task_info['queue_position']}")
        print(f"   影片時長: {task_info['video_duration']} 秒")
    else:
        print("   ❌ 找不到任務")
    print()
    
    # 測試 4: 獲取隊列統計
    print("📊 測試 4: 隊列統計")
    stats = qm.get_queue_stats()
    print(f"   排隊中: {stats['queued']}")
    print(f"   處理中: {stats['processing']}")
    print(f"   已完成: {stats['completed']}")
    print(f"   失敗: {stats['failed']}")
    print(f"   總計: {stats['total']}")
    print()
    
    # 測試 5: Email 冷卻期（再次測試）
    print("📧 測試 5: 再次檢查 Email 冷卻期")
    available, remaining = qm.check_email_cooldown(test_email)
    print(f"   可用: {available}")
    if not available:
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        days = hours // 24
        hours = hours % 24
        print(f"   需等待: {days} 天 {hours} 小時 {minutes} 分鐘")
    print()
    
    # 測試 6: 超時影片檢查
    print("🎬 測試 6: 超長影片檢查")
    long_video_id = str(uuid.uuid4())
    success, message = qm.add_task(
        long_video_id,
        "another@example.com",
        'long_video.mp4',
        240.0,  # 4 分鐘（超過 3 分鐘限制）
        params
    )
    print(f"   結果: {'成功' if success else '失敗'}")
    print(f"   訊息: {message}")
    print()
    
    print("✅ 測試完成！\n")
    print("💡 提示：")
    print("   - 資料庫文件位於: queue.db")
    print("   - 可使用 SQLite 瀏覽器查看資料庫內容")
    print("   - 測試數據可以手動刪除或使用 cleanup_old_tasks()")


def test_email_service():
    """測試 Email 服務配置"""
    print("\n📧 測試 Email 服務配置...\n")
    
    es = EmailService()
    
    print(f"SMTP 伺服器: {es.smtp_server}")
    print(f"SMTP 端口: {es.smtp_port}")
    print(f"SMTP 用戶: {es.smtp_user if es.smtp_user else '❌ 未設定'}")
    print(f"寄件人: {es.from_email}")
    print(f"寄件人名稱: {es.from_name}")
    
    if not es.smtp_user or not es.smtp_password:
        print("\n⚠️  警告：SMTP 設定未完成")
        print("   請參考 .env.example 配置 SMTP 設定")
        print("   配置完成後才能發送郵件通知")
    else:
        print("\n✅ SMTP 設定已配置")


if __name__ == '__main__':
    test_queue_system()
    test_email_service()
