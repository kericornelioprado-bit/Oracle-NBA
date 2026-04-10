import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from src.shared.logger import logger
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    """
    Servicio genérico de notificaciones vía SMTP (Gmail).
    Soporta personalización por deporte para reportes y alertas.
    """
    def __init__(self, sport='nba'):
        self.sport = sport.lower()
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("GMAIL_USER")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.receiver_email = os.getenv("GMAIL_USER")
        
        # Configuración visual por deporte
        self.sport_metadata = {
            'nba': {'emoji': '🏀', 'name': 'Oráculo NBA'},
            'mlb': {'emoji': '⚾', 'name': 'Diamante MLB'}
        }
        self.meta = self.sport_metadata.get(self.sport, {'emoji': '🎯', 'name': f'Oracle {self.sport.upper()}'})

    def send_email(self, subject, body, is_html=False):
        if not self.sender_email or not self.password:
            logger.error("Credenciales de Gmail no configuradas. Saltando envío de correo.")
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
            logger.info(f"✅ Correo '{subject}' enviado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al enviar correo: {e}")
            return False

    def send_prediction_report(self, report_html):
        """Envía el reporte diario de predicciones."""
        subject = f"{self.meta['emoji']} {self.meta['name']}: Predicciones del Día"
        return self.send_email(subject, report_html, is_html=True)

    def send_error_alert(self, error_traceback):
        """Envía una alerta de error crítico."""
        subject = f"⚠️ ALERT: Fallo Crítico {self.meta['name']}"
        body = f"Se ha detectado un error en la ejecución diaria del módulo {self.sport.upper()}:\n\n{error_traceback}"
        return self.send_email(subject, body, is_html=False)
