"""
SMTP 郵件發送測試腳本
使用方法：python test_smtp.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 載入環境變數
load_dotenv()

def test_smtp_connection():
    """測試 SMTP 連線和發送郵件"""
    
    print("=" * 60)
    print("🔍 SMTP 設定檢查")
    print("=" * 60)
    
    # 讀取 SMTP 設定（與 email_service.py 保持一致）
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    from_email = os.getenv('FROM_EMAIL', smtp_user)
    from_name = os.getenv('FROM_NAME', 'Deep Video Translation')
    
    # 檢查必要設定
    if not all([smtp_server, smtp_user, smtp_password]):
        print("❌ 錯誤：缺少必要的 SMTP 設定")
        print("\n請按照以下步驟設定：")
        print("\n1️⃣  複製範例配置文件：")
        print("   cp .env.example .env")
        print("\n2️⃣  編輯 .env 文件，填入您的設定：")
        print("SMTP_SERVER=smtp.gmail.com")
        print("SMTP_PORT=587")
        print("SMTP_USER=your_email@gmail.com")
        print("SMTP_PASSWORD=your_app_password")
        print("FROM_EMAIL=your_email@gmail.com")
        print("FROM_NAME=Deep Video Translation")
        print("\n💡 Gmail 應用程式密碼取得：https://myaccount.google.com/apppasswords")
        return False
    
    print(f"✅ SMTP 伺服器: {smtp_server}")
    print(f"✅ SMTP 埠號: {smtp_port}")
    print(f"✅ 使用者帳號: {smtp_user}")
    print(f"✅ 寄件人 Email: {from_email}")
    print(f"✅ 寄件人名稱: {from_name}")
    print(f"✅ 密碼: {'*' * len(smtp_password)}")
    
    # 詢問收件人
    print("\n" + "=" * 60)
    recipient = input("📧 請輸入測試收件人 Email（按 Enter 使用 rayc57429@gmail.com）: ").strip()
    if not recipient:
        recipient = "rayc57429@gmail.com"
    
    print(f"\n📤 準備發送測試郵件到: {recipient}")
    print("=" * 60)
    
    try:
        # 建立郵件內容
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🧪 SMTP 測試郵件 - Deep Video Translation'
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = recipient
        
        # 取得當前時間
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # HTML 郵件內容（黑白灰科技風格）
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background-color: #000000;
            color: #ffffff;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
            border: 1px solid #333;
            border-radius: 12px;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
            padding: 30px;
            text-align: center;
            border-bottom: 2px solid #444;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .success-icon {{
            text-align: center;
            font-size: 64px;
            margin-bottom: 20px;
        }}
        .message {{
            font-size: 16px;
            line-height: 1.8;
            color: #cccccc;
            margin-bottom: 20px;
        }}
        .info-box {{
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #2a2a2a;
        }}
        .info-item:last-child {{
            border-bottom: none;
        }}
        .info-label {{
            color: #888888;
            font-weight: 500;
        }}
        .info-value {{
            color: #ffffff;
            font-weight: 600;
        }}
        .highlight {{
            background-color: #2a2a2a;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #ffffff;
            margin: 15px 0;
        }}
        .footer {{
            background-color: #0f0f0f;
            padding: 20px 30px;
            text-align: center;
            border-top: 1px solid #2a2a2a;
            color: #666666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 SMTP 測試成功</h1>
        </div>
        <div class="content">
            <div class="success-icon">✅</div>
            <div class="message">
                <p><strong>恭喜！您的 SMTP 郵件服務已成功配置。</strong></p>
                <p>這是一封測試郵件，用於驗證 Deep Video Translation 系統的郵件發送功能是否正常運作。</p>
            </div>
            <div class="info-box">
                <div class="info-item">
                    <span class="info-label">📧 SMTP 伺服器</span>
                    <span class="info-value">{smtp_server}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🔌 連接埠</span>
                    <span class="info-value">{smtp_port}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">👤 寄件人</span>
                    <span class="info-value">{from_email}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📛 寄件人名稱</span>
                    <span class="info-value">{from_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">⏰ 測試時間</span>
                    <span class="info-value">{current_time}</span>
                </div>
            </div>
            <div class="highlight">
                <p style="margin: 0; color: #ffffff;"><strong>✨ 系統已就緒</strong></p>
                <p style="margin: 10px 0 0 0; color: #cccccc;">當使用者的影片翻譯完成後，系統將自動發送通知郵件到使用者指定的 Email 地址。</p>
            </div>
            <div class="message" style="margin-top: 30px;">
                <p><strong>🎯 功能說明</strong></p>
                <ul style="line-height: 1.8; color: #aaaaaa;">
                    <li>自動發送處理完成通知</li>
                    <li>提供影片下載連結</li>
                    <li>5 天冷卻期機制</li>
                    <li>1 分鐘影片時長限制</li>
                </ul>
            </div>
        </div>
        <div class="footer">
            <p>© 2026 Deep Video Translation | Powered by AI</p>
            <p style="margin-top: 10px; font-size: 12px;">此郵件由系統自動發送，請勿直接回覆</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 純文字版本（作為備用）
        text_content = f"""
