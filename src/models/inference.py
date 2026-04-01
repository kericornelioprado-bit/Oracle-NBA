import pandas as pd
import numpy as np
import joblib
import os
import time
import json
from datetime import datetime
from src.utils.bdl_client import BallDontLieClient

from src.data.feature_engineering import NBAFeatureEngineer
from src.utils.logger import logger
from src.utils.odds_api import OddsAPIClient
from src.utils.report_generator import NBAReportGenerator
from src.utils.bigquery_client import NBABigQueryClient

# Nuevos módulos V2
from src.data.player_ingestion import PlayerStatsIngestion
from src.models.minutes_projector import MinutesProjector
from src.models.props_model import PlayerPropsModel

class NBAOracleInference:
    def __init__(self, model_path="models/nba_best_model_stacking.joblib"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encontró el modelo en {model_path}. Entrénalo primero.")
        self.model = joblib.load(model_path)
        self.engineer = NBAFeatureEngineer()
        self.odds_client = OddsAPIClient()
        self.bq_client = NBABigQueryClient()
        self.bdl_client = BallDontLieClient()
        
        # Módulos V2
        self.player_ingestion = PlayerStatsIngestion()
        self.minutes_projector = MinutesProjector()
        self.props_model = PlayerPropsModel()
        
        # Obtener banca virtual real desde BQ o default
        self.bankroll = self.bq_client.get_virtual_bankroll()
        self.min_ev = float(os.getenv("MIN_EV_THRESHOLD") or 0.05) # 5% EV mínimo para Props
        self.kelly_fraction = float(os.getenv("KELLY_FRACTION") or 0.25)
        
        # Obtener portafolio actual
        self.top_20_ids = self.bq_client.get_top_20_portfolio()

    def calculate_kelly(self, prob, odds):
        """Calcula el porcentaje de banca a apostar usando Kelly Fraccional."""
        if odds <= 1 or prob <= 0: return 0
        b = odds - 1
        q = 1 - prob
        kelly_full = (prob * b - q) / b
        return max(0, kelly_full * self.kelly_fraction)

    def get_today_games(self):
        """Obtiene los partidos programados para hoy vía BallDontLie."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Obteniendo partidos programados para hoy ({today_str}) vía BallDontLie...")
        try:
            games = self.bdl_client.get_games(start_date=today_str)
            
            if games.empty:
                logger.warning("No hay partidos programados para hoy en BDL.")
                return None
            
            # Formatear para que coincida con lo que espera el resto del código
            # Necesitamos GAME_ID, HOME_TEAM_ID, VISITOR_TEAM_ID
            # BDL entrega una fila por equipo, necesitamos pivotar o agrupar
            
            formatted_games = []
            game_ids = games['GAME_ID'].unique()
            
            for g_id in game_ids:
                g_df = games[games['GAME_ID'] == g_id]
                home = g_df[g_df['MATCHUP'].str.contains('vs.')]
                visitor = g_df[g_df['MATCHUP'].str.contains('@')]
                
                if not home.empty and not visitor.empty:
                    formatted_games.append({
                        'GAME_ID': g_id,
                        'HOME_TEAM_ID': home.iloc[0]['TEAM_ID'],
                        'VISITOR_TEAM_ID': visitor.iloc[0]['TEAM_ID']
                    })
            
            return pd.DataFrame(formatted_games)
        except Exception as e:
            logger.error(f"Error al obtener juegos de BDL: {e}")
            raise

    def fetch_recent_history(self, team_ids):
        """Obtiene el historial reciente de los equipos vía BallDontLie."""
        logger.info(f"Extrayendo historial reciente vía BallDontLie...")
        # Obtenemos juegos de la temporada actual (2023 para 2023-24)
        current_season = 2023 
        try:
            df = self.bdl_client.get_games(seasons=[current_season])
            # Filtrar solo juegos que ya ocurrieron (tienen puntuación)
            df = df[df['WL'].notnull()]
            return df
        except Exception as e:
            logger.warning(f"Fallo al obtener historial de BDL: {e}")
            return pd.DataFrame()

    def predict_today(self):
        today_games = self.get_today_games()
        if today_games is None: return None, None

        # --- 1. PREDICCIÓN MONEYLINE (GAME SCRIPT) ---
        team_ids = list(set(today_games['HOME_TEAM_ID'].tolist() + today_games['VISITOR_TEAM_ID'].tolist()))
        history_df = self.fetch_recent_history(team_ids)
        history_df['GAME_DATE'] = pd.to_datetime(history_df['GAME_DATE'])
        
        processed_history = self.engineer.create_rolling_features(history_df)
        processed_history = self.engineer.calculate_rest_days(processed_history)
        latest_stats = processed_history.groupby('TEAM_ID').tail(1).fillna(0)
        
        config_path = "config/model_features.json"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                feature_cols_order = json.load(f)
        else:
            raw_cols = [c for c in latest_stats.columns if 'ROLL_' in c or 'DAYS_REST' in c]
            feature_cols_order = [f'HOME_{c}' for c in raw_cols] + [f'AWAY_{c}' for c in raw_cols]

        ml_predictions = []
        game_scripts = {} # Guarda el margen esperado por game_id
        
        for _, game in today_games.iterrows():
            home_id = game['HOME_TEAM_ID']
            away_id = game['VISITOR_TEAM_ID']
            
            home_features = latest_stats[latest_stats['TEAM_ID'] == home_id]
            away_features = latest_stats[latest_stats['TEAM_ID'] == away_id]
            if home_features.empty or away_features.empty: continue
                
            feature_vector = {}
            for col in [c for c in latest_stats.columns if 'ROLL_' in c or 'DAYS_REST' in c]:
                feature_vector[f'HOME_{col}'] = home_features[col].values[0]
                feature_vector[f'AWAY_{col}'] = away_features[col].values[0]
            
            X = pd.DataFrame([feature_vector])[feature_cols_order]
            prob_home = self.model.predict_proba(X)[0][1]
            
            # Heurística simple de Game Script: 1% de prob = 0.5 puntos de margen
            margin = (prob_home - 0.5) * 100 * 0.5
            game_scripts[game['GAME_ID']] = margin
            
            ml_predictions.append({
                'GAME_ID': game['GAME_ID'],
                'HOME_ID': home_id,
                'AWAY_ID': away_id,
                'PROB_HOME_WIN': prob_home,
                'RECOMMENDATION': 'HOME' if prob_home > 0.524 else ('AWAY' if prob_home < 0.476 else 'NO BET'),
                'ODDS': 1.91, 'EV': 0.0, 'KELLY_PCT': 0.0, 'UNITS_SUGGESTED': 0.0, 'BOOKMAKER': 'N/A'
            })

        # --- 2. MOTOR DE PROPS (V2) ---
        logger.info(f"Iniciando evaluación de Props para {len(self.top_20_ids)} jugadores del portafolio...")
        player_logs = self.player_ingestion.get_player_logs(self.top_20_ids)
        player_features = self.player_ingestion.calculate_rolling_features(player_logs)

        props_picks = []

        if not player_features.empty:
            latest_player_stats = player_features.groupby('PLAYER_ID').tail(1).set_index('PLAYER_ID').to_dict('index')

            # Construir mapa de cuotas reales desde The Odds API
            # {player_name_lower: {stat: {line, odds, bookmaker}}}
            real_odds_map = {}
            market_to_stat = {
                'player_rebounds': 'REB',
                'player_points':   'PTS',
                'player_assists':  'AST',
            }

            today_events = self.odds_client.get_latest_odds() or []
            for event in today_events:
                event_id = event.get('id')
                props_data = self.odds_client.get_player_props(
                    event_id,
                    markets="player_rebounds,player_points,player_assists"
                )
                if not props_data:
                    continue
                for bookmaker in props_data.get('bookmakers', []):
                    bookie_title = bookmaker.get('title', '')
                    for market in bookmaker.get('markets', []):
                        stat = market_to_stat.get(market.get('key', ''))
                        if not stat:
                            continue
                        for outcome in market.get('outcomes', []):
                            if outcome.get('description', '').lower() != 'over':
                                continue
                            player_key = outcome.get('name', '').lower()
                            price = outcome.get('price', 0.0)
                            point = outcome.get('point', 0.0)
                            if player_key not in real_odds_map:
                                real_odds_map[player_key] = {}
                            existing = real_odds_map[player_key].get(stat)
                            if not existing or price > existing['odds']:
                                real_odds_map[player_key][stat] = {
                                    'line': point, 'odds': price, 'bookmaker': bookie_title
                                }

            logger.info(f"Cuotas reales obtenidas para {len(real_odds_map)} jugadores.")

            # Margen promedio de los partidos de hoy como proxy de game script
            avg_margin = sum(game_scripts.values()) / len(game_scripts) if game_scripts else 0.0

            for player_id, stats in latest_player_stats.items():
                player_name = stats.get('PLAYER_NAME', f'Unknown_{player_id}')
                player_odds = real_odds_map.get(player_name.lower(), {})

                if not player_odds:
                    continue  # sin cuotas reales, no hay pick

                proj_min = self.minutes_projector.project_minutes(stats, avg_margin)

                for stat, odds_info in player_odds.items():
                    expected_stat = self.props_model.predict_stat(stat, proj_min, stats)
                    player_std = stats.get(f'L10_STD_{stat}')

                    line      = odds_info['line']
                    odds_open = odds_info['odds']
                    bookmaker = odds_info['bookmaker']

                    prob_over = self.props_model.calculate_prob_over(expected_stat, line, stat, player_std)
                    ev = self.props_model.calculate_ev(prob_over, odds_open)

                    if ev > self.min_ev:
                        kelly = self.calculate_kelly(prob_over, odds_open)
                        stake = kelly * self.bankroll

                        if stake > 0:
                            pick = {
                                "player_name": player_name,
                                "market":      f"{stat}_OVER",
                                "line":        line,
                                "odds_open":   odds_open,
                                "odds_close":  None,
                                "stake_usd":   round(stake, 2),
                                "bookmaker":   bookmaker,
                                "ev":          round(ev, 4),
                                "kelly_pct":   round(kelly, 4),
                            }
                            props_picks.append(pick)
                            logger.info(f"PICK: {player_name} Over {line} {stat} @ {odds_open} | EV: {ev:.2%} | Stake: ${stake:.2f}")
        
        # Guardar en BigQuery el historial de picks V2
        if props_picks:
            self.bq_client.insert_prop_bets(props_picks)

        return pd.DataFrame(ml_predictions), pd.DataFrame(props_picks)

if __name__ == "__main__":
    oracle = NBAOracleInference()
    oracle.predict_today()
