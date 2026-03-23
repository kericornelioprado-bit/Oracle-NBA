import pytest
import pandas as pd
import numpy as np
from src.data.feature_engineering import NBAFeatureEngineer


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_two_team_df():
    """Dataset con 2 equipos y juegos de local y visitante."""
    data = []
    game_id = 1
    for i in range(8):
        # Equipo 1 vs Equipo 2
        data.append({
            'TEAM_ID': 1,
            'GAME_ID': str(game_id),
            'GAME_DATE': pd.Timestamp('2023-01-01') + pd.Timedelta(days=i * 2),
            'PTS': 100 + i,
            'FG_PCT': 0.45 + i * 0.01,
            'FG3_PCT': 0.35,
            'FT_PCT': 0.75,
            'AST': 25,
            'REB': 44,
            'TOV': 14,
            'PLUS_MINUS': float(i),
            'MATCHUP': 'T1 vs. T2',
            'WL': 'W' if i % 2 == 0 else 'L',
        })
        data.append({
            'TEAM_ID': 2,
            'GAME_ID': str(game_id),
            'GAME_DATE': pd.Timestamp('2023-01-01') + pd.Timedelta(days=i * 2),
            'PTS': 98 + i,
            'FG_PCT': 0.43 + i * 0.01,
            'FG3_PCT': 0.33,
            'FT_PCT': 0.73,
            'AST': 23,
            'REB': 42,
            'TOV': 15,
            'PLUS_MINUS': float(-i),
            'MATCHUP': 'T2 @ T1',
            'WL': 'L' if i % 2 == 0 else 'W',
        })
        game_id += 1
    return pd.DataFrame(data)


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_structure_for_modeling_shape(make_two_team_df=None):
    """structure_for_modeling debe producir 1 fila por partido."""
    engineer = NBAFeatureEngineer()
    df = make_two_team_df() if make_two_team_df else None
    if df is None:
        # Crear datos propios
        df = make_two_team_df.__class__ and None
    # Usar la función directamente
    df = pd.DataFrame([
        {'TEAM_ID': 1, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 100, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'AST': 25,
         'REB': 44, 'TOV': 14, 'PLUS_MINUS': 5.0, 'MATCHUP': 'T1 vs. T2', 'WL': 'W'},
        {'TEAM_ID': 2, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 95, 'FG_PCT': 0.42, 'FG3_PCT': 0.33, 'FT_PCT': 0.73, 'AST': 23,
         'REB': 42, 'TOV': 15, 'PLUS_MINUS': -5.0, 'MATCHUP': 'T2 @ T1', 'WL': 'L'},
        {'TEAM_ID': 1, 'GAME_ID': '2', 'GAME_DATE': pd.Timestamp('2023-01-03'),
         'PTS': 105, 'FG_PCT': 0.46, 'FG3_PCT': 0.36, 'FT_PCT': 0.76, 'AST': 26,
         'REB': 45, 'TOV': 13, 'PLUS_MINUS': 8.0, 'MATCHUP': 'T1 vs. T2', 'WL': 'L'},
        {'TEAM_ID': 2, 'GAME_ID': '2', 'GAME_DATE': pd.Timestamp('2023-01-03'),
         'PTS': 110, 'FG_PCT': 0.44, 'FG3_PCT': 0.34, 'FT_PCT': 0.74, 'AST': 24,
         'REB': 43, 'TOV': 14, 'PLUS_MINUS': -8.0, 'MATCHUP': 'T2 @ T1', 'WL': 'W'},
    ])
    df = engineer.create_rolling_features(df, windows=[3])
    df = engineer.calculate_rest_days(df)
    result = engineer.structure_for_modeling(df)
    assert len(result) == 2  # 2 partidos → 2 filas


def test_structure_for_modeling_columns():
    """El dataset estructurado debe tener columnas HOME_ y AWAY_."""
    engineer = NBAFeatureEngineer()
    df = pd.DataFrame([
        {'TEAM_ID': 1, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 100, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'AST': 25,
         'REB': 44, 'TOV': 14, 'PLUS_MINUS': 5.0, 'MATCHUP': 'T1 vs. T2', 'WL': 'W'},
        {'TEAM_ID': 2, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 95, 'FG_PCT': 0.42, 'FG3_PCT': 0.33, 'FT_PCT': 0.73, 'AST': 23,
         'REB': 42, 'TOV': 15, 'PLUS_MINUS': -5.0, 'MATCHUP': 'T2 @ T1', 'WL': 'L'},
    ])
    df = engineer.create_rolling_features(df, windows=[3])
    df = engineer.calculate_rest_days(df)
    result = engineer.structure_for_modeling(df)

    assert 'TARGET' in result.columns
    home_cols = [c for c in result.columns if c.startswith('HOME_')]
    away_cols = [c for c in result.columns if c.startswith('AWAY_')]
    assert len(home_cols) > 0
    assert len(away_cols) > 0


