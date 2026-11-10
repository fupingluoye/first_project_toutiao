from celerys.celery_config import cel
from email.mime.text import MIMEText
import smtplib
from email.header import Header

from config import Config

SMTP_USER = Config.SMTP_USER
SMTP_PORT = Config.SMTP_PORT
SMTP_HOST = Config.SMTP_HOST
SMTP_PASS = Config.SMTP_PASS
@cel.task(bind = True,max_retries=3)
def send_email(self,to_email:str,code:int):
    msg = MIMEText(f"你的账号已注销，恢复登陆的验证码是{code},五分钟内有效","plain","utf-8")
    msg["Subject"] = Header("账号回复验证码","utf-8").encode()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    
    try:
        with smtplib.SMTP_SSL(SMTP_HOST,SMTP_PORT) as server:
            server.login(SMTP_USER,SMTP_PASS)
            server.send_message(msg)
            
    except smtplib.SMTPException as e:
        raise self.retry(exc=e,countdown=2)