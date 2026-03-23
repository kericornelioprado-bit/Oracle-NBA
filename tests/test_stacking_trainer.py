import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_feature_parquet(tmp_path):
    """Crea un parquet mínimo con features y TARGET para tests de entrenamiento."""
    n = 30
    np.random.seed(0)
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
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_stacking_trainer_init(tmp_path):
    """Debe inicializarse con la ruta de datos y parámetros XGB hardcodeados."""
    from src.models.stacking_trainer import NBAStackingTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAStackingTrainer(data_path=path)
    assert trainer.data_path == path
    assert 'n_estimators' in trainer.best_xgb_params
    assert 'max_depth' in trainer.best_xgb_params


def test_build_stacking_model(tmp_path):
    """build_stacking_model debe retornar un StackingClassifier."""
    from src.models.stacking_trainer import NBAStackingTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAStackingTrainer(data_path=path)
    model = trainer.build_stacking_model()
    assert isinstance(model, StackingClassifier)
    estimator_names = [name for name, _ in model.estimators]
    assert 'lr' in estimator_names
    assert 'xgb' in estimator_names


def test_train_and_evaluate_mocked(tmp_path):
    """train_and_evaluate debe llamar a mlflow y retornar el modelo entrenado."""
    from src.models.stacking_trainer import NBAStackingTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAStackingTrainer(data_path=path)

    mock_model = MagicMock()

    mock_sim_results = pd.DataFrame({
        'BET_PLACED': [1, 0, 1],
        'TARGET': [1, 1, 0],
        'PREDICTION': [1, 1, 0],
        'PROFIT': [91, 0, -100],
    })

    with patch('mlflow.set_experiment'), \
         patch('mlflow.start_run') as mock_run, \
         patch('mlflow.log_metric'), \
         patch('joblib.dump'), \
         patch('src.models.stacking_trainer.accuracy_score', return_value=0.65), \
         patch('src.models.stacking_trainer.log_loss', return_value=0.55), \
         patch.object(trainer, 'build_stacking_model', return_value=mock_model), \
         patch('src.models.stacking_trainer.NBAProfitSim') as mock_sim_cls:

        mock_ctx = MagicMock()
        mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_sim_instance = MagicMock()
        mock_sim_instance.run_simulation.return_value = mock_sim_results
        mock_sim_cls.return_value = mock_sim_instance

        result = trainer.train_and_evaluate()

    assert result is mock_model
    mock_model.fit.assert_called_once()


def test_stacking_trainer_uses_correct_data_path(tmp_path):
    """El NBAModelTrainer interno debe usar la misma ruta de datos."""
    from src.models.stacking_trainer import NBAStackingTrainer
    path = make_feature_parquet(tmp_path)
    trainer = NBAStackingTrainer(data_path=path)
    assert trainer.trainer.data_path == path
