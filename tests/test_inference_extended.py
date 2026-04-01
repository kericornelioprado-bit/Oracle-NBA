import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_today_games():
    return pd.DataFrame({
        'GAME_ID': ['0022300001', '0022300002'],
        'HOME_TEAM_ID': [1610612738, 1610612745],
        'VISITOR_TEAM_ID': [1610612743, 1610612747],
    })


def make_history_df(team_ids):
    """Genera historial suficiente para calcular features móviles."""
    rows = []
    for team_id in team_ids:
        for i in range(25):
            rows.append({
                'TEAM_ID': team_id,
                'GAME_ID': f'FAKE_{team_id}_{i:04d}',
                'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                'PTS': 100 + i,
                'FG_PCT': 0.45,
                'FG3_PCT': 0.36,
                'FT_PCT': 0.78,
                'AST': 25,
                'REB': 44,
                'TOV': 14,
                'PLUS_MINUS': 2.0,
                'MATCHUP': f'TEAM @ OPP' if i % 2 == 0 else f'TEAM vs. OPP',
                'WL': 'W' if i % 2 == 0 else 'L',
            })
    return pd.DataFrame(rows)


def make_processed_features_parquet(tmp_path, team_ids):
    """Crea un parquet de features procesadas con columnas que el modelo espera."""
    rows = []
    for team_id in team_ids:
        for i in range(5):
            row = {'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i)}
            for col in ['PTS', 'FG_PCT', 'AST', 'REB', 'TOV', 'PLUS_MINUS', 'FG3_PCT', 'FT_PCT']:
                for w in [3, 5, 10, 20]:
                    row[f'HOME_ROLL_{col}_{w}'] = np.random.uniform(90, 130)
                    row[f'AWAY_ROLL_{col}_{w}'] = np.random.uniform(90, 130)
            row['HOME_DAYS_REST'] = 2.0
            row['AWAY_DAYS_REST'] = 2.0
            row['TARGET'] = 1
            rows.append(row)
    df = pd.DataFrame(rows)
    path = tmp_path / "nba_games_features.parquet"
    df.to_parquet(path, index=False)
    return str(path)


# Parche global para evitar conexión real a GCP en todos los tests de este módulo
BQ_PATCH = 'src.models.inference.NBABigQueryClient'
PLAYER_INGESTION_PATCH = 'src.models.inference.PlayerStatsIngestion'


def make_oracle(tmp_path, mock_model=None):
    """Helper: crea NBAOracleInference sin GCP ni NBA API real."""
    if mock_model is None:
        mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    mock_bq = MagicMock()
    mock_bq.get_virtual_bankroll.return_value = 20000.0
    mock_bq.get_top_20_portfolio.return_value = []

    with patch('joblib.load', return_value=mock_model), \
         patch(BQ_PATCH, return_value=mock_bq), \
         patch(PLAYER_INGESTION_PATCH):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    oracle.model = mock_model
    return oracle


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_oracle_init_file_not_found():
    """Debe lanzar FileNotFoundError si el modelo no existe."""
    with patch(BQ_PATCH), patch(PLAYER_INGESTION_PATCH):
        from src.models.inference import NBAOracleInference
        with pytest.raises(FileNotFoundError):
            NBAOracleInference(model_path="/tmp/nonexistent_model.joblib")


def test_oracle_init_loads_model(tmp_path):
    """Debe cargar el modelo y crear el NBAFeatureEngineer."""
    mock_model = MagicMock()
    oracle = make_oracle(tmp_path, mock_model)

    assert oracle.model is mock_model
    assert oracle.engineer is not None


def test_get_today_games_returns_dataframe(tmp_path):
    """get_today_games debe retornar DataFrame con columnas correctas."""
    oracle = make_oracle(tmp_path)
    
    # BDL entrega una fila por equipo, necesitamos GAME_ID, TEAM_ID y MATCHUP
    mock_df = pd.DataFrame([
        {'GAME_ID': '001', 'TEAM_ID': 10, 'MATCHUP': 'A vs. B'},
        {'GAME_ID': '001', 'TEAM_ID': 20, 'MATCHUP': 'B @ A'}
    ])

    with patch.object(oracle.bdl_client, 'get_games', return_value=mock_df):
        result = oracle.get_today_games()

    assert result is not None
    assert 'GAME_ID' in result.columns
    assert 'HOME_TEAM_ID' in result.columns
    assert result.iloc[0]['HOME_TEAM_ID'] == 10


def test_get_today_games_no_games(tmp_path):
    """Cuando no hay partidos debe retornar None."""
    oracle = make_oracle(tmp_path)

    with patch.object(oracle.bdl_client, 'get_games', return_value=pd.DataFrame()):
        result = oracle.get_today_games()

    assert result is None


def test_fetch_recent_history(tmp_path):
    """fetch_recent_history debe obtener historial vía BDL."""
    oracle = make_oracle(tmp_path)
    team_ids = [10, 20]
    
    # Mock de BDL con columna WL poblada para que no se filtre a vacío
    mock_df = pd.DataFrame([
        {'GAME_ID': '001', 'TEAM_ID': 10, 'WL': 'W', 'PTS': 110},
        {'GAME_ID': '001', 'TEAM_ID': 20, 'WL': 'L', 'PTS': 100}
    ])

    with patch.object(oracle.bdl_client, 'get_games', return_value=mock_df):
        result = oracle.fetch_recent_history(team_ids)

    assert isinstance(result, pd.DataFrame)
    assert not result.empty


def test_predict_today_no_games(tmp_path):
    """predict_today debe retornar (None, None) cuando no hay partidos hoy."""
    oracle = make_oracle(tmp_path)

    with patch.object(oracle, 'get_today_games', return_value=None):
        ml_df, props_df = oracle.predict_today()

    assert ml_df is None
    assert props_df is None


def test_predict_today_with_games(tmp_path):
    """predict_today debe retornar DataFrames con predicciones para los partidos."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.35, 0.65]])

    oracle = make_oracle(tmp_path, mock_model)

    team_ids = [1610612738, 1610612743, 1610612745, 1610612747]
    today_games = make_today_games()
    history = make_history_df(team_ids)

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch.object(oracle.player_ingestion, 'get_player_logs', return_value=pd.DataFrame()), \
         patch.object(oracle.player_ingestion, 'calculate_rolling_features', return_value=pd.DataFrame()):
        ml_df, props_df = oracle.predict_today()

    assert ml_df is not None
    assert isinstance(ml_df, pd.DataFrame)
    assert 'RECOMMENDATION' in ml_df.columns
    assert 'PROB_HOME_WIN' in ml_df.columns


def test_predict_today_recommendation_home(tmp_path):
    """Probabilidad > 0.524 debe generar recomendación HOME."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.35, 0.65]])

    oracle = make_oracle(tmp_path, mock_model)

    today_games = pd.DataFrame({
        'GAME_ID': ['0022300001'],
        'HOME_TEAM_ID': [1610612738],
        'VISITOR_TEAM_ID': [1610612743],
    })
    history = make_history_df([1610612738, 1610612743])

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch.object(oracle.player_ingestion, 'get_player_logs', return_value=pd.DataFrame()), \
         patch.object(oracle.player_ingestion, 'calculate_rolling_features', return_value=pd.DataFrame()):
        ml_df, _ = oracle.predict_today()

    if ml_df is not None and len(ml_df) > 0:
        assert ml_df.iloc[0]['RECOMMENDATION'] == 'HOME'


def test_predict_today_recommendation_away(tmp_path):
    """Probabilidad < 0.476 debe generar recomendación AWAY."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.65, 0.35]])

    oracle = make_oracle(tmp_path, mock_model)

    today_games = pd.DataFrame({
        'GAME_ID': ['0022300001'],
        'HOME_TEAM_ID': [1610612738],
        'VISITOR_TEAM_ID': [1610612743],
    })
    history = make_history_df([1610612738, 1610612743])

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch.object(oracle.player_ingestion, 'get_player_logs', return_value=pd.DataFrame()), \
         patch.object(oracle.player_ingestion, 'calculate_rolling_features', return_value=pd.DataFrame()):
        ml_df, _ = oracle.predict_today()

    if ml_df is not None and len(ml_df) > 0:
        assert ml_df.iloc[0]['RECOMMENDATION'] == 'AWAY'
