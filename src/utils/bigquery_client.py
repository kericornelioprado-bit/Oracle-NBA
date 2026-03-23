try:
    from google.cloud import bigquery
except ImportError:
    # Intento de respaldo si el namespace de Google está fragmentado
    import google.cloud.bigquery as bigquery

import os
from datetime import datetime
from src.utils.logger import logger

class NBABigQueryClient:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.dataset_id = "oracle_nba_ds"
        self.table_id = "predictions"
        self.client = bigquery.Client(project=self.project_id) if self.project_id else None

    def insert_predictions(self, predictions_df, model_version="stacking_v1", experiment_id="unknown"):
        if not self.client:
            logger.warning("GCP_PROJECT_ID no configurado. Saltando inserción en BigQuery.")
            return False

        table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
        
        rows_to_insert = []
        for _, row in predictions_df.iterrows():
            rows_to_insert.append({
                "game_id": str(row['GAME_ID']),
                "game_date": datetime.now().strftime('%Y-%m-%d'),
                "home_team_id": int(row['HOME_ID']),
                "away_team_id": int(row['AWAY_ID']),
                "prob_home_win": float(row['PROB_HOME_WIN']),
                "recommendation": str(row['RECOMMENDATION']),
                "model_version": model_version,
                "experiment_id": experiment_id,
                "timestamp": datetime.now().isoformat()
            })

        try:
            errors = self.client.insert_rows_json(table_ref, rows_to_insert)
            if errors == []:
                logger.info(f"Insertadas {len(rows_to_insert)} filas en BigQuery con éxito.")
                return True
            else:
                logger.error(f"Errores al insertar en BigQuery: {errors}")
                return False
        except Exception as e:
            logger.error(f"Error crítico en BigQueryClient: {e}")
            return False
