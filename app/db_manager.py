#!/usr/bin/env python3
"""
資料庫管理工具
"""
import sqlite3
import os
from datetime import datetime, timedelta
from queue_manager import QueueManager

def show_tasks():
    """顯示所有任務"""
    qm = QueueManager()
    
    with sqlite3.connect(qm.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT task_id, email, video_filename, status, created_at, queue_position
            FROM (
                SELECT task_id, email, video_filename, status, created_at,
                       ROW_NUMBER() OVER (ORDER BY created_at) as queue_position
                FROM tasks
                WHERE status = 'queued'
            )
            UNION ALL
            SELECT task_id, email, video_filename, status, created_at, 0 as queue_position
            FROM tasks
            WHERE status != 'queued'
            ORDER BY created_at DESC
        ''')
        
        tasks = cursor.fetchall()
        
        if not tasks:
            print("📭 沒有任務")
            return
        
        print("\n📋 任務列表:\n")
        print(f"{'任務 ID':<40} {'Email':<30} {'檔名':<20} {'狀態':<12} {'隊列位置':<8} {'建立時間'}")
        print("-" * 140)
        
        for task in tasks:
            task_id, email, filename, status, created_at, queue_pos = task
            queue_str = f"第 {queue_pos} 位" if queue_pos > 0 else "-"
            status_emoji = {
                'queued': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(status, '')
            
            print(f"{task_id[:36]:<40} {email:<30} {filename[:18]:<20} {status_emoji}{status:<11} {queue_str:<8} {created_at}")


def show_email_usage():
    """顯示 Email 使用記錄"""
    qm = QueueManager()
    
    with sqlite3.connect(qm.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT email, last_used, usage_count
            FROM email_usage
            ORDER BY last_used DESC
        ''')
        
        records = cursor.fetchall()
        
        if not records:
            print("📭 沒有使用記錄")
            return
        
        print("\n📧 Email 使用記錄:\n")
        print(f"{'Email':<40} {'最後使用':<25} {'使用次數':<10} {'冷卻狀態'}")
        print("-" * 90)
        
        now = datetime.now()
        for email, last_used, usage_count in records:
            last_used_dt = datetime.fromisoformat(last_used)
            cooldown_end = last_used_dt + timedelta(days=5)
            
            if now < cooldown_end:
                remaining = cooldown_end - now
                hours = int(remaining.total_seconds() // 3600)
                days = hours // 24
                hours = hours % 24
                status = f"🔒 {days}天{hours}小時"
            else:
                status = "✅ 可用"
            
            print(f"{email:<40} {last_used:<25} {usage_count:<10} {status}")


def cleanup_db(days=30):
    """清理舊任務"""
    qm = QueueManager()
    deleted = qm.cleanup_old_tasks(days)
    print(f"\n🗑️  已刪除 {deleted} 個超過 {days} 天的舊任務")


def reset_db():
    """重置資料庫（警告：會刪除所有數據）"""
    response = input("\n⚠️  確定要重置資料庫嗎？這將刪除所有任務和使用記錄！(yes/no): ")
    if response.lower() != 'yes':
        print("❌ 已取消")
        return
    
    db_path = 'queue.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ 資料庫已重置")
        
        # 重新初始化
        QueueManager()
        print("✅ 資料庫已重新初始化")
    else:
        print("ℹ️  資料庫不存在")


def show_stats():
    """顯示統計信息"""
    qm = QueueManager()
    stats = qm.get_queue_stats()
    
    print("\n📊 隊列統計:\n")
    print(f"   ⏳ 排隊中: {stats['queued']}")
    print(f"   🔄 處理中: {stats['processing']}")
    print(f"   ✅ 已完成: {stats['completed']}")
    print(f"   ❌ 失敗: {stats['failed']}")
    print(f"   📝 總計: {stats['total']}")


def main():
    """主菜單"""
    while True:
        print("\n" + "="*60)
        print("📚 資料庫管理工具")
        print("="*60)
        print("\n選擇操作:")
        print("  1. 📋 顯示所有任務")
        print("  2. 📧 顯示 Email 使用記錄")
        print("  3. 📊 顯示統計信息")
        print("  4. 🗑️  清理舊任務（30天前）")
        print("  5. ⚠️  重置資料庫（刪除所有數據）")
        print("  0. 🚪 退出")
        print()
        
        choice = input("請輸入選項 (0-5): ").strip()
        
        if choice == '1':
            show_tasks()
        elif choice == '2':
            show_email_usage()
        elif choice == '3':
            show_stats()
        elif choice == '4':
            cleanup_db(30)
        elif choice == '5':
            reset_db()
        elif choice == '0':
            print("\n👋 再見！")
            break
        else:
            print("\n❌ 無效選項，請重新選擇")
        
        input("\n按 Enter 繼續...")


if __name__ == '__main__':
    main()
