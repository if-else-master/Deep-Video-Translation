# 🎬 Deep Video Translation Platform

<div align="center">

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000.svg)](https://flask.palletsprojects.com/)

**AI 驅動的全自動智能影片深度翻譯平台**

跨語言影片內容翻譯 • 語音克隆 • 唇形同步 • PPT 翻譯 • Web 平台

[功能特色](#-功能特色) • [快速開始](#-快速開始) • [演示視頻](#-演示視頻) • [技術棧](#-技術棧) • [文檔](#-文檔)

</div>

---

## 📖 項目簡介

Deep Video Translation 是一個全自動的智能影片深度翻譯平台，結合最先進的 AI 技術實現：

🎙️ **語音識別** - Gemini API 高精度語音轉文字  
🌏 **智能翻譯** - AI 驅動的多語言翻譯  
🗣️ **語音克隆** - XTTS-v2 & F5-TTS 雙引擎 TTS  
👄 **唇形同步** - Wav2Lip 技術精準口型匹配  
📊 **PPT 翻譯** - OCR 識別並翻譯投影片文字  
🧠 **智能分段** - 自動區分人臉與簡報片段  
🌐 **Web 平台** - React + Flask 全棧應用

---

## ✨ 功能特色

### 🎯 核心功能

#### 用戶系統
- ✅ **用戶註冊/登入** - JWT 認證，安全可靠
- ✅ **驗證碼保護** - 6 位數字驗證碼防機器人
- ✅ **Email 驗證** - 郵件驗證機制
- ✅ **配額管理** - 每月免費 10 次翻譯（可配置）

#### 視頻處理
- ✅ **多格式支持** - MP4, MOV, AVI, MKV, WEBM
- ✅ **智能限制** - 最大 500MB，最長 3 分鐘
- ✅ **多語言支持** - 中文、英語、日語
- ✅ **雙 TTS 引擎** - XTTS-v2（快速）/ F5-TTS（高質量）
- ✅ **可選功能** - 唇形同步、PPT 翻譯自由選擇

#### 任務管理
- ✅ **異步處理** - Celery + Redis 任務隊列
- ✅ **實時更新** - WebSocket 推送進度
- ✅ **狀態追蹤** - PENDING → QUEUED → PROCESSING → COMPLETED
- ✅ **詳細日誌** - 每個處理步驟完整記錄
- ✅ **郵件通知** - 任務完成自動發送郵件
- ✅ **安全下載** - Token 驗證，30 天自動過期

#### 前端體驗
- ✅ **現代化 UI** - Tailwind CSS 精美設計
- ✅ **暗色模式** - 深淺主題無縫切換
- ✅ **響應式** - 支持所有設備屏幕
- ✅ **拖拽上傳** - 直觀的文件上傳體驗
- ✅ **即時反饋** - Toast 通知 + 進度條

### 🧠 智能分段處理（核心技術）

系統的核心創新在於**智能分段處理**，能夠自動分析視頻內容：

- 🔍 **場景檢測** - ImageHash 感知哈希檢測場景變化
- 👤 **人臉識別** - Haar Cascade 檢測人臉講話片段
- 📄 **簡報判斷** - Canny 邊緣檢測分析簡報頁面
- ⚡ **分別處理** - 人臉片段唇形同步，簡報片段 OCR 翻譯
- 🎬 **智能合併** - 多重策略解決解析度不一致問題

---

## 🎥 演示視頻

### 唇形同步效果

https://github.com/user-attachments/assets/5c8b0f10-e5e0-422a-8a3b-b469bdfabc0f

### 唇形同步 + 簡報 OCR 翻譯

https://github.com/user-attachments/assets/f74c6488-1ddc-4ac2-827b-0238bae53e1d

---

## 🚀 快速開始

### 前置需求

- **Python** 3.10+
- **Node.js** 18+
- **PostgreSQL** 15+
- **Redis** 7.0+
- **FFmpeg** (必須安裝)
- **CUDA** (可選，GPU 加速)

### 安裝步驟

#### 1️⃣ 克隆倉庫

```bash
git clone https://github.com/if-else-master/Deep-Video-Translation.git
cd Deep-Video-Translation
```

#### 2️⃣ Backend 設置

```bash
cd backend

# 創建虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境變量
cp .env.example .env
# 編輯 .env，配置：
# - DATABASE_URL (PostgreSQL 連接)
# - REDIS_URL (Redis 連接)
# - GEMINI_API_KEY (Gemini API 密鑰)
# - JWT_SECRET_KEY (JWT 密鑰)
# - MAIL_* (郵件服務配置)

# 初始化數據庫
flask init-db
```

#### 3️⃣ Frontend 設置

```bash
cd frontend

# 安裝依賴
npm install

# 配置 API 地址（如需要）
# 編輯 src/services/api.ts 修改 baseURL
```

#### 4️⃣ 啟動服務

**Terminal 1 - Backend API**
```bash
cd backend
source venv/bin/activate
python run.py
# 運行在 http://localhost:5000
```

**Terminal 2 - Celery Worker**
```bash
cd backend
source venv/bin/activate
celery -A celery_worker.celery worker --loglevel=info
```

**Terminal 3 - Frontend**
```bash
cd frontend
npm run dev
# 運行在 http://localhost:3000
```

#### 5️⃣ 訪問應用

打開瀏覽器訪問 **http://localhost:3000**

1. 註冊新賬號（填寫驗證碼）
2. 登入系統
3. 上傳視頻文件
4. 選擇翻譯選項
5. 監控處理進度
6. 下載完成的視頻

---

## 🛠️ 技術棧

### 前端技術

| 技術 | 版本 | 用途 |
|------|------|------|
| **React** | 18.0+ | UI 框架 |
| **TypeScript** | 5.0+ | 類型安全 |
| **Vite** | 5.0+ | 構建工具 |
| **Tailwind CSS** | 3.4+ | 樣式框架 |
| **Zustand** | 4.5+ | 狀態管理 |
| **Axios** | 1.6+ | HTTP 客戶端 |
| **Socket.io** | 4.6+ | WebSocket |
| **React Router** | 6.20+ | 路由管理 |

### 後端技術

| 技術 | 版本 | 用途 |
|------|------|------|
| **Flask** | 3.0+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM |
| **PostgreSQL** | 15+ | 數據庫 |
| **Redis** | 7.0+ | 緩存/隊列 |
| **Celery** | 5.3+ | 任務隊列 |
| **Flask-JWT-Extended** | 4.6+ | JWT 認證 |
| **Flask-SocketIO** | 5.3+ | WebSocket |
| **Flask-Mail** | 0.9+ | 郵件服務 |

### AI 核心組件

| 組件 | 功能 | 官方鏈接 |
|------|------|----------|
| **Gemini API** | 語音識別與文字翻譯 | [Google Gemini](https://ai.google.dev/) |
| **XTTS-v2** | 快速語音合成 | [Coqui TTS](https://github.com/coqui-ai/TTS) |
| **F5-TTS** | 高質量語音克隆 | [F5-TTS](https://github.com/SWivid/F5-TTS) |
| **Wav2Lip** | 唇形同步技術 | [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) |
| **EasyOCR** | 光學字符識別 | [EasyOCR](https://github.com/JaidedAI/EasyOCR) |
| **OpenCV** | 計算機視覺處理 | [OpenCV](https://opencv.org/) |
| **PyTorch** | 深度學習框架 | [PyTorch](https://pytorch.org/) |
| **FFmpeg** | 音視頻處理 | [FFmpeg](https://ffmpeg.org/) |

---

## 📁 項目結構

```
Deep-Video-Translation/
├── backend/                    # Flask 後端
│   ├── app/
│   │   ├── api/               # REST API 端點
│   │   ├── core/              # 視頻處理核心
│   │   ├── models/            # 數據庫模型
│   │   ├── services/          # 業務邏輯層
│   │   ├── tasks/             # Celery 異步任務
│   │   └── middleware/        # 中間件
│   ├── config.py              # 配置文件
│   ├── run.py                 # 應用入口
│   └── requirements.txt       # Python 依賴
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # React 組件
│   │   ├── pages/             # 頁面組件
│   │   ├── services/          # API 服務
│   │   ├── stores/            # Zustand 狀態
│   │   ├── hooks/             # 自定義 Hooks
│   │   └── types/             # TypeScript 類型
│   ├── package.json
│   └── vite.config.ts
│
├── app/                        # 原有 AI 處理代碼
│   ├── F5-TTS/                 # F5-TTS 模型
│   ├── Wav2Lip/               # Wav2Lip 模型
│   └── XTTS-v2/               # XTTS-v2 模型
│
├── PHASE1_CHECKLIST.md        # 階段一完成清單
├── DEVELOPMENT.md             # 完整開發文檔
└── README.md                  # 項目說明（本文件）
```

---

## 📚 文檔

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 完整開發文檔（架構設計、API、部署指南）
- **[PHASE1_CHECKLIST.md](PHASE1_CHECKLIST.md)** - 階段一完成檢查清單

---

## 🎯 使用流程

### Web 平台使用

1. **註冊/登入**
   - 訪問 http://localhost:3000
   - 註冊新賬號並驗證郵箱
   - 使用賬號登入系統

2. **上傳視頻**
   - 點擊「上傳」頁面
   - 拖拽或選擇視頻文件
   - 選擇來源語言和目標語言
   - 選擇 TTS 引擎（XTTS-v2 / F5-TTS）
   - 可選：啟用唇形同步
   - 可選：啟用 PPT 翻譯

3. **監控處理**
   - 任務提交後自動跳轉到任務列表
   - 實時查看處理進度（WebSocket 更新）
   - 查看詳細日誌信息

4. **下載結果**
   - 任務完成後會收到郵件通知
   - 在任務列表點擊「下載」按鈕
   - 下載鏈接 30 天有效

### 原始命令行使用（保留）

```bash
python app/main.py
```

使用 tkinter GUI 進行操作。

---

## 🔬 核心技術原理

### 智能分段算法

系統使用多層檢測機制區分「人臉講話」和「簡報展示」：

1. **場景變化檢測** - ImageHash 感知哈希
2. **人臉檢測** - OpenCV Haar Cascade
3. **簡報判斷** - Canny 邊緣檢測分析邊緣密度

### 分別處理策略

- **人臉片段**：語音識別 → 翻譯 → TTS → Wav2Lip 唇形同步
- **簡報片段**：語音識別 → 翻譯 → TTS → OCR 文字翻譯

### 智能合併技術

解決不同處理方式導致的解析度不一致問題：

1. **Filter Complex** - FFmpeg 濾鏡鏈統一解析度
2. **預處理統一** - 先統一解析度再合併
3. **逐個合併** - 兩兩遞歸合併（最穩定）
4. **備用方案** - 直接複製（保證不失敗）

詳見 [DEVELOPMENT.md](DEVELOPMENT.md) 技術詳解章節。

---

## 🐛 已知問題與限制

### 當前限制
- ✅ 視頻最長 3 分鐘（可配置）
- ✅ 文件最大 500MB
- ✅ 每月默認 10 次配額
- ⚠️ Wav2Lip 輸出解析度為 640x360（由模型限制）

### 待改進項目
- [ ] 支持更長視頻處理
- [ ] 優化 OCR 翻譯準確率
- [ ] 添加進度預估功能
- [ ] 支持批量處理
- [ ] 支持更多語言

---

## 🚧 TODO List

- [ ] Docker 部署配置
- [ ] 添加 RAG (檢索增強生成)
- [ ] Speaker Diarization（說話人分離）
- [ ] 支持更多視頻格式
- [ ] API 文檔（Swagger）
- [ ] 單元測試覆蓋
- [ ] 性能監控系統

---

## 🤝 貢獻指南

歡迎貢獻！請遵循以下步驟：

1. Fork 本倉庫
2. 創建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 📄 授權條款

本項目採用 GPLv3 授權條款 - 詳見 [LICENSE](LICENSE) 文件

---

## 🙏 致謝

感謝以下開源項目：

- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) - 唇形同步技術
- [XTTS-v2](https://github.com/coqui-ai/TTS) - 語音克隆模型
- [F5-TTS](https://github.com/SWivid/F5-TTS) - 高質量 TTS
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR 文字識別
- [Google Gemini](https://ai.google.dev/) - 語音識別與翻譯 API

---

## 📞 聯繫方式

- **GitHub Issues**: [提交問題](https://github.com/if-else-master/Deep-Video-Translation/issues)
- **項目主頁**: https://github.com/if-else-master/Deep-Video-Translation

---

<div align="center">

**⭐ 如果這個項目對您有幫助，請給我們一顆星星！**

Made with ❤️ by the Deep Video Translation Team

</div>
