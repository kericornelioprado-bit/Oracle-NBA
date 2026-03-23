import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_feature_parquet(tmp_path, n=30):
    np.random.seed(1)
    df = pd.DataFrame({
        'GAME_DATE': pd.date_range('2023-01-01', periods=n, freq='D'),
        'HOME_ROLL_PTS_3': np.random.uniform(95, 125, n),
        'HOME_ROLL_PTS_5': np.random.uniform(95, 125, n),
        'HOME_DAYS_REST': np.random.randint(1, 5, n).astype(float),
        'AWAY_ROLL_PTS_3': np.random.uniform(95, 125, n),
        'AWAY_ROLL_PTS_5': np.random.uniform(95, 125, n),
        'AWAY_DAYS_REST': np.random.randint(1, 5, n).astype(float),
        'TARGET': np.random.randint(0, 2, n),
    })
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return str(path)


# --------------------------------------------------------------------------- #
# Tests para NBAModelTrainer                                                   #
# --------------------------------------------------------------------------- #
def test_prepare_data_feature_columns(tmp_path):
    """prepare_data debe identificar correctamente las columnas de features."""
    from src.models.trainer import NBAModelTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAModelTrainer(data_path=path)
    X_train, X_test, y_train, y_test, feature_cols = trainer.prepare_data()

    assert 'HOME_ROLL_PTS_3' in feature_cols
    assert 'HOME_DAYS_REST' in feature_cols
    assert 'TARGET' not in feature_cols
    assert 'GAME_DATE' not in feature_cols


def test_prepare_data_temporal_order(tmp_path):
    """El split debe respetar el orden temporal: train antes que test."""
    from src.models.trainer import NBAModelTrainer
    path = make_feature_parquet(tmp_path, n=30)
    trainer = NBAModelTrainer(data_path=path)
    X_train, X_test, y_train, y_test, _ = trainer.prepare_data()

    # Los 24 primeros (80% de 30) van a train
    assert len(X_train) == 24
    assert len(X_test) == 6


def test_save_temp_model(tmp_path):
    """save_temp_model debe crear el archivo joblib."""
    from src.models.trainer import NBAModelTrainer
    from sklearn.linear_model import LogisticRegression
    path = make_feature_parquet(tmp_path)
    trainer = NBAModelTrainer(data_path=path)

    import os
    # Necesitamos que el directorio models/ exista
    models_dir = tmp_path / "models"

    with patch('os.makedirs'), \
         patch('joblib.dump') as mock_dump:
        trainer.save_temp_model(LogisticRegression())
        mock_dump.assert_called_once()


def test_train_and_evaluate_mocked(tmp_path):
    """train_and_evaluate debe ejecutar ambos modelos y loguear en MLflow."""
    from src.models.trainer import NBAModelTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAModelTrainer(data_path=path)

    mock_sim_results = pd.DataFrame({
        'BET_PLACED': [1, 0, 1, 1],
        'TARGET': [1, 1, 0, 1],
        'PREDICTION': [1, 1, 1, 1],
        'PROFIT': [91, 0, -100, 91],
    })

    with patch('mlflow.set_experiment'), \
         patch('mlflow.start_run') as mock_run, \
         patch('mlflow.log_params'), \
         patch('mlflow.log_metric'), \
         patch('mlflow.sklearn.log_model'), \
         patch.object(trainer, 'save_temp_model'), \
         patch('src.models.trainer.NBAProfitSim') as mock_sim_cls:

        mock_ctx = MagicMock()
        mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_sim_instance = MagicMock()
        mock_sim_instance.run_simulation.return_value = mock_sim_results
        mock_sim_cls.return_value = mock_sim_instance

        trainer.train_and_evaluate()

    # Debe haberse ejecutado mlflow.start_run para cada modelo (2 modelos)
    assert mock_run.call_count == 2


# --------------------------------------------------------------------------- #
# Tests para NBAHyperTuner                                                     #
# --------------------------------------------------------------------------- #
def test_tuner_objective_returns_float(tmp_path):
    """objective debe retornar un float (log_loss)."""
    from src.models.tuner import NBAHyperTuner
    path = make_feature_parquet(tmp_path)
    tuner = NBAHyperTuner(data_path=path)

    mock_trial = MagicMock()
    mock_trial.suggest_int.side_effect = [100, 5]
    mock_trial.suggest_float.side_effect = [0.05, 0.8, 0.7, 1e-4]

    result = tuner.objective(mock_trial)
    assert isinstance(result, float)
    assert result >= 0


def test_run_tuning_mocked(tmp_path):
    """run_tuning debe ejecutar la optimización y guardar el modelo tuneado."""
    from src.models.tuner import NBAHyperTuner
    path = make_feature_parquet(tmp_path)
    tuner = NBAHyperTuner(data_path=path)

    mock_study = MagicMock()
    mock_study.best_value = 0.65
    mock_study.best_params = {
        'n_estimators': 100,
        'max_depth': 4,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.7,
        'gamma': 1e-4,
    }

    mock_sim_results = pd.DataFrame({
        'BET_PLACED': [1, 1],
        'TARGET': [1, 0],
        'PREDICTION': [1, 1],
        'PROFIT': [91, -100],
    })

    with patch('mlflow.set_experiment'), \
         patch('mlflow.start_run') as mock_run, \
         patch('mlflow.log_params'), \
         patch('mlflow.log_metric'), \
         patch('optuna.create_study', return_value=mock_study), \
         patch('os.makedirs'), \
         patch('joblib.dump'), \
         patch('src.models.tuner.NBAProfitSim') as mock_sim_cls:

        mock_ctx = MagicMock()
        mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_sim_instance = MagicMock()
        mock_sim_instance.run_simulation.return_value = mock_sim_results
        mock_sim_cls.return_value = mock_sim_instance

        result = tuner.run_tuning(n_trials=2)

    assert result == mock_study.best_params
    mock_study.optimize.assert_called_once()
