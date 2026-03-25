import os
from datetime import datetime
from google.cloud import bigquery
from src.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

def init_v2_infrastructure():
    """Inicializa el estado inicial de la banca y el portafolio en BigQuery V2."""
    project_id = os.getenv("GCP_PROJECT_ID", "oracle-nba")
    dataset_id = "oracle_nba_v2"
    
    client = bigquery.Client(project=project_id)
    
    # 1. Inicializar Banca Virtual con $20,000 USD
    logger.info(f"Inicializando banca virtual con $20,000 en {dataset_id}.virtual_bankroll...")
    bankroll_query = f"""
        INSERT INTO `{project_id}.{dataset_id}.virtual_bankroll` (current_balance, last_updated)
        VALUES (20000.0, CURRENT_TIMESTAMP())
    """
    
    # 2. Inicializar Portafolio de Jugadores Iniciales (Tier 1 y 2)
    # IDs de ejemplo (pueden ser Naz Reid, Malik Monk, etc. según temporada)
    logger.info(f"Cargando portafolio inicial en {dataset_id}.top_20_portfolio...")
    portfolio_query = f"""
        INSERT INTO `{project_id}.{dataset_id}.top_20_portfolio` (tier, player_id, minute_swing, updated_at)
        VALUES 
            (1, 1629013, 15.2, CURRENT_TIMESTAMP()), -- Naz Reid
            (1, 1628374, 12.1, CURRENT_TIMESTAMP()), -- Derrick White
            (2, 1630162, 8.5, CURRENT_TIMESTAMP())   -- Anthony Edwards (Ejemplo backup/volatilidad)
    """
    
    try:
        # Ejecutar banca
        client.query(bankroll_query).result()
        logger.info("✅ BANCA INICIALIZADA: $20,000.00")
        
        # Ejecutar portafolio
        client.query(portfolio_query).result()
        logger.info("✅ PORTAFOLIO INICIAL CARGADO.")
        
    except Exception as e:
        logger.error(f"❌ Error durante la inicialización de datos: {e}")
        logger.info("Asegúrate de haber ejecutado 'terraform apply' primero para crear el dataset y las tablas.")

if __name__ == "__main__":
    init_v2_infrastructure()
