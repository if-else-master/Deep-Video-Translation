"""
Email 發送服務
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

class EmailService:
    """處理 Email 發送"""
    
    def __init__(self):
        """初始化 Email 服務"""
        # 從環境變數讀取 SMTP 配置
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'Deep Video Translation')
        
    def send_completion_email(self, to_email, video_filename, output_path=None, download_url=None):
        """
        發送處理完成通知郵件
        
        Args:
            to_email: 收件人 email
            video_filename: 原始影片檔名
            output_path: 輸出檔案路徑（可選，用於附件）
            download_url: 下載連結（可選）
        """
        try:
            # 創建郵件
            msg = MIMEMultipart('alternative')
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = to_email
            msg['Subject'] = f'✅ 影片翻譯完成 - {video_filename}'
            
            # HTML 郵件內容（黑白灰風格）
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif;
                        background-color: #000000;
                        color: #e0e0e0;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 8px;
                        overflow: hidden;
                    }}
                    .header {{
                        background-color: #2d2d2d;
                        padding: 30px;
                        text-align: center;
                        border-bottom: 1px solid #404040;
                    }}
                    .header h1 {{
                        color: #ffffff;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 700;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    .success-icon {{
                        font-size: 48px;
                        text-align: center;
                        margin-bottom: 20px;
                    }}
                    .message {{
                        color: #c4c4c4;
                        line-height: 1.6;
                        margin-bottom: 20px;
                    }}
                    .info-box {{
                        background-color: #2d2d2d;
                        border: 1px solid #404040;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .info-box strong {{
                        color: #ffffff;
                        display: block;
                        margin-bottom: 10px;
                    }}
                    .filename {{
                        color: #a3a3a3;
                        font-family: monospace;
                        padding: 10px;
                        background-color: #0f0f0f;
                        border-radius: 4px;
                        border: 1px solid #404040;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #ffffff;
                        color: #000000;
                        padding: 15px 30px;
                        text-decoration: none;
                        border-radius: 6px;
                        font-weight: 600;
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .footer {{
                        background-color: #0f0f0f;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #404040;
                        font-size: 12px;
                        color: #6b6b6b;
                    }}
                    .note {{
                        background-color: #2d2d2d;
                        border-left: 3px solid #ffffff;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 4px;
                    }}
                    .note strong {{
                        color: #ffffff;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Deep Video Translation</h1>
                    </div>
                    <div class="content">
                        <div class="success-icon">✅</div>
                        <div class="message">
                            <p>您好！</p>
                            <p>您的影片已經成功完成翻譯處理。</p>
                        </div>
                        
                        <div class="info-box">
                            <strong>📁 原始檔名：</strong>
                            <div class="filename">{video_filename}</div>
                        </div>
            """
            
            # 如果有下載連結
            if download_url:
                html_body += f"""
                        <div style="text-align: center;">
                            <a href="{download_url}" class="button">立即下載翻譯後的影片</a>
                        </div>
                """
            
            # 如果有附件檔案路徑
            if output_path and os.path.exists(output_path):
                html_body += """
                        <div class="note">
                            <strong>💡 提示：</strong>
                            翻譯後的影片已作為附件隨信發送。
                        </div>
                """
            
            html_body += """
                        <div style="background-color:#1a1a1a; border:2px solid #ffffff; border-radius:8px; padding:28px; margin:28px 0; text-align:center;">
                            <div style="font-size:32px; margin-bottom:12px;">📝</div>
                            <h2 style="color:#ffffff; margin:0 0 10px 0; font-size:18px; font-weight:700;">使用體驗回饋</h2>
                            <p style="color:#a3a3a3; margin:0 0 22px 0; line-height:1.6; font-size:14px;">
                                您的反饋對我們非常重要！<br>
                                請花 1 分鐘填寫使用體驗問卷，幫助我們持續改善服務品質。
                            </p>
                            <a href="https://docs.google.com/forms/d/e/1FAIpQLScHhcZU-Leqyf218TaRRw-xhIotjMNAmB1_3Wqw1IT5exMVEA/viewform?usp=header"
                               style="display:inline-block; background-color:#ffffff; color:#000000; padding:14px 32px; text-decoration:none; border-radius:6px; font-weight:700; font-size:15px; letter-spacing:0.3px;">
                                填寫使用體驗問卷 →
                            </a>
                        </div>

                        <div class="message">
                            <p><strong>注意事項：</strong></p>
                            <ul style="color: #a3a3a3; line-height: 1.8;">
                                <li>此 Email 地址 5 小時內無法再次使用服務</li>
                                <li>如有任何問題，請聯繫技術支援</li>
                            </ul>
                        </div>
                    </div>
                    <div class="footer">
                        <p>&copy; 2026 Deep Video Translation. All rights reserved.</p>
                        <p>這是一封自動發送的郵件，請勿直接回覆。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # 純文字版本（備用）
            text_body = f"""
