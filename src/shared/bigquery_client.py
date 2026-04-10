try:
    from google.cloud import bigquery
except ImportError:
    import google.cloud.bigquery as bigquery

import os
import uuid
from datetime import datetime
from src.shared.logger import logger

class BigQueryClient:
    """
    Cliente universal para BigQuery. 
    Direcciona los datos según el deporte especificado.
    """
    def __init__(self, sport='nba'):
        self.sport = sport.lower()
        self.project_id = os.getenv("GCP_PROJECT_ID")
        
        # Datasets dinámicos por deporte
        self.dataset_id_v1 = f"oracle_{self.sport}_ds"
        self.dataset_id_v2 = f"oracle_{self.sport}_v2"
        
        self.client = bigquery.Client(project=self.project_id) if self.project_id else None

    def _get_table_ref(self, dataset_id, table_name):
        return f"{self.project_id}.{dataset_id}.{table_name}"

    def insert_rows(self, dataset_id, table_name, rows):
        """Método genérico para insertar filas en una tabla de BigQuery."""
        if not self.client:
            logger.warning(f"GCP_PROJECT_ID no configurado. Saltando inserción en {table_name}.")
            return False

        table_ref = self._get_table_ref(dataset_id, table_name)
        try:
            errors = self.client.insert_rows_json(table_ref, rows)
            if not errors:
                logger.info(f"Insertadas {len(rows)} filas en {table_name} ({self.sport}).")
                return True
            else:
                logger.error(f"Errores al insertar en {table_name}: {errors}")
                return False
        except Exception as e:
            logger.error(f"Error crítico insertando en {table_name}: {e}")
            return False

    # --- Métodos de Inferencia / Predicciones ---
    def insert_predictions(self, predictions_df, model_version="stacking_v1", experiment_id="unknown"):
        """Inserta predicciones de Moneyline/Game Outcome."""
        if predictions_df is None or predictions_df.empty:
            return False

        rows = []
        for _, row in predictions_df.iterrows():
            rows.append({
                "game_id": str(row.get('GAME_ID')),
                "game_date": datetime.now().strftime('%Y-%m-%d'),
                "home_team_id": int(row.get('HOME_ID')),
                "away_team_id": int(row.get('AWAY_ID')),
                "prob_home_win": float(row.get('PROB_HOME_WIN', 0)),
                "recommendation": str(row.get('RECOMMENDATION', 'NO BET')),
                "model_version": model_version,
                "experiment_id": experiment_id,
                "timestamp": datetime.now().isoformat()
            })

        return self.insert_rows(self.dataset_id_v1, "predictions", rows)

    # --- Métodos de Paper Trading / Bankroll ---
    def get_virtual_bankroll(self, default_balance=20000.0):
        """Obtiene el saldo actual de la banca virtual."""
        if not self.client:
            return default_balance
            
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
            return default_balance
        except Exception as e:
            logger.error(f"Error al obtener bankroll para {self.sport}, asumiendo {default_balance}: {e}")
            return default_balance

    def insert_bets(self, bets_list, market_type='props'):
        """Inserta apuestas en el ledger de Paper Trading (V2)."""
        if not self.client or not bets_list:
            return False

        table_name = "bet_history"
        rows = []
        
        for bet in bets_list:
            rows.append({
                "bet_id": str(uuid.uuid4()),
                "player_name": bet.get('player_name', 'N/A'),
                "market": bet.get('market', market_type),
                "line": float(bet.get('line', 0)),
                "odds_open": float(bet.get('odds_open', 0)),
                "odds_close": bet.get('odds_close'),
                "stake_usd": float(bet.get('stake_usd', 0)),
                "result": bet.get('result', 'PENDING'),
                "payout": float(bet.get('payout', 0.0)),
                "timestamp": datetime.now().isoformat()
            })

        return self.insert_rows(self.dataset_id_v2, table_name, rows)

    # --- Métodos específicos de NBA (Retro-compatibilidad) ---
    def get_top_20_portfolio(self):
        """Obtiene IDs de jugadores del portafolio (Específico para NBA Props)."""
        if not self.client or self.sport != 'nba':
            return [1629013, 1630162] # Mock
            
        query = f"SELECT player_id FROM `{self.project_id}.{self.dataset_id_v2}.top_20_portfolio`"
        try:
            query_job = self.client.query(query)
            return [row.player_id for row in query_job]
        except Exception as e:
            logger.error(f"Error obteniendo portafolio NBA: {e}")
            return []
