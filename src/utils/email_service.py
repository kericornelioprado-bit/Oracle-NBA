import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from src.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

class NBAEmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_USER")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.receiver_email = os.getenv("GMAIL_USER") # Envío al mismo correo personal

    def send_email(self, subject, body, is_html=False):
        if not self.sender_email or not self.password:
            logger.error("Credenciales de Gmail no configuradas en variables de entorno.")
            return False

        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = self.receiver_email
        message["Subject"] = subject

        part = MIMEText(body, "html" if is_html else "plain")
        message.attach(part)

        try:
            logger.info(f"Enviando correo: {subject}...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, self.receiver_email, message.as_string())
            logger.info("Correo enviado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al enviar correo: {e}")
            return False

    def send_prediction_report(self, report_html):
        subject = "🏀 Oráculo NBA: Predicciones del Día"
        return self.send_email(subject, report_html, is_html=True)

    def send_error_alert(self, error_traceback):
        subject = "⚠️ ALERT: Fallo Crítico Oráculo NBA"
        body = f"Se ha detectado un error en la ejecución diaria:\n\n{error_traceback}"
        return self.send_email(subject, body, is_html=False)
