import pytest
import pandas as pd
import numpy as np
from src.models.trainer import NBAModelTrainer
from src.models.tuner import NBAHyperTuner
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_processed_data(tmp_path):
    """Crea un dataset procesado falso para pruebas de entrenamiento."""
    df = pd.DataFrame({
        'GAME_ID': ['1', '2', '3', '4', '5'],
        'GAME_DATE': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']),
        'HOME_ROLL_PTS_5': [100, 105, 110, 115, 120],
        'AWAY_ROLL_PTS_5': [95, 100, 105, 110, 115],
        'DAYS_REST': [2, 2, 2, 2, 2],
        'TARGET': [1, 0, 1, 1, 0]
    })
    path = tmp_path / "features.parquet"
    df.to_parquet(path)
    return str(path)

@patch('mlflow.set_experiment')
@patch('mlflow.start_run')
def test_trainer_split_logic(mock_start, mock_set, mock_processed_data):
    """Verifica que el split temporal 80/20 funcione correctamente."""
    trainer = NBAModelTrainer(data_path=mock_processed_data)
    X_train, X_test, y_train, y_test, features = trainer.prepare_data()
    
    # 80% de 5 registros es 4
    assert len(X_train) == 4
    assert len(X_test) == 1
    assert 'HOME_ROLL_PTS_5' in X_train.columns

@patch('optuna.create_study')
def test_tuner_initialization(mock_study, mock_processed_data):
    """Verifica que el tuner se inicialice con el dataset correcto."""
    tuner = NBAHyperTuner(data_path=mock_processed_data)
    assert tuner.data_path == mock_processed_data
    assert tuner.trainer.data_path == mock_processed_data