def test_structure_for_modeling_target_encoding():
    """TARGET debe ser 1 si ganó el local, 0 si ganó el visitante."""
    engineer = NBAFeatureEngineer()
    df = pd.DataFrame([
        {'TEAM_ID': 1, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 100, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75, 'AST': 25,
         'REB': 44, 'TOV': 14, 'PLUS_MINUS': 5.0, 'MATCHUP': 'T1 vs. T2', 'WL': 'W'},
        {'TEAM_ID': 2, 'GAME_ID': '1', 'GAME_DATE': pd.Timestamp('2023-01-01'),
         'PTS': 95, 'FG_PCT': 0.42, 'FG3_PCT': 0.33, 'FT_PCT': 0.73, 'AST': 23,
         'REB': 42, 'TOV': 15, 'PLUS_MINUS': -5.0, 'MATCHUP': 'T2 @ T1', 'WL': 'L'},
    ])
    df = engineer.create_rolling_features(df, windows=[3])
    df = engineer.calculate_rest_days(df)
    result = engineer.structure_for_modeling(df)
    # Equipo 1 es local y ganó (WL='W') → TARGET = 1
    assert result.iloc[0]['TARGET'] == 1


def test_load_data_mocked(tmp_path):
    """load_data debe leer parquet y convertir GAME_DATE a datetime."""
    df = pd.DataFrame({
        'TEAM_ID': [1, 2],
        'GAME_DATE': ['2023-01-01', '2023-01-02'],
        'PTS': [100, 110],
    })
    parquet_path = tmp_path / "nba_games_raw.parquet"
    df.to_parquet(parquet_path, index=False)

    engineer = NBAFeatureEngineer(input_path=str(parquet_path))
    result = engineer.load_data()

    assert pd.api.types.is_datetime64_any_dtype(result['GAME_DATE'])
    assert len(result) == 2


def test_run_pipeline_full(tmp_path):
    """run() debe ejecutar el pipeline completo y guardar el parquet de salida."""
    # Crear datos de entrada con estructura correcta para el pipeline
    rows = []
    game_id = 1
    for i in range(10):
        rows.extend([
            {'TEAM_ID': 1, 'GAME_ID': str(game_id),
             'GAME_DATE': (pd.Timestamp('2023-01-01') + pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
             'PTS': 100 + i, 'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.75,
             'AST': 25, 'REB': 44, 'TOV': 14, 'PLUS_MINUS': float(i),
             'MATCHUP': 'T1 vs. T2', 'WL': 'W' if i % 2 == 0 else 'L'},
            {'TEAM_ID': 2, 'GAME_ID': str(game_id),
             'GAME_DATE': (pd.Timestamp('2023-01-01') + pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
             'PTS': 98 + i, 'FG_PCT': 0.43, 'FG3_PCT': 0.33, 'FT_PCT': 0.73,
             'AST': 23, 'REB': 42, 'TOV': 15, 'PLUS_MINUS': float(-i),
             'MATCHUP': 'T2 @ T1', 'WL': 'L' if i % 2 == 0 else 'W'},
        ])
        game_id += 1

    input_path = tmp_path / "nba_games_raw.parquet"
    output_path = tmp_path / "nba_games_features.parquet"
    pd.DataFrame(rows).to_parquet(input_path, index=False)

    engineer = NBAFeatureEngineer(
        input_path=str(input_path),
        output_path=str(output_path)
    )
    result = engineer.run()

    assert result is not None
    assert output_path.exists()
    assert 'TARGET' in result.columns


def test_rest_days_clipped_at_10():
    """Los días de descanso deben estar capped en 10."""
    engineer = NBAFeatureEngineer()
    df = pd.DataFrame({
        'TEAM_ID': [1, 1],
        'GAME_DATE': pd.to_datetime(['2023-01-01', '2023-01-20']),  # 19 días de diferencia
        'PTS': [100, 110],
        'FG_PCT': [0.45, 0.46],
        'FG3_PCT': [0.35, 0.36],
        'FT_PCT': [0.75, 0.76],
        'AST': [25, 26], 'REB': [44, 45], 'TOV': [14, 13], 'PLUS_MINUS': [5.0, 6.0],
        'MATCHUP': ['T1 vs. T2', 'T1 vs. T2'], 'WL': ['W', 'L'],
    })
    result = engineer.calculate_rest_days(df)
    # 19 días debe estar capped en 10
    assert result['DAYS_REST'].max() <= 10


def test_rolling_features_no_data_leakage():
    """El shift(1) garantiza que no hay data leakage: la fila i no ve sus propios datos."""
    engineer = NBAFeatureEngineer()
    df = pd.DataFrame({
        'TEAM_ID': [1] * 5,
        'GAME_DATE': pd.to_datetime(['2023-01-01', '2023-01-03', '2023-01-05',
                                      '2023-01-07', '2023-01-10']),
        'PTS': [100.0, 110.0, 120.0, 130.0, 140.0],
        'FG_PCT': [0.4] * 5, 'FG3_PCT': [0.3] * 5, 'FT_PCT': [0.7] * 5,
        'AST': [20.0] * 5, 'REB': [40.0] * 5, 'TOV': [10.0] * 5, 'PLUS_MINUS': [5.0] * 5,
    })
    result = engineer.create_rolling_features(df, windows=[3])
    # La fila 3 (índice 3) debe tener promedio de las 3 anteriores (100+110+120)/3=110
    assert result['ROLL_PTS_3'].iloc[3] == pytest.approx(110.0)
    # Las primeras filas deben ser NaN (no hay suficiente historia)
    assert pd.isna(result['ROLL_PTS_3'].iloc[0])
