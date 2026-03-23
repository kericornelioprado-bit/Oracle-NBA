import pandas as pd
import numpy as np
import joblib
from nba_api.stats.endpoints import scoreboardv2, leaguegamefinder
from src.data.feature_engineering import NBAFeatureEngineer
from src.utils.logger import logger
from datetime import datetime
import os

class NBAOracleInference:
    def __init__(self, model_path="models/nba_best_model_stacking.joblib"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encontró el modelo en {model_path}. Entrénalo primero.")
        self.model = joblib.load(model_path)
        self.engineer = NBAFeatureEngineer()

    def get_today_games(self):
        """Obtiene los partidos programados para hoy."""
        logger.info("Obteniendo partidos programados para hoy...")
        sb = scoreboardv2.ScoreboardV2()
        games = sb.get_data_frames()[0]
        
        if games.empty:
            logger.warning("No hay partidos programados para hoy.")
            return None
            
        # Limpiar y formatear
        games = games[['GAME_ID', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID']]
        return games

    def fetch_recent_history(self, team_ids, days_back=60):
        """Obtiene el historial reciente de los equipos para calcular features."""
        logger.info(f"Extrayendo historial reciente para los equipos: {team_ids}")
        all_history = []
        for team_id in team_ids:
            game_finder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                league_id_nullable='00',
                season_type_nullable='Regular Season'
            )
            df = game_finder.get_data_frames()[0]
            all_history.append(df)
            
        return pd.concat(all_history).drop_duplicates(subset='GAME_ID')

    def predict_today(self):
        today_games = self.get_today_games()
        if today_games is None: return

        # Obtener IDs únicos de equipos que juegan hoy
        team_ids = list(set(today_games['HOME_TEAM_ID'].tolist() + today_games['VISITOR_TEAM_ID'].tolist()))
        
        # Obtener historial reciente para calcular medias móviles
        history_df = self.fetch_recent_history(team_ids)
        
        # CORRECCIÓN: Convertir fecha a datetime antes de procesar
        history_df['GAME_DATE'] = pd.to_datetime(history_df['GAME_DATE'])
        
        # Ejecutar ingeniería de características sobre el historial
        processed_history = self.engineer.create_rolling_features(history_df)
        processed_history = self.engineer.calculate_rest_days(processed_history)
        
        # Extraer solo la última fila de cada equipo (su estado actual)
        latest_stats = processed_history.groupby('TEAM_ID').tail(1)
        
        # CORRECCIÓN DEFINITIVA: Imputar nulos asegurando persistencia
        cols_to_fill = ['PTS', 'FG_PCT', 'FG3_PCT', 'FT_PCT', 'AST', 'REB', 'TOV', 'PLUS_MINUS']
        for col in cols_to_fill:
            for window_target, window_source in [('20', '10'), ('10', '5'), ('5', '3')]:
                target_col = f'ROLL_{col}_{window_target}'
                source_col = f'ROLL_{col}_{window_source}'
                latest_stats[target_col] = latest_stats[target_col].fillna(latest_stats[source_col])
            
            # Último recurso: llenar con 0 (muy raro si el equipo ha jugado al menos un partido)
            latest_stats[f'ROLL_{col}_3'] = latest_stats[f'ROLL_{col}_3'].fillna(0)
        
        latest_stats['DAYS_REST'] = latest_stats['DAYS_REST'].fillna(2)
        
        # Eliminar cualquier fila que aún tenga nulos (seguridad final)
        latest_stats = latest_stats.fillna(0)
        
        # Obtener el orden de columnas con el que se entrenó el modelo
        # (Lo extraemos del dataset procesado para asegurar consistencia total)
        train_features_path = "data/processed/nba_games_features.parquet"
        train_df = pd.read_parquet(train_features_path)
        feature_cols_order = [col for col in train_df.columns if 'ROLL_' in col or 'DAYS_REST' in col]

        predictions = []
        for _, game in today_games.iterrows():
            home_id = game['HOME_TEAM_ID']
            away_id = game['VISITOR_TEAM_ID']
            
            home_features = latest_stats[latest_stats['TEAM_ID'] == home_id]
            away_features = latest_stats[latest_stats['TEAM_ID'] == away_id]
            
            if home_features.empty or away_features.empty:
                logger.warning(f"Faltan datos para el juego {game['GAME_ID']}")
                continue
                
            # Construir vector de características
            feature_vector = {}
            for col in [c for c in latest_stats.columns if 'ROLL_' in c or 'DAYS_REST' in c]:
                feature_vector[f'HOME_{col}'] = home_features[col].values[0]
                feature_vector[f'AWAY_{col}'] = away_features[col].values[0]
            
            # Crear DataFrame y REORDENAR columnas según el entrenamiento
            X = pd.DataFrame([feature_vector])
            X = X[feature_cols_order]
            
            proba = self.model.predict_proba(X)[0][1]
            
            predictions.append({
                'GAME_ID': game['GAME_ID'],
                'HOME_ID': home_id,
                'AWAY_ID': away_id,
                'PROB_HOME_WIN': proba,
                'RECOMMENDATION': 'HOME' if proba > 0.524 else ('AWAY' if proba < 0.476 else 'SKIP')
            })

        result_df = pd.DataFrame(predictions)
        print("\n=== CARTELERA DE APUESTAS DEL DÍA (ORÁCULO NBA) ===")
        print(result_df[['HOME_ID', 'AWAY_ID', 'PROB_HOME_WIN', 'RECOMMENDATION']])
        return result_df

if __name__ == "__main__":
    oracle = NBAOracleInference()
    oracle.predict_today()
