import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.data.player_ingestion import PlayerStatsIngestion


@pytest.fixture
def ingestion():
    with patch('src.data.player_ingestion.BallDontLieClient') as mock_bdl_cls:
        mock_bdl = MagicMock()
        mock_bdl_cls.return_value = mock_bdl
        obj = PlayerStatsIngestion(season=2024)
        obj.mock_bdl = mock_bdl
        return obj


def make_raw_logs_df(n_players=2, n_games=12):
    """Genera un DataFrame de logs de jugadores similar al de BDL."""
    rows = []
    for player_id in range(1, n_players + 1):
        for i in range(n_games):
            rows.append({
                'PLAYER_ID': player_id,
                'PLAYER_NAME': f'Player {player_id}',
                'GAME_DATE': f'2024-01-{i+1:02d}T00:00:00',
                'MIN': f'{20 + player_id}:30',
                'PTS': 10 + i,
                'REB': 5 + (i % 3),
                'AST': 3 + (i % 2),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# _parse_minutes                                                               #
# --------------------------------------------------------------------------- #

def test_parse_minutes_mm_ss_format(ingestion):
    """Convierte '28:30' → 28 + 30/60 ≈ 28.5."""
    result = ingestion._parse_minutes('28:30')
    assert result == pytest.approx(28.5)


def test_parse_minutes_exact_zero_seconds(ingestion):
    """'30:00' debe devolver exactamente 30.0."""
    result = ingestion._parse_minutes('30:00')
    assert result == pytest.approx(30.0)


def test_parse_minutes_float_string(ingestion):
    """Si ya viene como string float '28.5', debe devolver 28.5."""
    result = ingestion._parse_minutes('28.5')
    assert result == pytest.approx(28.5)


def test_parse_minutes_empty_string(ingestion):
    """Cadena vacía devuelve 0.0."""
    result = ingestion._parse_minutes('')
    assert result == 0.0


def test_parse_minutes_nan(ingestion):
    """Valor NaN de pandas devuelve 0.0."""
    result = ingestion._parse_minutes(float('nan'))
    assert result == 0.0


def test_parse_minutes_invalid_format(ingestion):
    """Formato inválido devuelve 0.0 sin lanzar excepción."""
    result = ingestion._parse_minutes('invalid')
    assert result == 0.0


# --------------------------------------------------------------------------- #
# get_player_logs                                                               #
# --------------------------------------------------------------------------- #

def test_get_player_logs_returns_dataframe(ingestion):
    """Cuando la API responde correctamente, devuelve un DataFrame no vacío."""
    raw_df = make_raw_logs_df(n_players=2, n_games=5)
    ingestion.mock_bdl.get_player_stats.return_value = raw_df

    result = ingestion.get_player_logs()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(raw_df)


def test_get_player_logs_filters_by_player_ids(ingestion):
    """Filtra el DataFrame a los player_ids especificados."""
    raw_df = make_raw_logs_df(n_players=3, n_games=5)
    ingestion.mock_bdl.get_player_stats.return_value = raw_df

    result = ingestion.get_player_logs(player_ids=[1, 2])
    ingestion.mock_bdl.get_player_stats.assert_called_with(seasons=[2024], player_ids=[1, 2])


def test_get_player_logs_sorted_by_player_and_date(ingestion):
    """El resultado debe estar ordenado por PLAYER_ID y GAME_DATE."""
    raw_df = make_raw_logs_df(n_players=2, n_games=5)
    raw_df = raw_df.sample(frac=1)
    ingestion.mock_bdl.get_player_stats.return_value = raw_df

    result = ingestion.get_player_logs()
    assert result.iloc[0]['PLAYER_ID'] <= result.iloc[-1]['PLAYER_ID']
    assert pd.api.types.is_datetime64_any_dtype(result['GAME_DATE'])


def test_get_player_logs_parses_min_column(ingestion):
    """Las columnas MIN quedan como float después del parseo."""
    raw_df = make_raw_logs_df(n_players=1, n_games=3)
    ingestion.mock_bdl.get_player_stats.return_value = raw_df

    result = ingestion.get_player_logs()
    assert result['MIN'].dtype in [float, 'float64']


def test_get_player_logs_api_error_returns_empty_df(ingestion):
    """Si la API falla, devuelve un DataFrame vacío."""
    ingestion.mock_bdl.get_player_stats.side_effect = Exception("BDL API timeout")

    result = ingestion.get_player_logs()
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# --------------------------------------------------------------------------- #
# Rolling Features & Enrichment                                                #
# --------------------------------------------------------------------------- #

def _make_clean_logs_df(n_players=2, n_games=15):
    """Genera logs con columnas ya limpias (MIN como float)."""
    rows = []
    for player_id in range(1, n_players + 1):
        for i in range(n_games):
            rows.append({
                'PLAYER_ID': player_id,
                'PLAYER_NAME': f'Player {player_id}',
                'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                'MIN': 25.0 + (i % 5),
                'PTS': 15.0 + (i % 10),
                'REB': 7.0 + (i % 4),
                'AST': 4.0 + (i % 3),
                'FGA': 12.0, 'FTA': 5.0,
                'GAME_ID': f'G_{i}', 'TEAM_ID': player_id + 100
            })
    return pd.DataFrame(rows)

def test_calculate_rolling_features(ingestion):
    df = _make_clean_logs_df(n_players=1, n_games=25)
    result = ingestion.calculate_rolling_features(df)
    
    assert 'L10_PTS' in result.columns
    assert 'L10_STD_MIN' in result.columns
    assert not pd.isna(result.iloc[24]['L10_PTS'])

def test_enrich_with_game_context_empty(ingestion):
    df = pd.DataFrame()
    result = ingestion.enrich_with_game_context(df)
    assert 'GAME_MARGIN' in result.columns
    assert result.empty

def test_enrich_with_game_context_missing_cols(ingestion):
    df = pd.DataFrame({'SOMETHING': [1]})
    result = ingestion.enrich_with_game_context(df)
    assert 'GAME_MARGIN' in result.columns
    assert result['GAME_MARGIN'].iloc[0] == 0.0

def test_enrich_with_game_context_success(ingestion):
    df = _make_clean_logs_df(n_players=1, n_games=5)
    mock_games = pd.DataFrame([
        {'GAME_ID': 'G_0', 'TEAM_ID': 101, 'PLUS_MINUS': 10},
        {'GAME_ID': 'G_1', 'TEAM_ID': 101, 'PLUS_MINUS': -5},
    ])
    ingestion.mock_bdl.get_games.return_value = mock_games
    
    result = ingestion.enrich_with_game_context(df)
    assert 'GAME_MARGIN' in result.columns
    assert result.loc[result['GAME_ID'] == 'G_0', 'GAME_MARGIN'].iloc[0] == 10.0
    assert result.loc[result['GAME_ID'] == 'G_1', 'GAME_MARGIN'].iloc[0] == -5.0
    assert result.loc[result['GAME_ID'] == 'G_2', 'GAME_MARGIN'].iloc[0] == 0.0 # No en mock_games

def test_enrich_with_game_context_empty_games_response(ingestion):
    df = _make_clean_logs_df(n_players=1, n_games=5)
    ingestion.mock_bdl.get_games.return_value = pd.DataFrame() # Vacío
    
    result = ingestion.enrich_with_game_context(df)
    assert 'GAME_MARGIN' in result.columns
    assert 'TEAM_L10_MARGIN' in result.columns
    assert (result['GAME_MARGIN'] == 0.0).all()

def test_add_team_rolling_margin_missing_cols(ingestion):
    df = pd.DataFrame({'OTHER': [1, 2, 3]})
    result = ingestion._add_team_rolling_margin(df)
    assert 'TEAM_L10_MARGIN' in result.columns
    assert (result['TEAM_L10_MARGIN'] == 0.0).all()
