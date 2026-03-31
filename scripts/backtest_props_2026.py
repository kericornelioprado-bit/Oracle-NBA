"""
Backtest de Player Props V2 — temporada 2025-26

Pipeline:
  1. Player logs (BallDontLie) → rolling features L10 + std por jugador
  2. Games (BallDontLie) → Modelo Moneyline predice el margen por partido
  3. MinutesProjector usa el margen predicho (no un proxy histórico)
  4. Props model predice E[stat] con std real del jugador
  5. Kelly sizing y registro de resultados

El edge central: el modelo Moneyline predice blowouts específicos.
Las líneas de bench players reflejan sus promedios históricos (L10),
que no anticipan el partido de hoy. Cuando el modelo predice paliza,
estos jugadores jugarán más minutos de lo que la casa asume.
"""
import json
import os

import joblib
import pandas as pd

from src.data.feature_engineering import NBAFeatureEngineer
from src.data.player_ingestion import PlayerStatsIngestion
from src.models.minutes_projector import MinutesProjector
from src.models.props_model import PlayerPropsModel
from src.utils.logger import logger

# Portafolio: bench players cuyas líneas son menos eficientes
PORTFOLIO_MIN_LOW  = 15.0   # mín. minutos para rotación estable
PORTFOLIO_MIN_HIGH = 27.0   # por debajo del umbral de titular (28 min)
PORTFOLIO_STD_MIN  = 3.0    # alta variabilidad de minutos (sensibles al game script)


