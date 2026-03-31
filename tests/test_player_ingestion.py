import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.data.player_ingestion import PlayerStatsIngestion


@pytest.fixture
def ingestion():
    return PlayerStatsIngestion(season='2024-25')


def make_raw_logs_df(n_players=2, n_games=12):
    """Genera un DataFrame de logs de jugadores similar al de nba_api."""
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

    with patch('src.data.player_ingestion.playergamelogs.PlayerGameLogs') as mock_api:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [raw_df]
        mock_api.return_value = mock_instance

        result = ingestion.get_player_logs()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(raw_df)


def test_get_player_logs_filters_by_player_ids(ingestion):
    """Filtra el DataFrame a los player_ids especificados."""
    raw_df = make_raw_logs_df(n_players=3, n_games=5)

    with patch('src.data.player_ingestion.playergamelogs.PlayerGameLogs') as mock_api:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [raw_df]
        mock_api.return_value = mock_instance

        result = ingestion.get_player_logs(player_ids=[1, 2])

    assert set(result['PLAYER_ID'].unique()) == {1, 2}


def test_get_player_logs_sorted_by_player_and_date(ingestion):
    """El resultado debe estar ordenado por PLAYER_ID y GAME_DATE."""
    raw_df = make_raw_logs_df(n_players=2, n_games=5)

    with patch('src.data.player_ingestion.playergamelogs.PlayerGameLogs') as mock_api:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [raw_df]
        mock_api.return_value = mock_instance

        result = ingestion.get_player_logs()

    sorted_result = result.sort_values(['PLAYER_ID', 'GAME_DATE'])
    pd.testing.assert_frame_equal(result.reset_index(drop=True), sorted_result.reset_index(drop=True))


def test_get_player_logs_parses_min_column(ingestion):
    """Las columnas MIN quedan como float después del parseo."""
    raw_df = make_raw_logs_df(n_players=1, n_games=3)

    with patch('src.data.player_ingestion.playergamelogs.PlayerGameLogs') as mock_api:
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [raw_df]
        mock_api.return_value = mock_instance

        result = ingestion.get_player_logs()

    assert result['MIN'].dtype in [float, 'float64']


def test_get_player_logs_api_error_returns_empty_df(ingestion):
    """Si la API falla, devuelve un DataFrame vacío."""
    with patch('src.data.player_ingestion.playergamelogs.PlayerGameLogs') as mock_api:
        mock_api.side_effect = Exception("NBA API timeout")

        result = ingestion.get_player_logs()

    assert isinstance(result, pd.DataFrame)
    assert result.empty


# --------------------------------------------------------------------------- #
# calculate_rolling_features                                                   #
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
                'MIN': 28.0 + player_id,
                'PTS': 15.0 + i % 5,
                'REB': 6.0 + i % 3,
                'AST': 4.0 + i % 2,
            })
    return pd.DataFrame(rows)


def test_calculate_rolling_features_adds_l10_columns(ingestion):
    """Debe agregar columnas L10_MIN, L10_REB, L10_AST, L10_PTS."""
    df = _make_clean_logs_df()
    result = ingestion.calculate_rolling_features(df)
    for col in ['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']:
        assert col in result.columns


def test_calculate_rolling_features_no_nans(ingestion):
    """Después del cálculo, no deben quedar NaN en las columnas L10."""
    df = _make_clean_logs_df()
    result = ingestion.calculate_rolling_features(df)
    l10_cols = ['L10_MIN', 'L10_REB', 'L10_AST', 'L10_PTS']
    assert result[l10_cols].isna().sum().sum() == 0


def test_calculate_rolling_features_empty_df(ingestion):
    """DataFrame vacío devuelve DataFrame vacío sin error."""
    result = ingestion.calculate_rolling_features(pd.DataFrame())
    assert result.empty


def test_calculate_rolling_features_no_data_leakage(ingestion):
    """El juego actual NO debe incluirse en su propio L10 (shift(1))."""
    df = _make_clean_logs_df(n_players=1, n_games=5)
    result = ingestion.calculate_rolling_features(df)

    # El primer juego de cada jugador no tiene historial previo → L10 = 0.0
    first_game = result[result['PLAYER_ID'] == 1].iloc[0]
    assert first_game['L10_MIN'] == 0.0


def test_calculate_rolling_features_independent_per_player(ingestion):
    """Los rolling features de un jugador no se contaminan con los de otro."""
    df = _make_clean_logs_df(n_players=2, n_games=12)
    result = ingestion.calculate_rolling_features(df)

    p1_l10 = result[result['PLAYER_ID'] == 1]['L10_MIN'].dropna()
    p2_l10 = result[result['PLAYER_ID'] == 2]['L10_MIN'].dropna()

    # Player 1 tiene MIN=29, Player 2 tiene MIN=30. Los promedios deben diferir.
    assert not p1_l10.equals(p2_l10)


