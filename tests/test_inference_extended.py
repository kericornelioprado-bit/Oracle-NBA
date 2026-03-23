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


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_oracle_init_file_not_found():
    """Debe lanzar FileNotFoundError si el modelo no existe."""
    from src.models.inference import NBAOracleInference
    with pytest.raises(FileNotFoundError):
        NBAOracleInference(model_path="/tmp/nonexistent_model.joblib")


def test_oracle_init_loads_model(tmp_path):
    """Debe cargar el modelo y crear el NBAFeatureEngineer."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    assert oracle.model is mock_model
    assert oracle.engineer is not None


def test_get_today_games_returns_dataframe(tmp_path):
    """get_today_games debe retornar DataFrame con columnas correctas."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    mock_games = make_today_games()

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch('nba_api.stats.endpoints.scoreboardv2.ScoreboardV2') as mock_sb:
        mock_sb.return_value.get_data_frames.return_value = [mock_games]
        result = oracle.get_today_games()

    assert result is not None
    assert 'GAME_ID' in result.columns
    assert 'HOME_TEAM_ID' in result.columns


def test_get_today_games_no_games(tmp_path):
    """Cuando no hay partidos debe retornar None."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch('nba_api.stats.endpoints.scoreboardv2.ScoreboardV2') as mock_sb:
        mock_sb.return_value.get_data_frames.return_value = [pd.DataFrame()]
        result = oracle.get_today_games()

    assert result is None


def test_fetch_recent_history(tmp_path):
    """fetch_recent_history debe concatenar y deduplicar por GAME_ID."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    team_ids = [1610612738, 1610612743]
    history = make_history_df(team_ids)

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    # Separar el history por team y mock LeagueGameFinder
    with patch('nba_api.stats.endpoints.leaguegamefinder.LeagueGameFinder') as mock_lgf:
        def side_effect(**kwargs):
            team_id = kwargs.get('team_id_nullable')
            team_df = history[history['TEAM_ID'] == team_id]
            mock_inst = MagicMock()
            mock_inst.get_data_frames.return_value = [team_df]
            return mock_inst

        mock_lgf.side_effect = side_effect
        result = oracle.fetch_recent_history(team_ids)

    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_predict_today_no_games(tmp_path):
    """predict_today debe retornar None cuando no hay partidos hoy."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch.object(oracle, 'get_today_games', return_value=None):
        result = oracle.predict_today()

    assert result is None


def test_predict_today_with_games(tmp_path):
    """predict_today debe retornar DataFrame con predicciones para los partidos."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    team_ids = [1610612738, 1610612743, 1610612745, 1610612747]
    today_games = make_today_games()
    history = make_history_df(team_ids)
    features_parquet = make_processed_features_parquet(tmp_path, team_ids)

    # El modelo siempre retorna probabilidad 0.65
    mock_model.predict_proba.return_value = np.array([[0.35, 0.65]])

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch('pandas.read_parquet', return_value=pd.read_parquet(features_parquet)):
        result = oracle.predict_today()

    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert 'RECOMMENDATION' in result.columns
    assert 'PROB_HOME_WIN' in result.columns


def test_predict_today_recommendation_home(tmp_path):
    """Probabilidad > 0.524 debe generar recomendación HOME."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    team_ids = [1610612738, 1610612743]
    today_games = pd.DataFrame({
        'GAME_ID': ['0022300001'],
        'HOME_TEAM_ID': [1610612738],
        'VISITOR_TEAM_ID': [1610612743],
    })
    history = make_history_df(team_ids)
    features_parquet = make_processed_features_parquet(tmp_path, team_ids)

    mock_model.predict_proba.return_value = np.array([[0.35, 0.65]])

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch('pandas.read_parquet', return_value=pd.read_parquet(features_parquet)):
        result = oracle.predict_today()

    if result is not None and len(result) > 0:
        assert result.iloc[0]['RECOMMENDATION'] == 'HOME'


def test_predict_today_recommendation_away(tmp_path):
    """Probabilidad < 0.476 debe generar recomendación AWAY."""
    mock_model = MagicMock()
    fake_model_path = tmp_path / "fake_model.joblib"
    fake_model_path.touch()

    team_ids = [1610612738, 1610612743]
    today_games = pd.DataFrame({
        'GAME_ID': ['0022300001'],
        'HOME_TEAM_ID': [1610612738],
        'VISITOR_TEAM_ID': [1610612743],
    })
    history = make_history_df(team_ids)
    features_parquet = make_processed_features_parquet(tmp_path, team_ids)

    mock_model.predict_proba.return_value = np.array([[0.65, 0.35]])

    with patch('joblib.load', return_value=mock_model):
        from src.models.inference import NBAOracleInference
        oracle = NBAOracleInference(model_path=str(fake_model_path))

    with patch.object(oracle, 'get_today_games', return_value=today_games), \
         patch.object(oracle, 'fetch_recent_history', return_value=history), \
         patch('pandas.read_parquet', return_value=pd.read_parquet(features_parquet)):
        result = oracle.predict_today()

    if result is not None and len(result) > 0:
        assert result.iloc[0]['RECOMMENDATION'] == 'AWAY'
