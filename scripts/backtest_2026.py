import pandas as pd
import numpy as np
import joblib
import os
import json
from datetime import datetime, timedelta
from src.utils.bdl_client import BallDontLieClient
from src.data.feature_engineering import NBAFeatureEngineer
from src.utils.logger import logger

class NBABacktester:
    def __init__(self, model_path="models/nba_best_model_stacking.joblib"):
        self.model = joblib.load(model_path)
        self.engineer = NBAFeatureEngineer()
        self.bdl_client = BallDontLieClient()
        
        with open("config/model_features.json", "r") as f:
            self.feature_cols = json.load(f)
            
        self.initial_bankroll = 1000.0 # Config de .env.example
        self.current_bankroll = self.initial_bankroll
        self.kelly_fraction = 0.25
        self.bet_history = []

    def fetch_all_season_games(self, season=2025):
        """Obtiene todos los juegos de la temporada 2025-26."""
        logger.info(f"🏀 Extrayendo datos reales de la temporada {season}-26 vía BDL (Nivel GOAT)...")
        # Para backtesting necesitamos stats detalladas para reconstruir las rolling features
        # get_games nos da los scores, pero para las features necesitamos pts, reb, ast, etc.
        # Por simplicidad en este script, usaremos get_games y asumiremos que las features
        # se calculan sobre el historial que vamos construyendo.
        
        # OJO: Para un backtest PRECISO, deberíamos usar get_player_stats agrupado por equipo
        # o un endpoint de team_stats si BDL lo tuviera. Usaremos get_games para obtener el WL
        # y simularemos que las features vienen del historial previo.
        games_df = self.bdl_client.get_games(seasons=[season])
        if games_df.empty:
            logger.error("No se encontraron juegos para la temporada.")
            return None
        
        games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
        return games_df.sort_values('GAME_DATE')

    def calculate_kelly(self, prob, odds=1.91):
        """Calcula el stake basado en Kelly."""
        if odds <= 1 or prob <= 0: return 0
        b = odds - 1
        q = 1 - prob
        kelly_full = (prob * b - q) / b
        return max(0, kelly_full * self.kelly_fraction)

    def run_simulation(self, games_df):
        logger.info(f"🚀 Iniciando simulación desde {games_df['GAME_DATE'].min().date()} hasta hoy...")
        
        # Reconstruir features. El FeatureEngineer espera un DF con historial.
        # En un backtest real, para cada día calculamos las features basadas en el pasado.
        
        # Simplificación para el reporte: Calculamos todas las features de una vez 
        # PERO asegurándonos de que cada fila solo use información del pasado (shift(1)).
        full_history = self.engineer.create_rolling_features(games_df)
        full_history = self.engineer.calculate_rest_days(full_history)
        
        unique_games = games_df['GAME_ID'].unique()
        
        for g_id in unique_games:
            # Obtener las dos filas del juego (Home y Away)
            game_rows = full_history[full_history['GAME_ID'] == g_id]
            if len(game_rows) < 2: continue
            
            # Identificar Home y Away
            # En BDL mapped format, home tiene 'vs.' y away tiene '@' en MATCHUP
            home_row = game_rows[game_rows['MATCHUP'].str.contains('vs.')].iloc[0]
            away_row = game_rows[game_rows['MATCHUP'].str.contains('@')].iloc[0]
            
            # Construir vector de features
            feature_vector = {}
            raw_cols = [c for c in full_history.columns if 'ROLL_' in c or 'DAYS_REST' in c]
            for col in raw_cols:
                feature_vector[f'HOME_{col}'] = home_row[col]
                feature_vector[f'AWAY_{col}'] = away_row[col]
                
            X = pd.DataFrame([feature_vector])[self.feature_cols]
            X = X.fillna(0) # Manejar juegos al inicio de temporada sin historial suficiente
            
            # Predecir
            prob_home = self.model.predict_proba(X)[0][1]
            actual_winner = "HOME" if home_row['WL'] == 'W' else "AWAY"
            
            # Decisión de apuesta (Uso el umbral de 52.4% para compensar el vigorish del 4.5% / cuota 1.91)
            odds = 1.91
            recommendation = None
            if prob_home > 0.524:
                recommendation = "HOME"
                prob_bet = prob_home
            elif prob_home < 0.476:
                recommendation = "AWAY"
                prob_bet = 1 - prob_home
            
            if recommendation:
                kelly_pct = self.calculate_kelly(prob_bet, odds)
                if kelly_pct > 0:
                    stake = self.current_bankroll * kelly_pct
                    is_win = (recommendation == actual_winner)
                    profit = stake * (odds - 1) if is_win else -stake
                    
                    self.current_bankroll += profit
                    self.bet_history.append({
                        'date': home_row['GAME_DATE'],
                        'matchup': home_row['MATCHUP'],
                        'prob': prob_bet,
                        'bet': recommendation,
                        'winner': actual_winner,
                        'stake': stake,
                        'profit': profit,
                        'bankroll': self.current_bankroll
                    })

    def report(self):
        if not self.bet_history:
            print("No se realizaron apuestas en el periodo.")
            return
            
        df = pd.DataFrame(self.bet_history)
        total_bets = len(df)
        wins = len(df[df['profit'] > 0])
        win_rate = wins / total_bets
        total_profit = self.current_bankroll - self.initial_bankroll
        roi = (total_profit / (df['stake'].sum())) * 100
        
        print("\n" + "="*40)
        print("📊 REPORTE DE BACKTESTING NBA 2025-26")
        print("="*40)
        print(f"Periodo: {df['date'].min().date()} a {df['date'].max().date()}")
        print(f"Banca Inicial: ${self.initial_bankroll:.2f}")
        print(f"Banca Final:   ${self.current_bankroll:.2f}")
        print(f"Ganancia/Pérdida: ${total_profit:+.2f}")
        print(f"ROI Estimado: {roi:.2%}")
        print("-" * 40)
        print(f"Total apuestas: {total_bets}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Max Stake: ${df['stake'].max():.2f}")
        print(f"Min Stake: ${df['stake'].min():.2f}")
        print("="*40)
        
        # Guardar resultados
        df.to_csv("data/results/backtest_2026_results.csv", index=False)
        print("✅ Resultados detallados guardados en data/results/backtest_2026_results.csv")

if __name__ == "__main__":
    backtester = NBABacktester()
    games = backtester.fetch_all_season_games(season=2025)
    if games is not None:
        backtester.run_simulation(games)
        backtester.report()