# --------------------------------------------------------------------------- #
# calculate_rolling_features — columnas L10_STD                               #
# --------------------------------------------------------------------------- #

def test_calculate_rolling_features_adds_std_columns(ingestion):
    """Debe agregar columnas L10_STD_MIN, L10_STD_REB, L10_STD_AST, L10_STD_PTS."""
    df = _make_clean_logs_df()
    result = ingestion.calculate_rolling_features(df)
    for col in ['L10_STD_MIN', 'L10_STD_REB', 'L10_STD_AST', 'L10_STD_PTS']:
        assert col in result.columns, f"Columna {col} no encontrada"


def test_calculate_rolling_features_std_no_nans(ingestion):
    """Las columnas L10_STD no deben tener NaN (fallback a DEFAULT_STD)."""
    df = _make_clean_logs_df()
    result = ingestion.calculate_rolling_features(df)
    std_cols = ['L10_STD_MIN', 'L10_STD_REB', 'L10_STD_AST', 'L10_STD_PTS']
    assert result[std_cols].isna().sum().sum() == 0


def test_calculate_rolling_features_std_nonnegative(ingestion):
    """La desviación estándar siempre debe ser >= 0."""
    df = _make_clean_logs_df(n_players=3, n_games=15)
    result = ingestion.calculate_rolling_features(df)
    for col in ['L10_STD_REB', 'L10_STD_AST', 'L10_STD_PTS']:
        assert (result[col] >= 0).all(), f"{col} tiene valores negativos"


def test_calculate_rolling_features_std_uses_default_when_insufficient_history(ingestion):
    """Con < 3 juegos de historial, L10_STD_REB usa el fallback (2.5)."""
    df = _make_clean_logs_df(n_players=1, n_games=4)
    result = ingestion.calculate_rolling_features(df)
    # Primer juego: sin historial → L10_STD_REB debe ser el default 2.5
    first_row = result[result['PLAYER_ID'] == 1].iloc[0]
    assert first_row['L10_STD_REB'] == pytest.approx(2.5)


def test_calculate_rolling_features_std_antileakage(ingestion):
    """El juego actual NO debe incluirse en su propia std (shift(1))."""
    # Construimos un jugador con stats constantes para que std sea 0 cuando hay historial
    rows = [
        {'PLAYER_ID': 1, 'PLAYER_NAME': 'P1', 'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
         'MIN': 25.0, 'PTS': 10.0, 'REB': 5.0, 'AST': 3.0}
        for i in range(15)
    ]
    df = pd.DataFrame(rows)
    result = ingestion.calculate_rolling_features(df)

    # A partir del juego 4 (índice 3), hay ≥ 3 juegos previos con REB=5 constante → std=0
    late_games = result.iloc[4:]
    assert (late_games['L10_STD_REB'] < 1e-9).all(), (
        "Jugador con REB constante debería tener L10_STD_REB=0 con historial suficiente"
    )