class PropsBacktester:
    def __init__(self, season=2025,
                 model_path="models/nba_best_model_stacking.joblib",
                 features_path="config/model_features.json"):
        self.season = season
        self.ingestion = PlayerStatsIngestion(season=season)
        self.minutes_projector = MinutesProjector()
        self.props_model = PlayerPropsModel()
        self.engineer = NBAFeatureEngineer()

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
        self.model = joblib.load(model_path)

        with open(features_path) as f:
            self.feature_cols = json.load(f)

        self.initial_bankroll = 1000.0
        self.current_bankroll = self.initial_bankroll
        self.kelly_fraction   = 0.25
        self.min_ev           = 0.05
        self.bet_history      = []

    # ------------------------------------------------------------------
    # Kelly
    # ------------------------------------------------------------------

    def _kelly(self, prob, odds=1.90):
        if odds <= 1 or prob <= 0:
            return 0.0
        b = odds - 1
        kelly_full = (prob * b - (1 - prob)) / b
        return max(0.0, kelly_full * self.kelly_fraction)

    # ------------------------------------------------------------------
    # Game Script: Moneyline model → margen predicho por partido
    # ------------------------------------------------------------------

    def _build_game_scripts(self, games_df):
        """
        Para cada juego en games_df, corre el modelo Moneyline con las features
        del equipo LOCAL y VISITANTE computadas ANTES de ese juego (shift(1)).

        Retorna dict: {GAME_ID: {'home_team_id': int, 'predicted_margin': float}}
          predicted_margin > 0  → modelo espera que gane el local
          predicted_margin < 0  → modelo espera que gane el visitante
        """
        if games_df.empty:
            logger.warning("_build_game_scripts: games_df vacío, sin predicciones.")
            return {}

        gdf = games_df.copy()
        gdf['GAME_DATE'] = pd.to_datetime(gdf['GAME_DATE'])
        gdf = gdf.sort_values(['TEAM_ID', 'GAME_DATE'])

        # Rolling features de equipos (shift(1) → sin data leakage)
        gdf = self.engineer.create_rolling_features(gdf)
        gdf = self.engineer.calculate_rest_days(gdf)

        gdf['IS_HOME'] = gdf['MATCHUP'].apply(lambda x: 1 if 'vs.' in x else 0)

        roll_cols = [c for c in gdf.columns if 'ROLL_' in c or c == 'DAYS_REST']

        home_df = (
            gdf[gdf['IS_HOME'] == 1][['GAME_ID', 'TEAM_ID'] + roll_cols]
            .rename(columns={c: f'HOME_{c}' for c in roll_cols})
            .rename(columns={'TEAM_ID': 'HOME_TEAM_ID'})
        )
        away_df = (
            gdf[gdf['IS_HOME'] == 0][['GAME_ID', 'TEAM_ID'] + roll_cols]
            .rename(columns={c: f'AWAY_{c}' for c in roll_cols})
            .rename(columns={'TEAM_ID': 'AWAY_TEAM_ID'})
        )

        combined = home_df.merge(away_df, on='GAME_ID', how='inner')

        X = combined.reindex(columns=self.feature_cols).fillna(0)
        probs_home = self.model.predict_proba(X)[:, 1]

        game_scripts = {}
        for i, row in enumerate(combined.itertuples(index=False)):
            # Heurística usada también en predict_today():
            # 1 pp de prob = 0.5 puntos de margen esperado
            predicted_margin = (probs_home[i] - 0.5) * 100 * 0.5
            game_scripts[row.GAME_ID] = {
                'home_team_id':    row.HOME_TEAM_ID,
                'predicted_margin': predicted_margin,
                'prob_home':        probs_home[i],
            }

        logger.info(
            f"Game scripts calculados para {len(game_scripts)} partidos. "
            f"Promedio |margen predicho|: "
            f"{pd.Series([v['predicted_margin'] for v in game_scripts.values()]).abs().mean():.1f} pts"
        )
        return game_scripts

    # ------------------------------------------------------------------
    # Backtest principal
    # ------------------------------------------------------------------

    def run_backtest(self):
        logger.info(f"Iniciando Backtest Props V2 — temporada {self.season}-26")

        # 1. Player logs y features rolling (L10 promedios + std por jugador)
        player_logs = self.ingestion.get_player_logs()
        if player_logs.empty:
            logger.error("Sin logs de jugadores.")
            return
        player_data = self.ingestion.calculate_rolling_features(player_logs)

        # 2. Games — una sola llamada a la API (reutilizada abajo)
        logger.info("Descargando juegos de la temporada para Moneyline + contexto...")
        games_df = self.ingestion.bdl_client.get_games(seasons=[self.season])

        # 3. Añadir GAME_MARGIN real (para diagnóstico, no para el edge)
        if not games_df.empty and 'GAME_ID' in player_data.columns:
            margin_map = (
                games_df[['GAME_ID', 'TEAM_ID', 'PLUS_MINUS']]
                .rename(columns={'PLUS_MINUS': 'GAME_MARGIN'})
            )
            player_data = player_data.merge(margin_map, on=['GAME_ID', 'TEAM_ID'], how='left')
            player_data['GAME_MARGIN'] = player_data['GAME_MARGIN'].fillna(0.0)
        else:
            player_data['GAME_MARGIN'] = 0.0

        # 4. Game Scripts: modelo Moneyline predice margen por partido
        game_scripts = self._build_game_scripts(games_df)

        # 5. Mapear equipo local a cada partido (para saber el signo del margen)
        home_teams = (
            games_df[games_df['MATCHUP'].str.contains('vs.', na=False)]
            [['GAME_ID', 'TEAM_ID']]
            .rename(columns={'TEAM_ID': 'HOME_TEAM_ID'})
        )
        player_data = player_data.merge(home_teams, on='GAME_ID', how='left')

        # 6. Portafolio: bench players con alta varianza de minutos
        valid_bets = player_data[
            player_data['L10_MIN'].between(PORTFOLIO_MIN_LOW, PORTFOLIO_MIN_HIGH) &
            (player_data['L10_STD_MIN'] >= PORTFOLIO_STD_MIN)
        ].copy()

        logger.info(
            f"Portafolio: {len(valid_bets)} actuaciones de bench players "
            f"({PORTFOLIO_MIN_LOW}-{PORTFOLIO_MIN_HIGH} min, "
            f"L10_STD_MIN >= {PORTFOLIO_STD_MIN})"
        )

        stat_to_test = 'REB'
        skipped_no_gs = 0

        for _, row in valid_bets.iterrows():
            game_id   = row['GAME_ID']
            team_id   = row['TEAM_ID']

            gs = game_scripts.get(game_id)
            if gs is None:
                skipped_no_gs += 1
                continue

            # Signo correcto: margen positivo = ventaja para el equipo del jugador
            if team_id == gs['home_team_id']:
                predicted_margin = gs['predicted_margin']
            else:
                predicted_margin = -gs['predicted_margin']

            stats_context = {
                'L10_MIN': row['L10_MIN'],
                'L10_REB': row['L10_REB'],
                'L10_AST': row['L10_AST'],
                'L10_PTS': row['L10_PTS'],
            }

            # MinutesProjector con el margen predicho por el modelo Moneyline
            proj_min = self.minutes_projector.project_minutes(
                stats_context, game_script_margin=predicted_margin
            )

            expected_val = self.props_model.predict_stat(stat_to_test, proj_min, stats_context)

            # Línea proxy: L10 + 0.5
            # TODO sprint siguiente: reemplazar con líneas reales de The-Odds-API
            line = row[f'L10_{stat_to_test}'] + 0.5
            odds = 1.90

            player_std = row.get(f'L10_STD_{stat_to_test}')
            prob_over  = self.props_model.calculate_prob_over(
                expected_val, line, stat_to_test, player_std=player_std
            )
            ev = self.props_model.calculate_ev(prob_over, odds)

            if ev > self.min_ev:
                actual_val = row[stat_to_test]
                is_win = actual_val > line

                kelly_pct = self._kelly(prob_over, odds)
                stake = self.current_bankroll * kelly_pct

                if stake > 0:
                    profit = stake * (odds - 1) if is_win else -stake
                    self.current_bankroll += profit

                    self.bet_history.append({
                        'date':             row['GAME_DATE'],
                        'player':           row['PLAYER_NAME'],
                        'stat':             stat_to_test,
                        'line':             line,
                        'expected':         expected_val,
                        'actual':           actual_val,
                        'real_margin':      row['GAME_MARGIN'],
                        'predicted_margin': predicted_margin,
                        'prob_home_ml':     gs['prob_home'],
                        'proj_min':         proj_min,
                        'player_std':       player_std,
                        'prob':             prob_over,
                        'ev':               ev,
                        'stake':            stake,
                        'profit':           profit,
                        'bankroll':         self.current_bankroll,
                    })

        if skipped_no_gs:
            logger.warning(f"Saltados {skipped_no_gs} rows sin game script (juegos sin datos suficientes).")

    # ------------------------------------------------------------------
    # Reporte
    # ------------------------------------------------------------------

    def report(self):
        if not self.bet_history:
            print("Sin apuestas con EV positivo en el periodo.")
            return

        df = pd.DataFrame(self.bet_history)
        n      = len(df)
        wins   = (df['profit'] > 0).sum()
        wr     = wins / n
        staked = df['stake'].sum()
        profit = self.current_bankroll - self.initial_bankroll
        roi    = profit / staked * 100

        print("\n" + "=" * 55)
        print("BACKTEST PLAYER PROPS V2 — Moneyline Game Script 2025-26")
        print("=" * 55)
        print(f"Periodo  : {df['date'].min()} → {df['date'].max()}")
        print(f"Banca    : ${self.initial_bankroll:.0f} → ${self.current_bankroll:.2f}  "
              f"({profit:+.2f})")
        print(f"ROI      : {roi:.2f}%")
        print(f"Apuestas : {n}  |  Win rate: {wr:.2%}  (break-even: 52.63%)")
        print(f"W/L      : {wins}/{n - wins}")
        print("-" * 55)

        # Desglose por intensidad del margen predicho
        df['margin_bucket'] = pd.cut(
            df['predicted_margin'].abs(),
            bins=[0, 5, 10, 15, 50],
            labels=['0-5 (coin flip)', '5-10', '10-15', '>15 (blowout)']
        )
        print("\nWin rate por margen predicho:")
        print(
            df.groupby('margin_bucket', observed=True)
            .agg(n=('profit', 'count'),
                 wr=('profit', lambda x: f"{(x > 0).mean():.1%}"),
                 roi=('profit', lambda x: f"{x.sum() / df.loc[x.index,'stake'].sum() * 100:.1f}%"))
            .to_string()
        )

        print("=" * 55)

        os.makedirs("data/results", exist_ok=True)
        out = "data/results/backtest_props_2026_results.csv"
        df.to_csv(out, index=False)
        print(f"Resultados en {out}")


if __name__ == "__main__":
    backtester = PropsBacktester()
    backtester.run_backtest()
    backtester.report()
