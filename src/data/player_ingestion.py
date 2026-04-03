import pandas as pd
from src.utils.bdl_client import BallDontLieClient
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger
import time

# Desviaciones estándar por defecto (fallback cuando hay < 3 juegos de historial)
_DEFAULT_STD = {'MIN': 4.0, 'REB': 2.5, 'AST': 2.0, 'PTS': 5.5}


class PlayerStatsIngestion:
    """Extrae y procesa los logs de juego a nivel de jugador para calcular features."""

    def __init__(self, season=2024):
        # BDL usa el año de inicio como entero
        self.season = season
        self.bdl_client = BallDontLieClient()

    def get_player_logs(self, player_ids=None, start_date=None):
        """
        Obtiene los logs de juego para todos o una lista de jugadores vía BallDontLie.
        Si se pasa start_date (YYYY-MM-DD), filtra desde esa fecha en adelante (ignora season).
        """
        if start_date:
            logger.info(f"Extrayendo player logs desde {start_date} vía BallDontLie...")
        else:
            logger.info(f"Extrayendo player logs para la temporada {self.season} vía BallDontLie...")
        try:
            if start_date:
                df = self.bdl_client.get_player_stats(player_ids=player_ids, start_date=start_date)
            else:
                df = self.bdl_client.get_player_stats(seasons=[self.season], player_ids=player_ids)
            
            if df.empty:
                logger.warning("No se encontraron logs de jugadores en BDL.")
                return df

            # Convertir GAME_DATE a datetime y MIN (minutos) a float
            df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
            
            # Limpiar minutos. BDL entrega minutos como string "MM:SS" o similar
            if 'MIN' in df.columns:
                df['MIN'] = df['MIN'].apply(self._parse_minutes)
                df['MIN'] = df['MIN'].fillna(0.0).astype(float)
            
            return df.sort_values(by=['PLAYER_ID', 'GAME_DATE'])
        except Exception as e:
            logger.error(f"Error extrayendo player logs de BDL: {e}")
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
        """Calcula promedios y desviaciones estándar móviles (L10) con shift(1) anti-leakage."""
        logger.info("Calculando features móviles de jugadores (L10 promedios + std)...")

        if df.empty:
            return df

        df = df.copy()
        grouped = df.groupby('PLAYER_ID')

        # Promedios L10
        df['L10_MIN'] = grouped['MIN'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_REB'] = grouped['REB'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_AST'] = grouped['AST'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
        df['L10_PTS'] = grouped['PTS'].transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())

        df[['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']] = (
            df[['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']].fillna(0)
        )

        # Desviaciones estándar L10 (requiere min 3 juegos; fallback a DEFAULT)
        # shift(1) garantiza que el juego actual no contamina su propia std
        for stat, default_std in _DEFAULT_STD.items():
            col = f'L10_STD_{stat}'
            df[col] = (
                grouped[stat]
                .transform(lambda x: x.shift(1).rolling(10, min_periods=3).std())
                .fillna(default_std)
            )

        return df

    def enrich_with_game_context(self, player_df):
        """
        Agrega GAME_MARGIN y TEAM_L10_MARGIN a cada fila de player_df.

        - GAME_MARGIN: margen real del partido desde la perspectiva del equipo del jugador
          (positivo = su equipo ganó, negativo = perdió). Requiere join con /games de BDL.
        - TEAM_L10_MARGIN: promedio móvil L10 del margen del equipo (predictor de Game Script
          sin data leakage). Se usa como input del MinutesProjector en el backtest.

        Si la API falla o no hay GAME_ID/TEAM_ID, rellena con 0.
        """
        if player_df.empty:
            player_df['GAME_MARGIN'] = 0.0
            player_df['TEAM_L10_MARGIN'] = 0.0
            return player_df

        if 'GAME_ID' not in player_df.columns or 'TEAM_ID' not in player_df.columns:
            logger.warning("enrich_with_game_context: faltan columnas GAME_ID o TEAM_ID. Usando 0.")
            player_df['GAME_MARGIN'] = 0.0
            player_df['TEAM_L10_MARGIN'] = 0.0
            return player_df

        logger.info("Enriqueciendo player logs con contexto de juego (márgenes)...")
        games_df = self.bdl_client.get_games(seasons=[self.season])

        if games_df.empty:
            logger.warning("No se obtuvieron juegos de BDL. GAME_MARGIN = 0.")
            player_df['GAME_MARGIN'] = 0.0
            player_df['TEAM_L10_MARGIN'] = 0.0
            return player_df

        margin_map = (
            games_df[['GAME_ID', 'TEAM_ID', 'PLUS_MINUS']]
            .rename(columns={'PLUS_MINUS': 'GAME_MARGIN'})
        )
        enriched = player_df.merge(margin_map, on=['GAME_ID', 'TEAM_ID'], how='left')
        enriched['GAME_MARGIN'] = enriched['GAME_MARGIN'].fillna(0.0)

        enriched = self._add_team_rolling_margin(enriched)
        return enriched

    def _add_team_rolling_margin(self, df):
        """
        Calcula TEAM_L10_MARGIN: promedio móvil del GAME_MARGIN del equipo
        en los últimos 10 juegos, con shift(1) para evitar data leakage.
        Un registro por (TEAM_ID, GAME_DATE) evita duplicados por múltiples jugadores.
        """
        if 'GAME_MARGIN' not in df.columns or 'GAME_DATE' not in df.columns:
            df['TEAM_L10_MARGIN'] = 0.0
            return df

        team_game = (
            df[['TEAM_ID', 'GAME_DATE', 'GAME_MARGIN']]
            .drop_duplicates(subset=['TEAM_ID', 'GAME_DATE'])
            .sort_values(['TEAM_ID', 'GAME_DATE'])
            .copy()
        )
        team_game['TEAM_L10_MARGIN'] = (
            team_game.groupby('TEAM_ID')['GAME_MARGIN']
            .transform(lambda x: x.shift(1).rolling(10, min_periods=1).mean())
            .fillna(0.0)
        )
        return df.merge(
            team_game[['TEAM_ID', 'GAME_DATE', 'TEAM_L10_MARGIN']],
            on=['TEAM_ID', 'GAME_DATE'],
            how='left',
        ).fillna({'TEAM_L10_MARGIN': 0.0})

if __name__ == "__main__":
    # Prueba rápida
    ingestion = PlayerStatsIngestion()
    df = ingestion.get_player_logs()
    df_features = ingestion.calculate_rolling_features(df)
    print(df_features[['PLAYER_NAME', 'GAME_DATE', 'MIN', 'L10_MIN', 'REB', 'L10_REB']].tail())
