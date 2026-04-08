import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

# --------------------------------------------------------------------------- #
# Mocks globales                                                               #
# --------------------------------------------------------------------------- #
BQ_PATCH = 'src.models.inference.NBABigQueryClient'
PLAYER_INGESTION_PATCH = 'src.models.inference.PlayerStatsIngestion'
ODDS_API_PATCH = 'src.models.inference.OddsAPIClient'

@pytest.fixture
def oracle_v2(tmp_path):
    mock_model = MagicMock()
    fake_model_path = tmp_path / "nba_best_model_stacking.joblib"
    fake_model_path.touch()

    mock_bq = MagicMock()
    mock_bq.get_virtual_bankroll.return_value = 20000.0
    mock_bq.get_top_20_portfolio.return_value = [1, 2]

    with patch('joblib.load', return_value=mock_model), \
         patch(BQ_PATCH, return_value=mock_bq), \
         patch(PLAYER_INGESTION_PATCH), \
         patch(ODDS_API_PATCH):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))
        oracle.bq_client = mock_bq
        return oracle

def test_calculate_kelly(oracle_v2):
    oracle_v2.kelly_fraction = 0.25
    assert oracle_v2.calculate_kelly(0.6, 2.0) == pytest.approx(0.05)
    assert oracle_v2.calculate_kelly(0.4, 2.0) == 0.0

def test_predict_today_full_flow(oracle_v2):
    # Mock ML
    oracle_v2.get_today_games = MagicMock(return_value=pd.DataFrame([
        {'GAME_ID': 'G1', 'HOME_TEAM_ID': 10, 'VISITOR_TEAM_ID': 20}
    ]))
    # Necesitamos columnas de stats para create_rolling_features
    history_df = pd.DataFrame([
        {'TEAM_ID': 10, 'GAME_ID': 'OLD', 'WL': 'W', 'GAME_DATE': '2023-12-31', 'PTS': 110, 'REB': 45, 'AST': 25, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'TOV': 12, 'PLUS_MINUS': 5},
        {'TEAM_ID': 20, 'GAME_ID': 'OLD2', 'WL': 'L', 'GAME_DATE': '2023-12-31', 'PTS': 100, 'REB': 40, 'AST': 20, 'FG_PCT': 0.40, 'FG3_PCT': 0.30, 'FT_PCT': 0.70, 'TOV': 15, 'PLUS_MINUS': -5}
    ])
    oracle_v2.fetch_recent_history = MagicMock(return_value=history_df)
    
    oracle_v2.engineer.generate_inference_data = MagicMock(return_value=pd.DataFrame([{
        'HOME_ROLL_PTS_3': 110, 'AWAY_ROLL_PTS_3': 105,
    }]))
    oracle_v2.model.predict_proba = MagicMock(return_value=np.array([[0.4, 0.6]]))

    # Mock Props
    oracle_v2.top_20_ids = [1]
    mock_logs = pd.DataFrame([
        {'PLAYER_ID': 1, 'PLAYER_NAME': 'LeBron James', 'PTS': 25, 'MIN': 35, 'GAME_DATE': '2024-01-01', 'L10_STD_PTS': 5.0}
    ])
    oracle_v2.player_ingestion.get_player_logs.return_value = mock_logs
    oracle_v2.player_ingestion.calculate_rolling_features.return_value = mock_logs
    
    # Mock consolidado que espera inference.py V2
    oracle_v2.odds_client.get_all_player_props_today.return_value = {
        'lebron james': {
            'PTS': {'line': 24.5, 'odds': 1.90, 'bookmaker': 'DK'}
        }
    }
    
    # Mocking methods of the component objects
    oracle_v2.minutes_projector.project_minutes = MagicMock(return_value=36.0)
    oracle_v2.props_model.predict_stat = MagicMock(return_value=28.0)
    oracle_v2.props_model.calculate_prob_over = MagicMock(return_value=0.70)
    oracle_v2.props_model.calculate_ev = MagicMock(return_value=0.33)

    ml_df, props_df = oracle_v2.predict_today()
    assert not ml_df.empty
    assert not props_df.empty
    oracle_v2.bq_client.insert_prop_bets.assert_called_once()

