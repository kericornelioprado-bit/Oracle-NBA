import os
from dotenv import load_dotenv
from src.utils.email_service import NBAEmailService
from src.utils.logger import logger

load_dotenv()

def test_email_now():
    logger.info("🧪 Iniciando prueba de humo de email...")
    email_service = NBAEmailService()
    
    # Intentamos enviar un correo de prueba
    success = email_service.send_email(
        subject="🚀 Oráculo NBA: Prueba de Humo Exitosa",
        body="Este es un mensaje de prueba para verificar que el sistema de correo está listo para el despliegue a main.",
        is_html=False
    )
    
    if success:
        print("\n✅ ¡PRUEBA EXITOSA! Revisa tu bandeja de entrada.")
    else:
        print("\n❌ FALLO EN EL ENVÍO. Revisa los logs de arriba.")

if __name__ == "__main__":
    test_email_now()