def test_calculate_rolling_features_std_per_player_independent(ingestion):
    """La std de un jugador no se contamina con la de otro."""
    # Player 1: REB muy variable (0, 10, 0, 10, ...)
    # Player 2: REB constante (5, 5, 5, ...)
    rows = []
    for i in range(15):
        rows.append({'PLAYER_ID': 1, 'PLAYER_NAME': 'P1',
                     'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                     'MIN': 25.0, 'PTS': 10.0, 'REB': float(i % 2) * 10, 'AST': 3.0})
        rows.append({'PLAYER_ID': 2, 'PLAYER_NAME': 'P2',
                     'GAME_DATE': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                     'MIN': 25.0, 'PTS': 10.0, 'REB': 5.0, 'AST': 3.0})
    df = pd.DataFrame(rows)
    result = ingestion.calculate_rolling_features(df)

    # Con historial suficiente: std del jugador variable > std del jugador constante
    p1_std = result[(result['PLAYER_ID'] == 1)].iloc[5:]['L10_STD_REB'].mean()
    p2_std = result[(result['PLAYER_ID'] == 2)].iloc[5:]['L10_STD_REB'].mean()
    assert p1_std > p2_std, (
        f"Jugador variable (std={p1_std:.2f}) debería tener mayor std que jugador constante (std={p2_std:.2f})"
    )


# --------------------------------------------------------------------------- #
# enrich_with_game_context                                                     #
# --------------------------------------------------------------------------- #

def _make_player_df_with_ids():
    """Player logs con GAME_ID y TEAM_ID para tests de enriquecimiento."""
    return pd.DataFrame([
        {'PLAYER_ID': 1, 'PLAYER_NAME': 'P1', 'TEAM_ID': 10,
         'GAME_ID': 'G1', 'GAME_DATE': '2024-01-01',
         'MIN': 25.0, 'REB': 7.0, 'AST': 3.0, 'PTS': 15.0},
        {'PLAYER_ID': 1, 'PLAYER_NAME': 'P1', 'TEAM_ID': 10,
         'GAME_ID': 'G2', 'GAME_DATE': '2024-01-03',
         'MIN': 20.0, 'REB': 5.0, 'AST': 2.0, 'PTS': 12.0},
        {'PLAYER_ID': 2, 'PLAYER_NAME': 'P2', 'TEAM_ID': 20,
         'GAME_ID': 'G1', 'GAME_DATE': '2024-01-01',
         'MIN': 22.0, 'REB': 4.0, 'AST': 6.0, 'PTS': 10.0},
    ])


def _make_games_df():
    """Games df con PLUS_MINUS por equipo (formato BDL client)."""
    return pd.DataFrame([
        {'GAME_ID': 'G1', 'TEAM_ID': 10, 'PLUS_MINUS': 18.0, 'GAME_DATE': '2024-01-01'},
        {'GAME_ID': 'G1', 'TEAM_ID': 20, 'PLUS_MINUS': -18.0, 'GAME_DATE': '2024-01-01'},
        {'GAME_ID': 'G2', 'TEAM_ID': 10, 'PLUS_MINUS': -5.0, 'GAME_DATE': '2024-01-03'},
        {'GAME_ID': 'G2', 'TEAM_ID': 20, 'PLUS_MINUS': 5.0, 'GAME_DATE': '2024-01-03'},
    ])


def test_enrich_with_game_context_adds_game_margin(ingestion):
    """GAME_MARGIN debe reflejar el PLUS_MINUS del equipo del jugador."""
    player_df = _make_player_df_with_ids()
    games_df = _make_games_df()

    with patch.object(ingestion.bdl_client, 'get_games', return_value=games_df):
        result = ingestion.enrich_with_game_context(player_df)

    p1_g1 = result[(result['PLAYER_ID'] == 1) & (result['GAME_ID'] == 'G1')].iloc[0]
    p2_g1 = result[(result['PLAYER_ID'] == 2) & (result['GAME_ID'] == 'G1')].iloc[0]

    assert p1_g1['GAME_MARGIN'] == pytest.approx(18.0)
    assert p2_g1['GAME_MARGIN'] == pytest.approx(-18.0)


def test_enrich_with_game_context_no_nans_on_game_margin(ingestion):
    """GAME_MARGIN no debe tener NaN (fillna(0) si no hay match)."""
    player_df = _make_player_df_with_ids()
    games_df = _make_games_df()

    with patch.object(ingestion.bdl_client, 'get_games', return_value=games_df):
        result = ingestion.enrich_with_game_context(player_df)

    assert result['GAME_MARGIN'].isna().sum() == 0


def test_enrich_with_game_context_adds_team_l10_margin(ingestion):
    """Debe agregar columna TEAM_L10_MARGIN (Game Script previo del equipo)."""
    player_df = _make_player_df_with_ids()
    games_df = _make_games_df()

    with patch.object(ingestion.bdl_client, 'get_games', return_value=games_df):
        result = ingestion.enrich_with_game_context(player_df)

    assert 'TEAM_L10_MARGIN' in result.columns
    assert result['TEAM_L10_MARGIN'].isna().sum() == 0


def test_enrich_with_game_context_team_l10_antileakage(ingestion):
    """
    TEAM_L10_MARGIN del primer juego del equipo debe ser 0
    (no hay historial previo — shift(1) anti-leakage).
    """
    player_df = _make_player_df_with_ids()
    games_df = _make_games_df()

    with patch.object(ingestion.bdl_client, 'get_games', return_value=games_df):
        result = ingestion.enrich_with_game_context(player_df)

    # Team 10, juego G1 (primer juego del equipo en los datos) → TEAM_L10_MARGIN = 0
    first_team_game = result[(result['TEAM_ID'] == 10) & (result['GAME_ID'] == 'G1')].iloc[0]
    assert first_team_game['TEAM_L10_MARGIN'] == pytest.approx(0.0)


def test_enrich_with_game_context_empty_games_fallback(ingestion):
    """Si BDL no devuelve juegos, GAME_MARGIN y TEAM_L10_MARGIN deben ser 0."""
    player_df = _make_player_df_with_ids()

    with patch.object(ingestion.bdl_client, 'get_games', return_value=pd.DataFrame()):
        result = ingestion.enrich_with_game_context(player_df)

    assert (result['GAME_MARGIN'] == 0.0).all()
    assert (result['TEAM_L10_MARGIN'] == 0.0).all()


def test_enrich_with_game_context_missing_columns_fallback(ingestion):
    """Si player_df no tiene GAME_ID o TEAM_ID, devuelve 0 sin error."""
    player_df = pd.DataFrame([{'PLAYER_ID': 1, 'MIN': 25.0}])

    result = ingestion.enrich_with_game_context(player_df)

    assert 'GAME_MARGIN' in result.columns
    assert 'TEAM_L10_MARGIN' in result.columns
    assert result['GAME_MARGIN'].iloc[0] == 0.0
