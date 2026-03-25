import pandas as pd
from nba_api.stats.endpoints import playergamelogs
from src.utils.logger import logger
import time

class PlayerStatsIngestion:
    """Extrae y procesa los logs de juego a nivel de jugador para calcular features."""
    
    def __init__(self, season='2024-25'):
        self.season = season

    def get_player_logs(self, player_ids=None):
        """
        Obtiene los logs de juego de la temporada para todos o una lista de jugadores.
        """
        logger.info(f"Extrayendo player logs para la temporada {self.season}...")
        try:
            # PlayerGameLogs obtiene los stats de TODOS los jugadores si no se especifica ID
            logs = playergamelogs.PlayerGameLogs(
                season_nullable=self.season,
                season_type_nullable='Regular Season'
            )
            df = logs.get_data_frames()[0]
            
            if player_ids:
                df = df[df['PLAYER_ID'].isin(player_ids)]
                
            # Convertir GAME_DATE a datetime y MIN (minutos) a float
            df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'].str[:10])
            
            # Limpiar minutos. Ejemplo: "28.5" o "28:30"
            if 'MIN' in df.columns:
                # En algunos endpoints MIN es float, en otros es string "MM:SS"
                if df['MIN'].dtype == 'O':
                    df['MIN'] = df['MIN'].apply(self._parse_minutes)
                df['MIN'] = df['MIN'].fillna(0.0).astype(float)
            
            return df.sort_values(by=['PLAYER_ID', 'GAME_DATE'])
        except Exception as e:
            logger.error(f"Error extrayendo player logs: {e}")
            return pd.DataFrame()

    def _parse_minutes(self, min_str):
        """Convierte formato MM:SS a float (ej. 28:30 -> 28.5)"""
        try:
            if pd.isna(min_str) or min_str == '':
                return 0.0
            if ':' in str(min_str):
                parts = str(min_str).split(':')
                return float(parts[0]) + float(parts[1])/60.0
            return float(min_str)
        except:
            return 0.0

    def calculate_rolling_features(self, df):
        """Calcula promedios móviles para minutos, rebotes y asistencias."""
        logger.info("Calculando features móviles de jugadores (L10_min, promedios REB/AST)...")
        
        if df.empty:
            return df
            
        df = df.copy()
        
        # Agrupar por jugador y calcular shift(1) para evitar Data Leakage
        # y luego calcular rolling de 10 juegos
        grouped = df.groupby('PLAYER_ID')
        
        # Calculamos los promedios de los últimos 10 juegos (L10)
        df['L10_MIN'] = grouped['MIN'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_REB'] = grouped['REB'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_AST'] = grouped['AST'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_PTS'] = grouped['PTS'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        
        # Llenar NaNs en L10 con 0
        df[['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']] = df[['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']].fillna(0)
        
        return df

if __name__ == "__main__":
    # Prueba rápida
    ingestion = PlayerStatsIngestion()
    df = ingestion.get_player_logs()
    df_features = ingestion.calculate_rolling_features(df)
    print(df_features[['PLAYER_NAME', 'GAME_DATE', 'MIN', 'L10_MIN', 'REB', 'L10_REB']].tail())
