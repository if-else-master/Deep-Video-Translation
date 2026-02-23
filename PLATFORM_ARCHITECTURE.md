# 🎬 影片深度翻譯平台 - 系統架構設計

## 📋 目錄
- [一、整體架構](#一整體架構)
- [二、技術棧選擇與比較](#二技術棧選擇與比較)
- [三、資料庫設計](#三資料庫設計)
- [四、系統模組設計](#四系統模組設計)
- [五、前端架構](#五前端架構)
- [六、後端架構](#六後端架構)
- [七、任務排隊系統](#七任務排隊系統)
- [八、Email 通知系統](#八email-通知系統)
- [九、安全性設計](#九安全性設計)
- [十、部署架構](#十部署架構)
- [十一、開發階段規劃](#十一開發階段規劃)

---

## 一、整體架構

```
┌─────────────────────────────────────────────────────────────────┐
│                         使用者瀏覽器                               │
├─────────────────────────────────────────────────────────────────┤
│                React 前端應用 (Vite + TypeScript)                 │
│  ┌───────────┬──────────┬──────────┬──────────┬─────────────┐   │
│  │   登入/   │  上傳    │  任務    │  結果    │  個人設定   │   │
│  │   註冊    │  介面    │  列表    │  下載    │  頁面       │   │
│  └───────────┴──────────┴──────────┴──────────┴─────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / REST API / WebSocket
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Nginx 反向代理 + SSL                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌─────────────────────┐              ┌──────────────────────┐
│   Flask REST API    │              │  WebSocket Server    │
│   (認證、任務管理)    │              │  (實時狀態推送)       │
└──────────┬──────────┘              └──────────────────────┘
           │
           ├─────────────┬──────────────┬──────────────┐
           ↓             ↓              ↓              ↓
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │PostgreSQL│  │  Redis   │  │  Celery  │  │  Email   │
    │   資料庫 │  │  快取/   │  │  Worker  │  │  Service │
    │          │  │  佇列    │  │  背景任務│  │          │
    └──────────┘  └──────────┘  └────┬─────┘  └──────────┘
                                     │
                                     ↓
                            ┌─────────────────┐
                            │  Video Processor│
                            │  ├─ Gemini API  │
                            │  ├─ XTTS-v2     │
                            │  ├─ F5-TTS      │
                            │  ├─ Wav2Lip     │
                            │  └─ EasyOCR     │
                            └─────────────────┘
                                     ↓
                            ┌─────────────────┐
                            │  本地檔案儲存    │
                            │  /outputs       │
                            │  /temp          │
                            └─────────────────┘
```

---

## 二、技術棧選擇與比較

### 2.1 後端框架：Python Flask vs Node.js

| 考量因素 | Python Flask (推薦 ✅) | Node.js Express |
|---------|----------------------|-----------------|
| **現有代碼兼容** | ✅ 完全兼容現有 Python 代碼 | ❌ 需要重寫所有 AI 處理邏輯 |
| **AI 生態系** | ✅ PyTorch、TTS、OpenCV 原生支援 | ⚠️ 需要透過 Python 橋接 |
| **開發速度** | ✅ 可直接在現有基礎上擴展 | ❌ 需從頭開始 |
| **性能** | ⚠️ 單線程（但用 Celery 解決） | ✅ 異步 I/O |
| **工程師熟悉度** | ✅ 你已經使用 Python | ⚠️ 需要學習 Node.js |
| **部署簡便性** | ✅ Docker 容器化 | ✅ Docker 容器化 |

**建議：使用 Python Flask**
- 保留所有現有的 AI 處理代碼
- 避免重複造輪子
- Flask 社群龐大，文檔完整

### 2.2 完整技術棧

#### 前端
- **框架**: React 18 + TypeScript
- **構建工具**: Vite
- **狀態管理**: Zustand（輕量級）或 Redux Toolkit
- **UI 組件庫**: 
  - Tailwind CSS（快速開發）
  - Shadcn/ui（高品質組件）
  - Radix UI（無障礙支援）
- **表單管理**: React Hook Form + Zod
- **HTTP 客戶端**: Axios
- **WebSocket**: Socket.io-client
- **主題切換**: next-themes

#### 後端
- **Web 框架**: Flask 3.0
- **認證**: Flask-JWT-Extended
- **資料庫 ORM**: SQLAlchemy 2.0
- **遷移工具**: Alembic
- **任務佇列**: Celery 5.3
- **消息代理**: Redis 7.0
- **WebSocket**: Flask-SocketIO
- **API 文檔**: Flask-RESTX（Swagger UI）
- **輸入驗證**: Marshmallow
- **郵件**: Flask-Mail + SMTP

#### 資料庫
- **主資料庫**: PostgreSQL 15
- **快取 & 佇列**: Redis 7.0

#### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **SSL**: Let's Encrypt (Certbot)
- **監控**: Prometheus + Grafana（可選）

---

## 三、資料庫設計

### 3.1 PostgreSQL Schema

```sql
-- ===========================
-- 使用者表
-- ===========================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    
    -- 帳號狀態
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    
    -- 使用配額（防濫用）
    total_translations INT DEFAULT 0,              -- 總翻譯次數
    monthly_translations INT DEFAULT 0,             -- 本月翻譯次數
    max_monthly_translations INT DEFAULT 10,        -- 每月上限
    last_reset_date DATE,                           -- 配額重置日期
    
    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- 索引
    INDEX idx_email (email),
    INDEX idx_verification_token (verification_token)
);

-- ===========================
-- 翻譯任務表
-- ===========================
CREATE TABLE translation_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) UNIQUE NOT NULL,           -- UUID
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 檔案資訊
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,                               -- bytes
    duration FLOAT,                                 -- seconds
    
    -- 任務設定
    source_language VARCHAR(50) DEFAULT 'auto',
    target_language VARCHAR(50) NOT NULL,
    tts_engine VARCHAR(50) DEFAULT 'xtts',          -- xtts, f5tts
    enable_lip_sync BOOLEAN DEFAULT TRUE,
    enable_ppt_translation BOOLEAN DEFAULT FALSE,
    
    -- 任務狀態
    status VARCHAR(50) DEFAULT 'pending',           -- pending, queued, processing, completed, failed
    queue_position INT,                             -- 佇列位置
    progress INT DEFAULT 0,                         -- 0-100
    
    -- 處理資訊
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time INT,                            -- seconds
    error_message TEXT,
    
    -- 輸出檔案
    output_path VARCHAR(500),
    output_size BIGINT,
    
    -- 下載資訊
    download_token VARCHAR(255),                    -- 下載連結 token
    download_count INT DEFAULT 0,
    expires_at TIMESTAMP,                           -- 檔案過期時間（30天）
    
    -- 通知狀態
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    
    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_queue_position (queue_position)
);

-- ===========================
-- 任務日誌表
-- ===========================
CREATE TABLE task_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL REFERENCES translation_tasks(task_id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) DEFAULT 'info',               -- info, warning, error
    message TEXT NOT NULL,
    
    INDEX idx_task_id (task_id),
    INDEX idx_timestamp (timestamp)
);

-- ===========================
-- 驗證碼表（防機器人註冊）
-- ===========================
CREATE TABLE captcha_records (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    captcha_text VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at)
);

-- ===========================
-- 系統設定表
-- ===========================
CREATE TABLE system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================
-- 預設系統設定
-- ===========================
INSERT INTO system_settings (key, value, description) VALUES
('max_file_size_mb', '500', '最大上傳檔案大小（MB）'),
('max_queue_size', '50', '任務佇列最大數量'),
('file_retention_days', '30', '檔案保留天數'),
('enable_registration', 'true', '是否開放註冊'),
('maintenance_mode', 'false', '維護模式');
```

### 3.2 Redis 資料結構

```python
# 任務佇列
task_queue = "celery:task_queue"                    # List：待處理任務

# 快取
user_session = f"session:{user_id}"                 # Hash：使用者 session
task_cache = f"task:{task_id}"                      # Hash：任務快取資料
task_progress = f"progress:{task_id}"               # String：任務進度

# 限流（Rate Limiting）
rate_limit_upload = f"rate:upload:{user_id}"        # String：上傳限制
rate_limit_api = f"rate:api:{user_id}"              # String：API 限制

# 下載 Token
download_token = f"download:{token}"                # String：下載憑證

# 快取過期時間
TTL_SESSION = 86400                                 # 24小時
TTL_TASK_CACHE = 3600                               # 1小時
TTL_DOWNLOAD_TOKEN = 86400                          # 24小時
TTL_RATE_LIMIT = 60                                 # 1分鐘
```

---

## 四、系統模組設計

### 4.1 後端模組結構

```
backend/
├── app/
│   ├── __init__.py              # Flask app 初始化
│   ├── config.py                # 配置管理
│   ├── extensions.py            # 擴展初始化（db, redis, celery）
│   │
│   ├── models/                  # 資料模型
│   │   ├── __init__.py
│   │   ├── user.py              # 使用者模型
│   │   ├── task.py              # 任務模型
│   │   ├── log.py               # 日誌模型
│   │   └── captcha.py           # 驗證碼模型
│   │
│   ├── schemas/                 # API 輸入輸出驗證
│   │   ├── __init__.py
│   │   ├── auth.py              # 認證相關 schema
│   │   ├── task.py              # 任務相關 schema
│   │   └── user.py              # 使用者相關 schema
│   │
│   ├── api/                     # REST API 路由
│   │   ├── __init__.py
│   │   ├── auth.py              # /api/auth/* - 認證相關
│   │   ├── tasks.py             # /api/tasks/* - 任務管理
│   │   ├── users.py             # /api/users/* - 使用者資訊
│   │   └── system.py            # /api/system/* - 系統資訊
│   │
│   ├── services/                # 業務邏輯層
│   │   ├── __init__.py
│   │   ├── auth_service.py      # 認證服務
│   │   ├── task_service.py      # 任務管理服務
│   │   ├── email_service.py     # 郵件服務
│   │   ├── captcha_service.py   # 驗證碼服務
│   │   └── storage_service.py   # 檔案儲存服務
│   │
│   ├── tasks/                   # Celery 背景任務
│   │   ├── __init__.py
│   │   ├── video_tasks.py       # 影片處理任務
│   │   └── email_tasks.py       # 郵件發送任務
│   │
│   ├── core/                    # 核心處理邏輯（保留現有代碼）
│   │   ├── __init__.py
│   │   ├── video_processor.py   # 影片處理器
│   │   ├── txtvoice.py          # 語音識別
│   │   ├── xttsv.py             # XTTS 語音合成
│   │   ├── f5ttsv.py            # F5-TTS 語音合成
│   │   └── ImageHash_ppt.py     # PPT 翻譯
│   │
│   ├── middleware/              # 中間件
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT 驗證中間件
│   │   ├── rate_limit.py        # 限流中間件
│   │   └── error_handler.py     # 錯誤處理
│   │
│   ├── utils/                   # 工具函數
│   │   ├── __init__.py
│   │   ├── security.py          # 安全相關（密碼加密）
│   │   ├── validators.py        # 驗證器
│   │   ├── helpers.py           # 輔助函數
│   │   └── constants.py         # 常數定義
│   │
│   └── websocket/               # WebSocket 處理
│       ├── __init__.py
│       └── events.py            # WebSocket 事件
│
├── migrations/                  # Alembic 資料庫遷移
├── tests/                       # 測試
├── requirements.txt
└── celery_worker.py             # Celery Worker 入口
```

### 4.2 前端模組結構

```
frontend/
├── src/
│   ├── main.tsx                 # 應用入口
│   ├── App.tsx                  # 根組件
│   │
│   ├── pages/                   # 頁面組件
│   │   ├── HomePage.tsx         # 首頁（產品介紹）
│   │   ├── AuthPage.tsx         # 登入/註冊頁
│   │   ├── DashboardPage.tsx    # 使用者儀表板
│   │   ├── UploadPage.tsx       # 上傳頁面
│   │   ├── TasksPage.tsx        # 任務列表
│   │   ├── ProfilePage.tsx      # 個人設定
│   │   └── NotFoundPage.tsx     # 404 頁面
│   │
│   ├── components/              # 共用組件
│   │   ├── Layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainLayout.tsx
│   │   │
│   │   ├── Auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── Captcha.tsx
│   │   │
│   │   ├── Task/
│   │   │   ├── TaskCard.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskStatus.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── LogViewer.tsx
│   │   │
│   │   ├── Upload/
│   │   │   ├── FileDropzone.tsx
│   │   │   ├── UploadForm.tsx
│   │   │   └── LanguageSelector.tsx
│   │   │
│   │   └── ui/                  # 基礎 UI 組件（Shadcn/ui）
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Card.tsx
│   │       ├── Dialog.tsx
│   │       └── ...
│   │
│   ├── stores/                  # 狀態管理（Zustand）
│   │   ├── authStore.ts         # 認證狀態
│   │   ├── taskStore.ts         # 任務狀態
│   │   └── themeStore.ts        # 主題狀態
│   │
│   ├── services/                # API 服務
│   │   ├── api.ts               # Axios 實例配置
│   │   ├── authService.ts       # 認證 API
│   │   ├── taskService.ts       # 任務 API
│   │   └── userService.ts       # 使用者 API
│   │
│   ├── hooks/                   # 自訂 Hooks
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   ├── useTask.ts
│   │   └── useTheme.ts
│   │
│   ├── types/                   # TypeScript 類型定義
│   │   ├── auth.ts
│   │   ├── task.ts
│   │   └── api.ts
│   │
│   ├── utils/                   # 工具函數
│   │   ├── formatters.ts        # 格式化函數
│   │   ├── validators.ts        # 驗證函數
│   │   └── constants.ts         # 常數
│   │
│   └── styles/                  # 樣式
│       ├── globals.css          # 全局樣式
│       └── themes/              # 主題配置
│           ├── light.css
│           └── dark.css
│
├── public/
│   ├── index.html
│   └── assets/
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

---

## 五、前端架構

### 5.1 頁面流程

```
┌─────────────────┐
│   Landing Page  │ ← 未登入使用者
│   （產品介紹）   │
└────────┬────────┘
         │
         ├──→ 註冊 ──→ Email 驗證 ──┐
         │                          │
         ├──→ 登入 ─────────────────┤
         │                          ↓
         │                   ┌──────────────┐
         │                   │  Dashboard   │
         │                   │  （儀表板）   │
         │                   └──────┬───────┘
         │                          │
         │                   ┌──────┴───────┐
         │                   │              │
         │              ┌────▼─────┐  ┌────▼─────┐
         │              │  Upload  │  │  Tasks   │
         │              │  上傳頁  │  │  任務列表│
         │              └──────────┘  └──────────┘
         │                                │
         └────────────────────────────────┴──→ 登出
```

### 5.2 核心功能組件

#### 1. 首頁（Landing Page）
```typescript
// 一頁式介紹，包含：
- Hero Section（主視覺區）
- Features（功能特色）
- How It Works（使用流程）
- Pricing（定價方案，目前免費）
- CTA（行動呼籲 - 立即開始）
```

#### 2. 認證頁面
```typescript
interface AuthFormProps {
  mode: 'login' | 'register';
}

// 註冊表單欄位
interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  captcha: string;
}

// 登入表單欄位
interface LoginFormData {
  email: string;
  password: string;
  remember: boolean;
}
```

#### 3. 上傳介面
```typescript
interface UploadFormData {
  file: File;
  sourceLanguage: string;      // 'auto', 'zh-TW', 'en', 'ja'
  targetLanguage: string;       // 'zh-TW', 'en', 'ja'
  ttsEngine: 'xtts' | 'f5tts';
  enableLipSync: boolean;
  enablePptTranslation: boolean;
}

// 拖拽上傳支援
// 檔案大小驗證（最大 500MB）
// 格式驗證（.mp4, .mov, .avi, .mkv）
```

#### 4. 任務列表
```typescript
interface Task {
  id: string;
  filename: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;              // 0-100
  queuePosition?: number;
  createdAt: string;
  completedAt?: string;
  outputUrl?: string;
  errorMessage?: string;
}

// 功能：
- 即時狀態更新（WebSocket）
- 進度條顯示
- 日誌查看
- 下載結果
- 刪除任務
```

### 5.3 UI 設計規範

#### 色彩方案

**淺色主題（Light Mode）**
```css
:root {
  /* 主色調 - 科技藍紫 */
  --primary-50: #f5f3ff;
  --primary-100: #ede9fe;
  --primary-500: #8b5cf6;      /* 主色 */
  --primary-600: #7c3aed;
  --primary-700: #6d28d9;
  
  /* 背景 */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;
  
  /* 文字 */
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-tertiary: #9ca3af;
  
  /* 邊框 */
  --border-primary: #e5e7eb;
  --border-secondary: #d1d5db;
  
  /* 狀態色 */
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
}
```

**深色主題（Dark Mode）**
```css
.dark {
  /* 主色調 */
  --primary-500: #a78bfa;
  --primary-600: #8b5cf6;
  --primary-700: #7c3aed;
  
  /* 背景 */
  --bg-primary: #0f172a;        /* 深藍黑 */
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  
  /* 文字 */
  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
  --text-tertiary: #94a3b8;
  
  /* 邊框 */
  --border-primary: #334155;
  --border-secondary: #475569;
}
```

#### 設計原則
- ✨ **科技感**：使用漸層、毛玻璃效果、微妙動畫
- 🎨 **低飽和度**：避免鮮艷色彩，使用柔和的紫藍色系
- 📱 **響應式**：支援桌面、平板、手機
- ♿ **無障礙**：符合 WCAG 2.1 AA 標準
- 🌓 **主題切換**：流暢的深淺色模式切換

---

## 六、後端架構

### 6.1 API 端點設計

#### 認證相關 (`/api/auth`)

| 方法 | 端點 | 說明 | 認證 |
|-----|------|------|-----|
| POST | `/register` | 使用者註冊 | ❌ |
| POST | `/login` | 使用者登入 | ❌ |
| POST | `/logout` | 使用者登出 | ✅ |
| POST | `/refresh` | 刷新 JWT Token | ✅ |
| POST | `/verify-email` | 驗證 Email | ❌ |
| GET | `/captcha` | 取得驗證碼圖片 | ❌ |

#### 任務相關 (`/api/tasks`)

| 方法 | 端點 | 說明 | 認證 |
|-----|------|------|-----|
| POST | `/upload` | 上傳影片並建立任務 | ✅ |
| GET | `/` | 取得使用者所有任務列表 | ✅ |
| GET | `/:id` | 取得特定任務詳情 | ✅ |
| GET | `/:id/logs` | 取得任務日誌 | ✅ |
| GET | `/:id/progress` | 取得任務進度 | ✅ |
| DELETE | `/:id` | 刪除任務 | ✅ |
| GET | `/download/:token` | 下載翻譯後的影片 | ❌ |

#### 使用者相關 (`/api/users`)

| 方法 | 端點 | 說明 | 認證 |
|-----|------|------|-----|
| GET | `/me` | 取得當前使用者資訊 | ✅ |
| PUT | `/me` | 更新使用者資訊 | ✅ |
| PUT | `/me/password` | 修改密碼 | ✅ |
| GET | `/me/quota` | 取得使用配額 | ✅ |

#### 系統相關 (`/api/system`)

| 方法 | 端點 | 說明 | 認證 |
|-----|------|------|-----|
| GET | `/status` | 系統狀態 | ❌ |
| GET | `/queue` | 佇列狀態 | ✅ |
| GET | `/languages` | 支援的語言列表 | ❌ |

### 6.2 認證流程

#### JWT 架構
```python
# Access Token（短期）
{
  "user_id": 123,
  "email": "user@example.com",
  "exp": 1234567890,        # 15 分鐘過期
  "type": "access"
}

# Refresh Token（長期）
{
  "user_id": 123,
  "exp": 1234567890,        # 7 天過期
  "type": "refresh"
}
```

#### 認證中間件
```python
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        return fn(current_user_id, *args, **kwargs)
    return wrapper
```

### 6.3 輸入驗證範例

```python
# schemas/auth.py
from marshmallow import Schema, fields, validate

class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128)
    )
    captcha = fields.Str(required=True, validate=validate.Length(equal=6))

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)
```

---

## 七、任務排隊系統

### 7.1 Celery 架構

```python
# celery_worker.py
from celery import Celery
from app.config import Config

celery = Celery(
    'video_translation',
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Taipei',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,           # 1 小時超時
    worker_prefetch_multiplier=1,   # 一次只處理一個任務
    worker_max_tasks_per_child=10,  # 處理 10 個任務後重啟 worker
)

# 任務路由
celery.conf.task_routes = {
    'app.tasks.video_tasks.*': {'queue': 'video_queue'},
    'app.tasks.email_tasks.*': {'queue': 'email_queue'},
}
```

### 7.2 背景任務實作

```python
# app/tasks/video_tasks.py
from app.extensions import celery, db
from app.models.task import TranslationTask
from app.services.email_service import send_completion_email
from app.core.video_processor import VideoProcessor
import traceback

@celery.task(bind=True, name='process_video_translation')
def process_video_translation(self, task_id: str):
    """
    背景處理影片翻譯
    
    Args:
        task_id: 任務 ID
    """
    task = TranslationTask.query.filter_by(task_id=task_id).first()
    if not task:
        return {'error': 'Task not found'}
    
    try:
        # 更新狀態為處理中
        task.status = 'processing'
        task.queue_position = None
        task.started_at = datetime.utcnow()
        db.session.commit()
        
        # 初始化處理器，傳入進度回調
        def progress_callback(message: str, progress: int):
            task.progress = progress
            task.add_log(message)
            db.session.commit()
            
            # 透過 WebSocket 推送即時進度
            from app.websocket.events import emit_task_update
            emit_task_update(task_id, {
                'progress': progress,
                'message': message
            })
        
        processor = VideoProcessor(progress_callback=progress_callback)
        
        # 執行完整翻譯流程
        output_path = processor.process_complete_video(
            video_path=task.file_path,
            api_key=Config.GEMINI_API_KEY,
            source_language=task.source_language,
            target_language=task.target_language,
            tts_engine=task.tts_engine,
            enable_lip_sync=task.enable_lip_sync,
            enable_ppt_translation=task.enable_ppt_translation
        )
        
        # 更新任務完成狀態
        task.status = 'completed'
        task.progress = 100
        task.output_path = output_path
        task.completed_at = datetime.utcnow()
        task.processing_time = (task.completed_at - task.started_at).total_seconds()
        
        # 生成下載 token
        import secrets
        task.download_token = secrets.token_urlsafe(32)
        task.expires_at = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        # 發送完成通知郵件
        send_completion_email.delay(task_id)
        
        return {'status': 'completed', 'output_path': output_path}
        
    except Exception as e:
        # 錯誤處理
        error_msg = str(e)
        task.status = 'failed'
        task.error_message = error_msg
        task.add_log(f'錯誤: {error_msg}', level='error')
        task.add_log(traceback.format_exc(), level='error')
        db.session.commit()
        
        return {'status': 'failed', 'error': error_msg}
```

### 7.3 佇列管理

```python
# app/services/task_service.py
class TaskService:
    @staticmethod
    def create_task(user_id: int, file_path: str, **params) -> TranslationTask:
        """建立新任務並加入佇列"""
        import uuid
        
        # 建立任務記錄
        task = TranslationTask(
            task_id=str(uuid.uuid4()),
            user_id=user_id,
            file_path=file_path,
            status='pending',
            **params
        )
        db.session.add(task)
        db.session.commit()
        
        # 加入 Celery 佇列
        from app.tasks.video_tasks import process_video_translation
        process_video_translation.apply_async(
            args=[task.task_id],
            queue='video_queue'
        )
        
        # 更新佇列位置
        task.status = 'queued'
        task.queue_position = TaskService.get_queue_size()
        db.session.commit()
        
        return task
    
    @staticmethod
    def get_queue_size() -> int:
        """取得目前佇列大小"""
        from celery.task.control import inspect
        i = inspect()
        active = i.active()
        reserved = i.reserved()
        
        total = 0
        if active:
            total += sum(len(tasks) for tasks in active.values())
        if reserved:
            total += sum(len(tasks) for tasks in reserved.values())
        
        return total
```

---

## 八、Email 通知系統

### 8.1 郵件服務配置

```python
# config.py
class Config:
    # Flask-Mail 配置
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@deepvideotranslation.com')
```

### 8.2 郵件模板

```python
# app/services/email_service.py
from flask_mail import Mail, Message
from flask import render_template
from app.extensions import celery

mail = Mail()

@celery.task(name='send_completion_email')
def send_completion_email(task_id: str):
    """發送翻譯完成通知"""
    from app.models.task import TranslationTask
    
    task = TranslationTask.query.filter_by(task_id=task_id).first()
    if not task or not task.user:
        return
    
    # 生成下載連結
    download_url = f"{Config.FRONTEND_URL}/download/{task.download_token}"
    
    # 渲染郵件內容
    html_body = render_template(
        'emails/completion.html',
        user_email=task.user.email,
        filename=task.original_filename,
        download_url=download_url,
        processing_time=task.processing_time,
        expires_at=task.expires_at
    )
    
    # 發送郵件
    msg = Message(
        subject='🎉 影片翻譯完成通知',
        recipients=[task.user.email],
        html=html_body
    )
    
    try:
        mail.send(msg)
        task.email_sent = True
        task.email_sent_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        print(f"郵件發送失敗: {e}")
```

### 8.3 郵件模板 HTML

```html
<!-- templates/emails/completion.html -->
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #8b5cf6;
            margin: 0;
        }
        .content {
            line-height: 1.6;
            color: #333;
        }
        .button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            margin: 20px 0;
            font-weight: bold;
        }
        .info {
            background: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 影片翻譯完成！</h1>
        </div>
        
        <div class="content">
            <p>親愛的使用者，</p>
            
            <p>您的影片 <strong>{{ filename }}</strong> 已完成翻譯處理！</p>
            
            <div class="info">
                <p><strong>處理資訊：</strong></p>
                <ul>
                    <li>處理時間：{{ processing_time }} 秒</li>
                    <li>檔案保留期限：{{ expires_at.strftime('%Y-%m-%d') }}</li>
                </ul>
            </div>
            
            <div style="text-align: center;">
                <a href="{{ download_url }}" class="button">
                    📥 立即下載
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                ⚠️ 下載連結將在 30 天後失效，請及時下載。
            </p>
        </div>
        
        <div class="footer">
            <p>Deep Video Translation Platform</p>
            <p>這是系統自動發送的郵件，請勿直接回覆。</p>
        </div>
    </div>
</body>
</html>
```

### 8.4 防濫用機制

```python
# app/middleware/rate_limit.py
from flask import request, jsonify
from functools import wraps
import redis

redis_client = redis.Redis.from_url(Config.REDIS_URL)

def rate_limit(max_requests: int, window: int):
    """
    限流裝飾器
    
    Args:
        max_requests: 時間窗口內最大請求數
        window: 時間窗口（秒）
    """
    def decorator(f):
        @wraps(f)
        def wrapped(user_id, *args, **kwargs):
            key = f"rate_limit:{f.__name__}:{user_id}"
            current = redis_client.incr(key)
            
            if current == 1:
                redis_client.expire(key, window)
            
            if current > max_requests:
                return jsonify({
                    'error': f'請求過於頻繁，請在 {window} 秒後再試'
                }), 429
            
            return f(user_id, *args, **kwargs)
        return wrapped
    return decorator

# 使用範例
@app.route('/api/tasks/upload', methods=['POST'])
@login_required
@rate_limit(max_requests=5, window=3600)  # 每小時最多 5 次
def upload_video(user_id):
    pass
```

---

## 九、安全性設計

### 9.1 密碼加密

```python
# app/utils/security.py
from werkzeug.security import generate_password_hash, check_password_hash

class Security:
    @staticmethod
    def hash_password(password: str) -> str:
        """使用 bcrypt 加密密碼"""
        return generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """驗證密碼"""
        return check_password_hash(password_hash, password)
```

### 9.2 驗證碼系統

```python
# app/services/captcha_service.py
from captcha.image import ImageCaptcha
import random
import string
from datetime import datetime, timedelta

class CaptchaService:
    @staticmethod
    def generate_captcha(session_id: str) -> tuple[str, bytes]:
        """
        生成驗證碼
        
        Returns:
            (驗證碼文字, 圖片二進位資料)
        """
        # 生成 6 位數字驗證碼
        captcha_text = ''.join(random.choices(string.digits, k=6))
        
        # 生成圖片
        image = ImageCaptcha(width=200, height=80)
        image_data = image.generate(captcha_text)
        
        # 儲存到資料庫
        from app.models.captcha import CaptchaRecord
        captcha = CaptchaRecord(
            session_id=session_id,
            captcha_text=captcha_text,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.session.add(captcha)
        db.session.commit()
        
        return captcha_text, image_data.getvalue()
    
    @staticmethod
    def verify_captcha(session_id: str, user_input: str) -> bool:
        """驗證驗證碼"""
        from app.models.captcha import CaptchaRecord
        
        captcha = CaptchaRecord.query.filter_by(
            session_id=session_id,
            is_used=False
        ).first()
        
        if not captcha:
            return False
        
        # 檢查是否過期
        if datetime.utcnow() > captcha.expires_at:
            return False
        
        # 驗證碼比對
        is_valid = captcha.captcha_text == user_input
        
        # 標記為已使用
        captcha.is_used = True
        db.session.commit()
        
        return is_valid
```

### 9.3 檔案上傳安全

```python
# app/services/storage_service.py
import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

class StorageService:
    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """檢查檔案格式"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_upload_file(file, user_id: int) -> str:
        """
        安全儲存上傳的檔案
        
        Returns:
            檔案路徑
        """
        if not file or not StorageService.is_allowed_file(file.filename):
            raise ValueError("不支援的檔案格式")
        
        # 生成安全的檔名
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # 建立使用者專屬目錄
        user_dir = os.path.join(Config.UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # 儲存檔案
        file_path = os.path.join(user_dir, unique_filename)
        file.save(file_path)
        
        # 驗證檔案大小
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise ValueError("檔案大小超過限制")
        
        return file_path
```

### 9.4 CORS 配置

```python
# app/__init__.py
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    # CORS 配置
    CORS(app, resources={
        r"/api/*": {
            "origins": Config.FRONTEND_URL,
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    return app
```

---

## 十、部署架構

### 10.1 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 資料庫
  postgres:
    image: postgres:15-alpine
    container_name: dvt_postgres
    environment:
      POSTGRES_DB: deep_video_translation
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7-alpine
    container_name: dvt_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  # Flask 後端 API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dvt_backend
    environment:
      - FLASK_APP=app
      - FLASK_ENV=${FLASK_ENV:-production}
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/deep_video_translation
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
      - outputs:/app/outputs
      - models:/app/models
    ports:
      - "5000:5000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # Celery Worker（影片處理）
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dvt_celery_worker
    command: celery -A celery_worker.celery worker --loglevel=info --queue=video_queue --concurrency=1
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/deep_video_translation
      - REDIS_URL=redis://redis:6379/0
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
      - outputs:/app/outputs
      - models:/app/models
    depends_on:
      - redis
      - postgres
      - backend
    restart: unless-stopped

  # Celery Worker（郵件發送）
  celery_email:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dvt_celery_email
    command: celery -A celery_worker.celery worker --loglevel=info --queue=email_queue --concurrency=2
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/deep_video_translation
      - REDIS_URL=redis://redis:6379/0
      - MAIL_SERVER=${MAIL_SERVER}
      - MAIL_USERNAME=${MAIL_USERNAME}
      - MAIL_PASSWORD=${MAIL_PASSWORD}
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - postgres
      - backend
    restart: unless-stopped

  # React 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_URL=${VITE_API_URL}
    container_name: dvt_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: dvt_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - outputs:/usr/share/nginx/outputs:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  uploads:
  outputs:
  models:
```

### 10.2 Nginx 配置

```nginx
# nginx/nginx.conf
upstream backend {
    server backend:5000;
}

upstream frontend {
    server frontend:80;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # 強制跳轉 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL 憑證
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL 安全設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # 最大上傳大小
    client_max_body_size 500M;
    
    # 前端
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 後端 API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' 'https://yourdomain.com' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        
        # Preflight requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # WebSocket
    location /socket.io/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 檔案下載（直接由 Nginx 提供）
    location /downloads/ {
        alias /usr/share/nginx/outputs/;
        internal;
        add_header Content-Disposition 'attachment';
    }
}
```

### 10.3 環境變數範例

```bash
# .env
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# 資料庫
DB_USER=dvt_user
DB_PASSWORD=your-secure-password
DATABASE_URL=postgresql://dvt_user:your-secure-password@postgres:5432/deep_video_translation

# Redis
REDIS_URL=redis://redis:6379/0

# API Keys
GEMINI_API_KEY=your-gemini-api-key

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# 前端
VITE_API_URL=https://yourdomain.com/api

# 其他
FRONTEND_URL=https://yourdomain.com
MAX_FILE_SIZE_MB=500
FILE_RETENTION_DAYS=30
```

---

## 十一、開發階段規劃

### 階段一：基礎架構搭建（預計 1 週）
**目標：建立基本的使用者認證系統與資料庫**

- [ ] 1.1 設置 PostgreSQL 資料庫
- [ ] 1.2 建立 SQLAlchemy 模型（User, Task, Log）
- [ ] 1.3 實作使用者註冊 API
- [ ] 1.4 實作使用者登入 API（JWT）
- [ ] 1.5 實作驗證碼系統
- [ ] 1.6 資料庫遷移腳本（Alembic）
- [ ] 1.7 基本的錯誤處理與日誌

**交付物：**
- 可運行的後端 API
- 使用者可以註冊、登入
- PostgreSQL 資料庫正常運作

---

### 階段二：前端開發（預計 2 週）
**目標：React 前端應用，包含所有主要頁面**

- [ ] 2.1 React + TypeScript + Vite 專案初始化
- [ ] 2.2 實作 Landing Page（產品介紹）
  - 保留現有設計風格
  - 添加深色/淺色模式切換
- [ ] 2.3 實作認證頁面（登入/註冊）
  - 表單驗證
  - 驗證碼整合
- [ ] 2.4 實作上傳頁面
  - 拖拽上傳
  - 進度顯示
  - 語言選擇
- [ ] 2.5 實作任務列表頁面
  - 任務卡片
  - 狀態顯示
  - 日誌查看
- [ ] 2.6 實作下載頁面
- [ ] 2.7 響應式設計（桌面/平板/手機）
- [ ] 2.8 深色/淺色主題切換

**交付物：**
- 完整的前端應用
- UI/UX 符合設計規範
- 與後端 API 整合完成

---

### 階段三：任務處理系統（預計 2 週）
**目標：整合現有影片處理邏輯與佇列系統**

- [ ] 3.1 設置 Redis
- [ ] 3.2 設置 Celery Worker
- [ ] 3.3 重構現有 VideoProcessor
  - 添加進度回調
  - 錯誤處理優化
  - 日誌記錄
- [ ] 3.4 實作任務佇列邏輯
  - 任務建立
  - 佇列管理
  - 任務狀態更新
- [ ] 3.5 實作 WebSocket 即時推送
  - 任務進度
  - 日誌推送
- [ ] 3.6 檔案儲存系統
  - 上傳檔案管理
  - 輸出檔案管理
  - 自動清理過期檔案

**交付物：**
- 背景任務系統正常運作
- 使用者可以上傳影片並排隊處理
- 即時進度更新

---

### 階段四：Email 通知系統（預計 3 天）
**目標：完成自動郵件通知**

- [ ] 4.1 設置 Flask-Mail
- [ ] 4.2 設計郵件模板
  - 歡迎信
  - Email 驗證
  - 任務完成通知
- [ ] 4.3 實作郵件發送任務（Celery）
- [ ] 4.4 測試郵件發送功能

**交付物：**
- 使用者註冊後收到驗證信
- 任務完成後收到通知

---

### 階段五：安全性與優化（預計 1 週）
**目標：提升系統安全性與性能**

- [ ] 5.1 限流機制（Rate Limiting）
- [ ] 5.2 使用配額系統
- [ ] 5.3 檔案上傳安全檢查
- [ ] 5.4 SQL Injection 防護
- [ ] 5.5 XSS 防護
- [ ] 5.6 CSRF 防護
- [ ] 5.7 API 文檔（Swagger）
- [ ] 5.8 效能測試與優化

**交付物：**
- 安全的生產環境
- 完整的 API 文檔

---

### 階段六：Docker 部署（預計 3 天）
**目標：容器化部署方案**

- [ ] 6.1 編寫 Dockerfile（前端、後端）
- [ ] 6.2 編寫 docker-compose.yml
- [ ] 6.3 Nginx 反向代理配置
- [ ] 6.4 SSL 憑證設置
- [ ] 6.5 部署文檔
- [ ] 6.6 一鍵部署腳本

**交付物：**
- 完整的 Docker 部署方案
- 部署文檔

---

### 階段七：測試與上線（預計 1 週）
**目標：全面測試，準備上線**

- [ ] 7.1 單元測試
- [ ] 7.2 整合測試
- [ ] 7.3 E2E 測試
- [ ] 7.4 負載測試
- [ ] 7.5 安全測試
- [ ] 7.6 使用者測試（Beta）
- [ ] 7.7 修復 Bug
- [ ] 7.8 正式上線

**交付物：**
- 穩定的生產環境
- 測試報告
- 使用者手冊

---

## 總結

### 核心技術決策

| 項目 | 選擇 | 理由 |
|-----|------|------|
| **後端框架** | Python Flask | 兼容現有代碼，AI 生態完整 |
| **前端框架** | React + TypeScript | 現代化、生態完整、易維護 |
| **資料庫** | PostgreSQL | 成熟穩定、功能強大 |
| **任務佇列** | Celery + Redis | Python 生態最佳選擇 |
| **認證方式** | JWT | 無狀態、易擴展 |
| **郵件服務** | Flask-Mail + SMTP | 簡單易用、成本低 |
| **部署方式** | Docker Compose | 一鍵部署、隔離環境 |

### 開發時間估計

- **總開發時間：約 6-7 週**
- **團隊建議：1-2 名全端工程師**
- **前端開發：2-3 週**
- **後端開發：2-3 週**
- **整合測試：1 週**

### 後續擴展方向

1. **進階功能**
   - 批次處理（一次上傳多個影片）
   - 自訂語音模型（使用者上傳參考音檔）
   - 翻譯預覽（處理前預覽轉錄文字）
   - 字幕檔輸出（SRT, ASS 格式）

2. **商業化**
   - 付費方案（更高配額）
   - API 金鑰系統（讓其他應用整合）
   - 企業版（私有部署）

3. **技術優化**
   - GPU 加速（NVIDIA Docker）
   - CDN 整合（加速檔案下載）
   - 監控告警（Prometheus + Grafana）
   - 日誌分析（ELK Stack）

---

## 下一步行動

**請確認以下事項：**

1. ✅ 技術棧選擇（Flask + React）是否認可？
2. ✅ 資料庫設計（User, Task, Log, Captcha）是否符合需求？
3. ✅ 開發階段規劃是否合理？
4. ✅ UI 設計方向（科技感、深淺色主題）是否認可？
5. ✅ 任務佇列方案（Celery + Redis）是否認可？

**確認後，我將開始：**
1. 建立專案目錄結構
2. 初始化 Git 分支
3. 開始階段一開發（基礎架構搭建）

---

**文件版本：1.0**  
**最後更新：2026年2月23日**  
**作者：GitHub Copilot**