Deep Video Translation - 影片翻譯完成通知

✅ 您的影片已經成功完成翻譯處理！

原始檔名：{video_filename}

{'下載連結：' + download_url if download_url else ''}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 使用體驗回饋
請花 1 分鐘填寫問卷，幫助我們持續改善服務：
https://docs.google.com/forms/d/e/1FAIpQLScHhcZU-Leqyf218TaRRw-xhIotjMNAmB1_3Wqw1IT5exMVEA/viewform?usp=header
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

注意事項：
- 此 Email 地址 5 小時內無法再次使用服務
- 如有任何問題，請聯繫技術支援

© 2026 Deep Video Translation. All rights reserved.
這是一封自動發送的郵件，請勿直接回覆。
            """
            
            # 附加郵件內容
            part_text = MIMEText(text_body, 'plain', 'utf-8')
            part_html = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part_text)
            msg.attach(part_html)
            
            # 如果有輸出檔案且檔案存在，添加為附件（小於 25MB）
            if output_path and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                # Gmail 限制 25MB，保守一點設 20MB
                if file_size < 20 * 1024 * 1024:  
                    with open(output_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = os.path.basename(output_path)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
            
            # 發送郵件
            if not self.smtp_user or not self.smtp_password:
                print("⚠️  警告：未配置 SMTP 設定，無法發送郵件")
                print(f"   預計發送給：{to_email}")
                print(f"   主題：{msg['Subject']}")
                return False, "SMTP 未配置"
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True, "郵件發送成功"
            
        except Exception as e:
            error_msg = f"發送郵件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def send_error_email(self, to_email, video_filename, error_message):
        """發送處理失敗通知郵件"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = to_email
            msg['Subject'] = f'❌ 影片翻譯失敗 - {video_filename}'
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', 'Microsoft JhengHei', -apple-system, BlinkMacSystemFont, sans-serif;
                        background-color: #000000;
                        color: #e0e0e0;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 8px;
                    }}
                    .header {{
                        background-color: #2d2d2d;
                        padding: 30px;
                        text-align: center;
                        border-bottom: 1px solid #404040;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    .error-icon {{
                        font-size: 48px;
                        text-align: center;
                        margin-bottom: 20px;
                    }}
                    .error-box {{
                        background-color: #2d2d2d;
                        border: 1px solid #ff6b6b;
                        border-left: 3px solid #ff6b6b;
                        border-radius: 6px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        background-color: #0f0f0f;
                        padding: 20px;
                        text-align: center;
                        border-top: 1px solid #404040;
                        font-size: 12px;
                        color: #6b6b6b;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="color: #ffffff; margin: 0;">Deep Video Translation</h1>
                    </div>
                    <div class="content">
                        <div class="error-icon">❌</div>
                        <p style="color: #c4c4c4;">很抱歉，您的影片處理過程中發生錯誤。</p>
                        
                        <div class="error-box">
                            <strong style="color: #ffffff;">錯誤訊息：</strong>
                            <p style="color: #ff6b6b; margin-top: 10px;">{error_message}</p>
                        </div>
                        
                        <p style="color: #a3a3a3;">
                            原始檔名：<code style="background: #0f0f0f; padding: 5px; border-radius: 3px;">{video_filename}</code>
                        </p>
                        
                        <p style="color: #a3a3a3;">請檢查影片格式和內容後，再次嘗試上傳。</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2026 Deep Video Translation. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
Deep Video Translation - 影片翻譯失敗通知

❌ 很抱歉，您的影片處理過程中發生錯誤。

原始檔名：{video_filename}
錯誤訊息：{error_message}

請檢查影片格式和內容後，再次嘗試上傳。

© 2026 Deep Video Translation. All rights reserved.
            """
            
            part_text = MIMEText(text_body, 'plain', 'utf-8')
            part_html = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part_text)
            msg.attach(part_html)
            
            if not self.smtp_user or not self.smtp_password:
                print("⚠️  警告：未配置 SMTP 設定，無法發送郵件")
                return False, "SMTP 未配置"
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True, "錯誤通知郵件發送成功"
            
        except Exception as e:
            error_msg = f"發送錯誤通知郵件失敗: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