def test_predict_today_no_props_data(oracle_v2):
    oracle_v2.get_today_games = MagicMock(return_value=pd.DataFrame([
        {'GAME_ID': 'G1', 'HOME_TEAM_ID': 10, 'VISITOR_TEAM_ID': 20}
    ]))
    history_df = pd.DataFrame([
        {'TEAM_ID': 10, 'GAME_ID': 'OLD', 'WL': 'W', 'GAME_DATE': '2023-12-31', 'PTS': 110, 'REB': 45, 'AST': 25, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'TOV': 12, 'PLUS_MINUS': 5},
        {'TEAM_ID': 20, 'GAME_ID': 'OLD2', 'WL': 'L', 'GAME_DATE': '2023-12-31', 'PTS': 100, 'REB': 40, 'AST': 20, 'FG_PCT': 0.40, 'FG3_PCT': 0.30, 'FT_PCT': 0.70, 'TOV': 15, 'PLUS_MINUS': -5}
    ])
    oracle_v2.fetch_recent_history = MagicMock(return_value=history_df)
    oracle_v2.engineer.generate_inference_data = MagicMock(return_value=pd.DataFrame([{'HOME_ROLL_PTS_3': 110, 'AWAY_ROLL_PTS_3': 105}]))
    oracle_v2.model.predict_proba = MagicMock(return_value=np.array([[0.4, 0.6]]))
    
    # Props vacíos
    oracle_v2.player_ingestion.get_player_logs.return_value = pd.DataFrame()
    
    ml_df, props_df = oracle_v2.predict_today()
    assert not ml_df.empty
    assert props_df.empty

def test_predict_today_exception(oracle_v2):
    oracle_v2.get_today_games = MagicMock(side_effect=ValueError("Error"))
    with pytest.raises(ValueError):
        oracle_v2.predict_today()


def test_predict_today_wires_real_ml_odds(oracle_v2):
    """get_latest_odds debe ser consultado y las cuotas reales llegan al DataFrame ML."""
    oracle_v2.get_today_games = MagicMock(return_value=pd.DataFrame([
        {'GAME_ID': 'G1', 'HOME_TEAM_ID': 1610612747, 'VISITOR_TEAM_ID': 1610612738}  # Lakers vs Celtics
    ]))
    history_df = pd.DataFrame([
        {'TEAM_ID': 1610612747, 'GAME_ID': 'OLD', 'WL': 'W', 'GAME_DATE': '2023-12-31',
         'PTS': 110, 'REB': 45, 'AST': 25, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'TOV': 12, 'PLUS_MINUS': 5},
        {'TEAM_ID': 1610612738, 'GAME_ID': 'OLD2', 'WL': 'L', 'GAME_DATE': '2023-12-31',
         'PTS': 100, 'REB': 40, 'AST': 20, 'FG_PCT': 0.40, 'FG3_PCT': 0.30, 'FT_PCT': 0.70, 'TOV': 15, 'PLUS_MINUS': -5}
    ])
    oracle_v2.fetch_recent_history = MagicMock(return_value=history_df)
    oracle_v2.model.predict_proba = MagicMock(return_value=np.array([[0.35, 0.65]]))

    # Real odds from The Odds API
    oracle_v2.odds_client.get_latest_odds.return_value = [{
        'home_team': 'Los Angeles Lakers',
        'bookmakers': [{
            'title': 'Pinnacle',
            'markets': [{'key': 'h2h', 'outcomes': [
                {'name': 'Los Angeles Lakers', 'price': 1.85},
                {'name': 'Boston Celtics', 'price': 2.05},
            ]}]
        }]
    }]
    oracle_v2.odds_client.get_all_player_props_today.return_value = {}

    ml_df, props_df = oracle_v2.predict_today()

    oracle_v2.odds_client.get_latest_odds.assert_called_once()
    assert not ml_df.empty
    row = ml_df.iloc[0]
    assert row['ODDS'] == pytest.approx(1.85)
    assert row['BOOKMAKER'] == 'Pinnacle'
    assert row['EV'] > 0.0
    assert row['KELLY_PCT'] > 0.0
    assert row['UNITS_SUGGESTED'] > 0.0