SMTP 測試郵件 - Deep Video Translation

✅ 測試成功！

您的 SMTP 郵件服務已成功配置。

=== 配置資訊 ===
SMTP 伺服器: {smtp_server}
連接埠: {smtp_port}
寄件人: {from_email}
寄件人名稱: {from_name}
測試時間: {current_time}

=== 系統功能 ===
• 自動發送處理完成通知
• 提供影片下載連結
• 5 天冷卻期機制
• 1 分鐘影片時長限制

系統已就緒，可以開始發送影片完成通知。

---
© 2026 Deep Video Translation
此郵件由系統自動發送，請勿直接回覆
        """
        
        # 附加純文字和 HTML 版本
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        # 連接 SMTP 伺服器並發送
        print("\n🔗 正在連接 SMTP 伺服器...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.ehlo()
        
        print("🔐 啟動 TLS 加密...")
        server.starttls()
        server.ehlo()
        
        print("🔑 正在驗證登入...")
        server.login(smtp_user, smtp_password)
        
        print("📨 正在發送郵件...")
        server.send_message(msg)
        server.quit()
        
        print("\n" + "=" * 60)
        print("✅ 測試成功！郵件已發送")
        print("=" * 60)
        print(f"\n請檢查 {recipient} 的收件匣（或垃圾郵件夾）")
        print("\n💡 提示：如果使用 Gmail，請確保：")
        print("   1. 已啟用「兩步驟驗證」")
        print("   2. 使用「應用程式密碼」而非帳戶密碼")
        print("   3. 應用程式密碼取得：https://myaccount.google.com/apppasswords")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "=" * 60)
        print("❌ 驗證失敗！")
        print("=" * 60)
        print(f"\n錯誤訊息: {str(e)}")
        print("\n可能的原因：")
        print("  • 帳號或密碼不正確")
        print("  • Gmail 需使用「應用程式密碼」(16位數)")
        print("  • 帳號未啟用「兩步驟驗證」")
        print("\n解決方法：")
        print("  1. 前往 https://myaccount.google.com/apppasswords")
        print("  2. 選擇「應用程式」→「郵件」")
        print("  3. 選擇「裝置」→「其他」")
        print("  4. 輸入名稱並產生密碼")
        print("  5. 將產生的 16 位密碼更新到 .env 的 SMTP_PASSWORD")
        return False
        
    except smtplib.SMTPConnectError as e:
        print("\n" + "=" * 60)
        print("❌ 無法連接到 SMTP 伺服器！")
        print("=" * 60)
        print(f"\n錯誤訊息: {str(e)}")
        print(f"\n請檢查：")
        print(f"  • SMTP_SERVER: {smtp_server}")
        print(f"  • SMTP_PORT: {smtp_port}")
        print(f"  • 網路連線是否正常")
        print(f"  • 防火牆是否阻擋了連線")
        return False
        
    except smtplib.SMTPException as e:
        print("\n" + "=" * 60)
        print("❌ SMTP 錯誤")
        print("=" * 60)
        print(f"\n錯誤訊息: {str(e)}")
        print(f"\n錯誤類型: {type(e).__name__}")
        return False
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 發生未預期的錯誤")
        print("=" * 60)
        print(f"\n錯誤訊息: {str(e)}")
        print(f"\n錯誤類型: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Deep Video Translation - SMTP 測試工具")
    print("=" * 60)
    print("\n此工具將測試您的 SMTP 郵件發送設定是否正確")
    print("測試郵件使用與系統相同的黑白灰科技風格設計\n")
    
    success = test_smtp_connection()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 SMTP 設定正確，系統可以正常發送郵件！")
        print("=" * 60)
        print("\n您現在可以啟動 Deep Video Translation 系統")
        print("當影片處理完成時，使用者會收到通知郵件\n")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ SMTP 測試失敗")
        print("=" * 60)
        print("\n請檢查 .env 文件中的設定，並重新測試\n")
        sys.exit(1)
