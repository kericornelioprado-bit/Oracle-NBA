import os
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger

def main():
    """
    Job dominical: Recalcula el portafolio Top 20 y actualiza BigQuery.
    """
    logger.info("Iniciando Sunday Update: Re-evaluación del Portafolio Top 20...")
    bq = NBABigQueryClient()
    
    if not bq.client:
        logger.error("No hay cliente de BigQuery disponible.")
        return
        
    # En un escenario real, aquí se ejecutaría una query compleja sobre 
    # los logs de los jugadores de la última semana para calcular el 'minute_swing'.
    # Para el MVP, simularemos la actualización con la query base descrita en el PRD.
    
    query = f"""
    -- Pseudo-query simulada de reemplazo para V2
    CREATE OR REPLACE TABLE `{bq.project_id}.{bq.dataset_id}.top_20_portfolio` AS
    SELECT 
        1 as tier,
        1629013 as player_id, -- Ej: ID de un 6to hombre
        12.5 as minute_swing,
        CURRENT_TIMESTAMP() as updated_at
    UNION ALL
    SELECT 
        2 as tier,
        1630162 as player_id, -- Ej: ID de un backup
        8.0 as minute_swing,
        CURRENT_TIMESTAMP() as updated_at
    """
    
    try:
        query_job = bq.client.query(query)
        query_job.result() # Espera a que termine
        logger.info("✅ Portafolio Top 20 actualizado exitosamente para la nueva semana.")
    except Exception as e:
        logger.error(f"❌ Error actualizando portafolio: {e}")

if __name__ == "__main__":
    main()
