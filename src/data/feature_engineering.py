import pandas as pd
import numpy as np
import os
from src.utils.logger import logger

class NBAFeatureEngineer:
    def __init__(self, input_path="data/raw/nba_games_raw.parquet", output_path="data/processed/nba_games_features.parquet"):
        self.input_path = input_path
        self.output_path = output_path

    def load_data(self):
        df = pd.read_parquet(self.input_path)
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values(['TEAM_ID', 'GAME_DATE'])
        return df

    def create_rolling_features(self, df, windows=[3, 5, 10, 20]):
        """Calcula promedios móviles para cada equipo."""
        cols_to_roll = ['PTS', 'FG_PCT', 'FG3_PCT', 'FT_PCT', 'AST', 'REB', 'TOV', 'PLUS_MINUS']
        
        logger.info(f"Calculando medias móviles para ventanas: {windows}...")
        
        for window in windows:
            for col in cols_to_roll:
                # Importante: Usamos shift(1) para evitar el 'data leakage' 
                # (no queremos que el promedio incluya el juego que intentamos predecir)
                df[f'ROLL_{col}_{window}'] = df.groupby('TEAM_ID')[col].transform(
                    lambda x: x.shift(1).rolling(window=window).mean()
                )
        return df

    def calculate_rest_days(self, df):
        """Calcula los días de descanso entre partidos."""
        logger.info("Calculando días de descanso...")
        df['DAYS_REST'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
        # Llenar nulos (primer juego de la temporada) con un valor razonable como 7 días
        df['DAYS_REST'] = df['DAYS_REST'].fillna(7).clip(upper=10)
        return df

    def structure_for_modeling(self, df):
        """
        Transforma el dataset de 2 filas por juego (una por equipo) 
        a 1 fila por juego con columnas para local y visitante.
        """
        logger.info("Estructurando dataset para modelado (1 fila por juego)...")
        
        # Identificar local y visitante basado en la columna MATCHUP
        # 'WAS @ CHA' -> WAS es visitante (@), CHA es local
        # 'CHA vs. WAS' -> CHA es local (vs.), WAS es visitante
        df['IS_HOME'] = df['MATCHUP'].apply(lambda x: 1 if 'vs.' in x else 0)
        
        # Separar en dos DataFrames
        home_df = df[df['IS_HOME'] == 1].copy()
        away_df = df[df['IS_HOME'] == 0].copy()
        
        # Columnas que queremos mantener para el modelo (las que calculamos)
        feature_cols = [col for col in df.columns if 'ROLL_' in col] + ['DAYS_REST', 'TEAM_ID', 'GAME_ID', 'GAME_DATE', 'WL']
        
        # Renombrar columnas para distinguir local de visitante
        home_df = home_df[feature_cols].rename(columns={col: f'HOME_{col}' for col in feature_cols if col not in ['GAME_ID', 'GAME_DATE']})
        away_df = away_df[feature_cols].rename(columns={col: f'AWAY_{col}' for col in feature_cols if col not in ['GAME_ID', 'GAME_DATE']})
        
        # Unir por GAME_ID
        final_df = pd.merge(home_df, away_df, on=['GAME_ID', 'GAME_DATE'])
        
        # Definir el Target: 1 si ganó el local, 0 si ganó el visitante
        final_df['TARGET'] = final_df['HOME_WL'].apply(lambda x: 1 if x == 'W' else 0)
        
        # Eliminar columnas de control que ya no necesitamos
        final_df = final_df.drop(columns=['HOME_WL', 'AWAY_WL'])
        
        return final_df

    def run(self):
        df = self.load_data()
        df = self.create_rolling_features(df)
        df = self.calculate_rest_days(df)
        final_df = self.structure_for_modeling(df)
        
        # Limpiar filas con NaN (los primeros juegos de cada equipo no tienen promedio móvil)
        logger.info(f"Registros antes de limpiar nulos: {len(final_df)}")
        final_df = final_df.dropna()
        logger.info(f"Registros listos para el modelo: {len(final_df)}")
        
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        final_df.to_parquet(self.output_path, index=False)
        logger.info(f"Dataset procesado guardado en {self.output_path}")
        return final_df

if __name__ == "__main__":
    engineer = NBAFeatureEngineer()
    engineer.run()
