import pytest
import pandas as pd
import numpy as np
from src.data.feature_engineering import NBAFeatureEngineer

@pytest.fixture
def dummy_data():
    """Crea un dataset mínimo para probar la lógica de features."""
    data = {
        'TEAM_ID': [1, 1, 1, 1, 1],
        'GAME_DATE': pd.to_datetime(['2023-01-01', '2023-01-03', '2023-01-05', '2023-01-07', '2023-01-10']),
        'PTS': [100, 110, 120, 130, 140],
        'FG_PCT': [0.4, 0.45, 0.5, 0.55, 0.6],
        'FG3_PCT': [0.3, 0.35, 0.4, 0.45, 0.5],
        'FT_PCT': [0.7, 0.75, 0.8, 0.85, 0.9],
        'AST': [20, 22, 24, 26, 28],
        'REB': [40, 42, 44, 46, 48],
        'TOV': [10, 12, 14, 16, 18],
        'PLUS_MINUS': [5, 10, 15, 20, 25],
        'MATCHUP': ['A vs B', 'A @ C', 'A vs D', 'A @ E', 'A vs F'],
        'WL': ['W', 'L', 'W', 'W', 'L']
    }
    return pd.DataFrame(data)

def test_rolling_averages(dummy_data):
    engineer = NBAFeatureEngineer()
    # Probamos con una ventana pequeña para el dummy
    df_result = engineer.create_rolling_features(dummy_data, windows=[3])
    
    # La primera ventana de 3 debe tener nulos (porque shift(1) mueve los datos)
    assert df_result['ROLL_PTS_3'].isna().iloc[0]
    assert df_result['ROLL_PTS_3'].isna().iloc[2]
    # La 4ta fila debería tener el promedio de las primeras 3 (100+110+120)/3 = 110
    assert df_result['ROLL_PTS_3'].iloc[3] == 110.0

def test_rest_days_calculation(dummy_data):
    engineer = NBAFeatureEngineer()
    df_result = engineer.calculate_rest_days(dummy_data)
    
    # Entre '2023-01-01' y '2023-01-03' hay 2 días
    assert df_result['DAYS_REST'].iloc[1] == 2
    # El primer registro debe tener el valor de relleno (7 o 10)
    assert df_result['DAYS_REST'].iloc[0] >= 7
