# 排隊系統配置指南

## 功能說明

本系統新增了排隊功能，主要特性：

1. **Email 通知系統**：處理完成後自動發送郵件通知
2. **Email 冷卻期**：每個 Email 地址 5 天內只能使用一次
3. **影片時長限制**：僅支援 3 分鐘（180 秒）以內的影片
4. **後台處理**：用戶可以關閉網頁，系統在後台繼續處理
5. **本地儲存**：處理完成的影片會儲存在 `output_videos` 資料夾

## Email 設定

### 1. Gmail 設定（推薦）

#### 步驟 1：啟用兩步驟驗證
1. 前往 https://myaccount.google.com/security
2. 找到「兩步驟驗證」並啟用

#### 步驟 2：生成應用程式專用密碼
1. 前往 https://myaccount.google.com/apppasswords
2. 選擇「郵件」和您的裝置
3. 點擊「生成」
4. 複製生成的 16 位密碼（移除空格）

#### 步驟 3：配置環境變數
```bash
cp .env.example .env
```

編輯 `.env` 文件：
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-digit-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Deep Video Translation
```

### 2. 其他 Email 服務商

#### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### Yahoo Mail
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

## 使用說明

### 1. 安裝依賴
```bash
pip install python-dotenv
```

或者
```bash
pip install -r requirements.txt
```

### 2. 啟動服務
```bash
cd app
python main.py
```

系統會自動：
- 初始化資料庫（queue.db）
- 啟動後台任務處理器
- 監聽隊列中的任務

### 3. 使用網頁介面

1. 訪問 http://localhost:32123
2. 點擊「進入系統」進入主功能頁
3. 填寫必要資訊：
   - Email 地址（接收完成通知）
   - API Key
   - 上傳影片（≤ 3 分鐘）
4. 提交後可關閉網頁
5. 等待 Email 通知

## 資料庫結構

系統使用 SQLite 資料庫（`queue.db`）：

### tasks 表
- `task_id`: 任務唯一識別碼
- `email`: 用戶 Email
- `video_filename`: 影片檔名
- `video_duration`: 影片時長（秒）
- `status`: 狀態（queued, processing, completed, failed）
- `created_at`: 建立時間
- `started_at`: 開始處理時間
- `completed_at`: 完成時間
- `output_path`: 輸出檔案路徑
- `error_message`: 錯誤訊息（如果失敗）

### email_usage 表
- `email`: Email 地址
- `last_used`: 最後使用時間
- `usage_count`: 使用次數

## API 端點

### POST /process
提交新任務到隊列

**參數**：
- `email`: 用戶 Email（必須）
- `video`: 影片檔案（必須，≤ 3 分鐘）
- 其他現有參數...

**回應**：
```json
{
  "success": true,
  "task_id": "uuid",
  "message": "任務已加入隊列，您的位置是第 X 位",
  "queue_position": 1,
  "queue_stats": {
    "queued": 5,
    "processing": 1,
    "completed": 10,
    "failed": 2
  },
  "email": "user@example.com",
  "video_duration": "2:30"
}
```

### GET /queue/status/<task_id>
查詢任務狀態

**回應**：
```json
{
  "task_id": "uuid",
  "status": "queued",
  "queue_position": 3,
  "created_at": "2026-02-23T10:30:00",
  "video_filename": "video.mp4",
  "video_duration": "2:30"
}
```

### GET /queue/stats
獲取隊列統計

**回應**：
```json
{
  "queued": 5,
  "processing": 1,
  "completed": 120,
  "failed": 3,
  "total": 129
}
```

## 常見問題

### Q: 為什麼沒有收到 Email？
A: 
1. 檢查 `.env` 設定是否正確
2. 確認 SMTP 密碼是應用程式專用密碼（而非帳戶密碼）
3. 檢查垃圾郵件夾
4. 查看伺服器日誌

### Q: Email 冷卻期可以修改嗎？
A: 可以，在 `queue_manager.py` 中修改：
```python
cooldown_end = last_used + timedelta(days=5)  # 改為您想要的天數
```

### Q: 影片時長限制可以修改嗎？
A: 可以，在：
1. `queue_manager.py` 修改檢查邏輯
2. `main.py` 的 `/process` 路由中修改限制
3. 前端 `app.html` 更新提示文字

### Q: 如何清理舊任務？
A: 使用 Python 腳本：
```python
from queue_manager import QueueManager

qm = QueueManager()
deleted = qm.cleanup_old_tasks(days=30)  # 清理 30 天前的任務
print(f"已刪除 {deleted} 個舊任務")
```

### Q: 如何查看隊列狀態？
A: 訪問 http://localhost:32123/queue/stats

## 注意事項

1. **安全性**：
   - 不要將 `.env` 文件上傳到版本控制系統
   - 使用應用程式專用密碼，不是帳戶密碼
   - 定期更換密碼

2. **效能**：
   - 後台處理器每 5 秒檢查一次隊列
   - 大檔案 Email 附件限制 20MB
   - 超過限制的檔案僅發送下載連結

3. **儲存空間**：
   - 完成的影片會儲存在 `output_videos/`
   - 定期清理舊檔案以節省空間
   - 建議使用 `cleanup_old_tasks()` 定期清理資料庫

## 排查日誌

後台處理器會輸出詳細日誌：
```
✅ 後台任務處理器已啟動
🔄 開始監聽任務隊列...
📝 開始處理任務: task-uuid
   Email: user@example.com
   影片: video.mp4
📧 發送完成通知給: user@example.com
✅ 任務完成: task-uuid
```

查看日誌可以了解系統運行狀態。
