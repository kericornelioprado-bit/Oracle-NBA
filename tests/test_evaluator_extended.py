import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def make_feature_df(n=20):
    """Dataset mínimo con features y TARGET."""
    np.random.seed(7)
    return pd.DataFrame({
        'GAME_DATE': pd.date_range('2023-01-01', periods=n, freq='D'),
        'HOME_ROLL_PTS_5': np.random.uniform(95, 125, n),
        'AWAY_ROLL_PTS_5': np.random.uniform(95, 125, n),
        'HOME_DAYS_REST': np.random.randint(1, 5, n).astype(float),
        'AWAY_DAYS_REST': np.random.randint(1, 5, n).astype(float),
        'TARGET': np.random.randint(0, 2, n),
    })


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_profit_sim_init_mocked():
    """NBAProfitSim debe inicializarse cargando modelo y datos correctamente."""
    mock_model = MagicMock()
    mock_df = make_feature_df()

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=mock_df):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim(model_path="models/fake.joblib", data_path="data/fake.parquet")
        assert sim.model is mock_model
        assert len(sim.df) == 20


def test_run_simulation_returns_dataframe():
    """run_simulation debe retornar un DataFrame con columnas de resultados."""
    mock_model = MagicMock()
    df = make_feature_df(25)

    def proba_side_effect(X):
        n = len(X)
        probas = np.random.uniform(0.4, 0.7, n)
        return np.column_stack([1 - probas, probas])

    def predict_side_effect(X):
        n = len(X)
        return np.ones(n, dtype=int)

    mock_model.predict_proba.side_effect = proba_side_effect
    mock_model.predict.side_effect = predict_side_effect

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=df), \
         patch('os.makedirs'), \
         patch('pandas.DataFrame.to_csv'):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim()
        result = sim.run_simulation()

    assert isinstance(result, pd.DataFrame)
    assert 'PROFIT' in result.columns
    assert 'CUM_PROFIT' in result.columns
    assert 'BET_PLACED' in result.columns
    assert 'PRED_PROBA' in result.columns


def test_run_simulation_bet_placed_logic():
    """Las apuestas solo se deben colocar cuando la prob está fuera de [0.476, 0.524]."""
    mock_model = MagicMock()
    # Con 25 filas, test_df tiene 5 filas (el 20%)
    df = make_feature_df(25)

    # 5 probabilidades para el test set
    controlled_probas = np.array([0.6, 0.5, 0.4, 0.52, 0.48])

    def proba_side_effect(X):
        n = len(X)
        p = controlled_probas[:n]
        return np.column_stack([1 - p, p])

    def predict_side_effect(X):
        n = len(X)
        return (controlled_probas[:n] > 0.5).astype(int)

    mock_model.predict_proba.side_effect = proba_side_effect
    mock_model.predict.side_effect = predict_side_effect

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=df), \
         patch('os.makedirs'), \
         patch('pandas.DataFrame.to_csv'):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim()
        result = sim.run_simulation()

    # Los partidos dentro del rango de umbral deben tener BET_PLACED == 0
    skip_mask = (result['PRED_PROBA'] >= 0.476) & (result['PRED_PROBA'] <= 0.524)
    assert (result.loc[skip_mask, 'BET_PLACED'] == 0).all()


def test_run_simulation_profit_calculation_home_win():
    """Si apostamos al local y gana, el beneficio debe ser unit*(odds-1)."""
    mock_model = MagicMock()
    # 25 filas: test_df = 5 filas
    df = make_feature_df(25)
    df['TARGET'] = 1  # Todos ganan el local

    def proba_side_effect(X):
        n = len(X)
        probas = np.full(n, 0.65)
        return np.column_stack([1 - probas, probas])

    def predict_side_effect(X):
        return np.ones(len(X), dtype=int)

    mock_model.predict_proba.side_effect = proba_side_effect
    mock_model.predict.side_effect = predict_side_effect

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=df), \
         patch('os.makedirs'), \
         patch('pandas.DataFrame.to_csv'):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim()
        result = sim.run_simulation(unit_size=100, odds=1.91)

    bets = result[result['BET_PLACED'] == 1]
    assert all(abs(v - 91.0) < 1e-6 for v in bets['PROFIT'])


def test_run_simulation_profit_calculation_away_win():
    """Si apostamos al visitante y gana, el beneficio debe ser unit*(odds-1)."""
    mock_model = MagicMock()
    # Usar 25 filas: 80% = 20 train, 20% = 5 test
    df = make_feature_df(25)
    df['TARGET'] = 0  # Todos ganan el visitante

    # predict_proba debe retornar solo las filas del test (20% = 5 filas)
    def proba_side_effect(X):
        n = len(X)
        probas = np.full(n, 0.40)
        return np.column_stack([1 - probas, probas])

    def predict_side_effect(X):
        return np.zeros(len(X), dtype=int)

    mock_model.predict_proba.side_effect = proba_side_effect
    mock_model.predict.side_effect = predict_side_effect

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=df), \
         patch('os.makedirs'), \
         patch('pandas.DataFrame.to_csv'):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim()
        result = sim.run_simulation(unit_size=100, odds=1.91)

    bets = result[result['BET_PLACED'] == 1]
    assert all(abs(v - 91.0) < 1e-6 for v in bets['PROFIT'])


def test_run_simulation_roi_zero_bets():
    """Con cero apuestas el ROI debe ser 0."""
    mock_model = MagicMock()
    # 25 filas: test set = 5 filas
    df = make_feature_df(25)

    # Todos dentro del umbral → no se apuesta
    def proba_side_effect(X):
        n = len(X)
        probas = np.full(n, 0.50)
        return np.column_stack([1 - probas, probas])

    def predict_side_effect(X):
        return np.ones(len(X), dtype=int)

    mock_model.predict_proba.side_effect = proba_side_effect
    mock_model.predict.side_effect = predict_side_effect

    with patch('joblib.load', return_value=mock_model), \
         patch('pandas.read_parquet', return_value=df), \
         patch('os.makedirs'), \
         patch('pandas.DataFrame.to_csv'):
        from src.models.evaluator import NBAProfitSim
        sim = NBAProfitSim()
        result = sim.run_simulation()

    assert result['BET_PLACED'].sum() == 0
    assert result['PROFIT'].sum() == 0
