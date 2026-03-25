try:
    from google.cloud import bigquery
except ImportError:
    import google.cloud.bigquery as bigquery

import os
from datetime import datetime
from src.utils.logger import logger
import uuid

class NBABigQueryClient:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.dataset_id_v1 = "oracle_nba_ds"
        self.dataset_id_v2 = "oracle_nba_v2"
        self.client = bigquery.Client(project=self.project_id) if self.project_id else None

    # --- Métodos V1: Moneyline (Restaurado Completo) ---
    def insert_predictions(self, predictions_df, model_version="stacking_v1", experiment_id="unknown"):
        """Inserta las predicciones de Moneyline en el dataset original (oracle_nba_ds)."""
        if not self.client:
            logger.warning("GCP_PROJECT_ID no configurado. Saltando inserción Moneyline.")
            return False

        table_ref = f"{self.project_id}.{self.dataset_id_v1}.predictions"
        
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
                logger.info(f"Insertadas {len(rows_to_insert)} filas de Moneyline en BigQuery.")
                return True
            else:
                logger.error(f"Errores al insertar Moneyline en BigQuery: {errors}")
                return False
        except Exception as e:
            logger.error(f"Error crítico insertando Moneyline: {e}")
            return False

    # --- Métodos V2: Paper Trading ($20,000) ---
    def get_virtual_bankroll(self):
        """Obtiene el saldo actual de la banca virtual (inicia en 20000)."""
        if not self.client:
            return 20000.0
            
        query = f"""
            SELECT current_balance 
            FROM `{self.project_id}.{self.dataset_id_v2}.virtual_bankroll`
            ORDER BY last_updated DESC LIMIT 1
        """
        try:
            query_job = self.client.query(query)
            results = list(query_job.result())
            if results:
                return float(results[0].current_balance)
            return 20000.0
        except Exception as e:
            logger.error(f"Error al obtener bankroll, asumiendo 20000: {e}")
            return 20000.0

    def insert_prop_bets(self, bets_list):
        """Inserta picks de Player Props en el ledger de V2."""
        if not self.client or not bets_list:
            return False

        table_ref = f"{self.project_id}.{self.dataset_id_v2}.bet_history"
        rows_to_insert = []
        
        for bet in bets_list:
            rows_to_insert.append({
                "bet_id": str(uuid.uuid4()),
                "player_name": bet.get('player_name'),
                "market": bet.get('market'),
                "line": float(bet.get('line', 0)),
                "odds_open": float(bet.get('odds_open', 0)),
                "odds_close": None,
                "stake_usd": float(bet.get('stake_usd', 0)),
                "result": "PENDING",
                "payout": 0.0,
                "timestamp": datetime.now().isoformat()
            })

        try:
            errors = self.client.insert_rows_json(table_ref, rows_to_insert)
            if not errors:
                logger.info(f"Registradas {len(rows_to_insert)} apuestas de Props en V2.")
                return True
            else:
                logger.error(f"Errores al insertar Props en BQ: {errors}")
                return False
        except Exception as e:
            logger.error(f"Excepción al insertar Props en BQ: {e}")
            return False

    def get_top_20_portfolio(self):
        """Obtiene la lista de IDs de jugadores del portafolio actual."""
        if not self.client:
            return [1629013, 1630162] # Mock IDs para local
            
        query = f"SELECT player_id FROM `{self.project_id}.{self.dataset_id_v2}.top_20_portfolio`"
        try:
            query_job = self.client.query(query)
            return [row.player_id for row in query_job]
        except Exception as e:
            logger.error(f"Error obteniendo portafolio: {e}")
            return []
