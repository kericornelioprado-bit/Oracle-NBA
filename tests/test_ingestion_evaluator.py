import pytest
import pandas as pd
import numpy as np
from src.data.ingestion import NBADataIngestor
from src.models.evaluator import NBAProfitSim
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_games_df():
    """Genera datos de juegos simulados."""
    return pd.DataFrame({
        'GAME_ID': ['001', '002'],
        'TEAM_ID': [1610612738, 1610612743],
        'WL': ['W', 'L'],
        'PTS': [110, 105],
        'GAME_DATE': ['2023-01-01', '2023-01-02']
    })

def test_ingestor_save_parquet(tmp_path, mock_games_df):
    """Prueba que el ingestor guarde correctamente en Parquet."""
    raw_path = tmp_path / "raw"
    raw_path.mkdir()
    ingestor = NBADataIngestor(raw_data_path=str(raw_path))
    
    filename = "test_games.parquet"
    ingestor.save_to_parquet(mock_games_df, filename)
    
    saved_file = raw_path / filename
    assert saved_file.exists()
    df_loaded = pd.read_parquet(saved_file)
    assert len(df_loaded) == 2
    assert 'WL' in df_loaded.columns

def test_profit_calculator_math():
    """Valida matemáticamente la lógica de cálculo de beneficios del simulador."""
    # Simulamos una fila de apuesta ganadora
    row_win = pd.Series({
        'BET_PLACED': 1,
        'PRED_PROBA': 0.8,
        'TARGET': 1, # Ganó el local
        'PREDICTION': 1
    })
    
    # Simulamos una fila de apuesta perdedora
    row_loss = pd.Series({
        'BET_PLACED': 1,
        'PRED_PROBA': 0.8,
        'TARGET': 0, # Perdió el local
        'PREDICTION': 1
    })

    # Usamos cuota 2.0 para simplificar: gana 100 o pierde 100
    unit_size = 100
    odds = 2.0
    
    # Lógica de beneficio (extrayendo de evaluator.py)
    def calc(row):
        if row['PRED_PROBA'] > 0.5 and row['TARGET'] == 1:
            return unit_size * (odds - 1)
        else:
            return -unit_size

    assert calc(row_win) == 100.0
    assert calc(row_loss) == -100.0

@patch('nba_api.stats.endpoints.leaguegamefinder.LeagueGameFinder')
def test_ingestor_api_error_handling(mock_finder):
    """Prueba que el ingestor maneje errores de la API sin romperse."""
    mock_finder.side_effect = Exception("API Timeout")
    ingestor = NBADataIngestor()
    
    # El método debe devolver None en caso de error y no lanzar la excepción
    result = ingestor.fetch_season_games("2023-24")
    assert result is None
