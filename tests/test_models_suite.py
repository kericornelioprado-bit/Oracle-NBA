"""
Suite robusta para NBAModelTrainer, NBAStackingTrainer y NBAHyperTuner.
Cubre edge cases, lógica de negocio y contratos de MLflow no testeados antes.
"""
import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, call
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import StackingClassifier


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures comunes
# ─────────────────────────────────────────────────────────────────────────────

def _make_parquet(tmp_path, n=30, seed=42, sorted_dates=True):
    """Crea un parquet mínimo con features ROLL_ + DAYS_REST + TARGET."""
    np.random.seed(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    if not sorted_dates:
        dates = dates[::-1]  # fechas en orden inverso
    df = pd.DataFrame({
        "GAME_DATE": dates,
        "HOME_ROLL_PTS_3":  np.random.uniform(95, 125, n),
        "HOME_ROLL_PTS_5":  np.random.uniform(95, 125, n),
        "HOME_ROLL_FG_PCT_3": np.random.uniform(0.4, 0.55, n),
        "HOME_DAYS_REST":   np.random.randint(1, 5, n).astype(float),
        "AWAY_ROLL_PTS_3":  np.random.uniform(95, 125, n),
        "AWAY_ROLL_PTS_5":  np.random.uniform(95, 125, n),
        "AWAY_DAYS_REST":   np.random.randint(1, 5, n).astype(float),
        "GAME_ID":          [f"G{i}" for i in range(n)],
        "TARGET":           np.random.randint(0, 2, n),
    })
    path = tmp_path / "features.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def _make_sim_df(n_bets=3, n_skips=1, win_rate=1.0):
    """Simula el DataFrame que retorna NBAProfitSim.run_simulation()."""
    rows = []
    for i in range(n_bets):
        won = int(np.random.random() < win_rate)
        rows.append({
            "BET_PLACED": 1,
            "TARGET":     won,
            "PREDICTION": 1,
            "PROFIT":     91.0 if won else -100.0,
        })
    for _ in range(n_skips):
        rows.append({"BET_PLACED": 0, "TARGET": 1, "PREDICTION": 0, "PROFIT": 0.0})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# NBAModelTrainer
# ─────────────────────────────────────────────────────────────────────────────

class TestNBAModelTrainer:

    def test_prepare_data_feature_filter(self, tmp_path):
        """Solo columnas con 'ROLL_' o 'DAYS_REST' deben aparecer en feature_cols."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)
        _, _, _, _, feature_cols = trainer.prepare_data()

        assert all("ROLL_" in c or "DAYS_REST" in c for c in feature_cols)
        assert "TARGET" not in feature_cols
        assert "GAME_DATE" not in feature_cols
        assert "GAME_ID" not in feature_cols

    def test_prepare_data_temporal_split_ratio(self, tmp_path):
        """El split debe respetar 80 % train / 20 % test sin mezclar."""
        from src.models.trainer import NBAModelTrainer
        n = 30
        path = _make_parquet(tmp_path, n=n)
        trainer = NBAModelTrainer(data_path=path)
        X_train, X_test, _, _, _ = trainer.prepare_data()

        assert len(X_train) == int(n * 0.8)
        assert len(X_test) == n - int(n * 0.8)

    def test_prepare_data_sorts_by_date(self, tmp_path):
        """El split debe ordenar por GAME_DATE aunque el parquet llegue desordenado."""
        from src.models.trainer import NBAModelTrainer
        n = 20
        path = _make_parquet(tmp_path, n=n, sorted_dates=False)
        trainer = NBAModelTrainer(data_path=path)
        # Leer el parquet original para saber cuáles son las fechas más antiguas
        df_raw = pd.read_parquet(path)
        df_raw["GAME_DATE"] = pd.to_datetime(df_raw["GAME_DATE"])
        df_sorted = df_raw.sort_values("GAME_DATE")
        split_idx = int(n * 0.8)

        X_train, X_test, y_train, y_test, feature_cols = trainer.prepare_data()

        # El total de registros se conserva
        assert len(X_train) + len(X_test) == n
        # Los índices de train son los primeros en el orden temporal
        expected_train_indices = df_sorted.index[:split_idx].tolist()
        assert list(X_train.index) == expected_train_indices

    def test_prepare_data_raises_on_missing_file(self, tmp_path):
        """prepare_data debe fallar si el archivo no existe."""
        from src.models.trainer import NBAModelTrainer
        trainer = NBAModelTrainer(data_path=str(tmp_path / "nonexistent.parquet"))
        with pytest.raises(Exception):
            trainer.prepare_data()

    def test_prepare_data_no_null_in_target(self, tmp_path):
        """y_train e y_test no deben contener nulos."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)
        _, _, y_train, y_test, _ = trainer.prepare_data()

        assert not y_train.isnull().any()
        assert not y_test.isnull().any()

    def test_save_temp_model_calls_joblib(self, tmp_path):
        """save_temp_model debe llamar a joblib.dump con la ruta correcta."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)

        with patch("os.makedirs"), patch("joblib.dump") as mock_dump:
            trainer.save_temp_model(LogisticRegression())
            mock_dump.assert_called_once()
            args = mock_dump.call_args[0]
            assert isinstance(args[0], LogisticRegression)
            assert args[1] == "models/temp_model.joblib"

    def test_save_temp_model_creates_directory(self, tmp_path):
        """save_temp_model debe crear el directorio models/ si no existe."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)

        with patch("os.makedirs") as mock_mkdir, patch("joblib.dump"):
            trainer.save_temp_model(LogisticRegression())
            mock_mkdir.assert_called_once_with("models", exist_ok=True)

    def test_train_and_evaluate_runs_both_models(self, tmp_path):
        """train_and_evaluate debe abrir un run de MLflow por cada modelo."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)
        sim_df = _make_sim_df()

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("mlflow.sklearn.log_model"), \
             patch.object(trainer, "save_temp_model"), \
             patch("src.models.trainer.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        # Hay exactamente 2 modelos (LR y XGBoost)
        assert mock_run.call_count == 2

    def test_train_and_evaluate_roi_zero_when_no_bets(self, tmp_path):
        """Si total_bets == 0, el ROI logueado debe ser 0."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)

        sim_df_no_bets = pd.DataFrame({
            "BET_PLACED": [0, 0],
            "TARGET":     [1, 0],
            "PREDICTION": [0, 1],
            "PROFIT":     [0.0, 0.0],
        })

        logged_metrics = {}

        def capture_metric(key, value):
            logged_metrics[key] = value

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric", side_effect=capture_metric), \
             patch("mlflow.sklearn.log_model"), \
             patch.object(trainer, "save_temp_model"), \
             patch("src.models.trainer.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df_no_bets

            trainer.train_and_evaluate()

        assert logged_metrics.get("roi_percentage") == 0

    def test_train_and_evaluate_uses_mlflow_tracking_uri_env(self, tmp_path, monkeypatch):
        """set_tracking_uri debe usar la var de entorno MLFLOW_TRACKING_URI."""
        from src.models.trainer import NBAModelTrainer
        custom_uri = "http://mlflow.example.com:5000"
        monkeypatch.setenv("MLFLOW_TRACKING_URI", custom_uri)
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)
        sim_df = _make_sim_df()

        captured_uris = []

        with patch("mlflow.set_tracking_uri", side_effect=lambda u: captured_uris.append(u)), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("mlflow.sklearn.log_model"), \
             patch.object(trainer, "save_temp_model"), \
             patch("src.models.trainer.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert custom_uri in captured_uris

    def test_train_and_evaluate_logs_financial_metrics(self, tmp_path):
        """train_and_evaluate debe loguear roi_percentage, bet_win_rate y total_profit."""
        from src.models.trainer import NBAModelTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAModelTrainer(data_path=path)
        sim_df = _make_sim_df(n_bets=2, n_skips=0, win_rate=1.0)

        logged = {}

        def capture(key, value):
            logged[key] = value

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric", side_effect=capture), \
             patch("mlflow.sklearn.log_model"), \
             patch.object(trainer, "save_temp_model"), \
             patch("src.models.trainer.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert "roi_percentage" in logged
        assert "bet_win_rate" in logged
        assert "total_profit_usd" in logged


# ─────────────────────────────────────────────────────────────────────────────
# NBAStackingTrainer
# ─────────────────────────────────────────────────────────────────────────────

class TestNBAStackingTrainer:

    def test_init_stores_all_xgb_params(self, tmp_path):
        """best_xgb_params debe tener todas las claves requeridas por XGBClassifier."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        required_keys = {
            "n_estimators", "max_depth", "learning_rate",
            "subsample", "colsample_bytree", "gamma",
        }
        assert required_keys.issubset(trainer.best_xgb_params.keys())

    def test_build_model_has_two_base_estimators(self, tmp_path):
        """El StackingClassifier debe tener exactamente 2 base estimators."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        model = trainer.build_stacking_model()

        assert len(model.estimators) == 2

    def test_build_model_estimator_names(self, tmp_path):
        """Los base estimators deben llamarse 'lr' y 'xgb'."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        model = trainer.build_stacking_model()

        names = [name for name, _ in model.estimators]
        assert names == ["lr", "xgb"]

    def test_build_model_meta_estimator_is_lr(self, tmp_path):
        """El meta-estimador debe ser LogisticRegression."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        model = trainer.build_stacking_model()

        assert isinstance(model.final_estimator, LogisticRegression)

    def test_build_model_cv_is_5(self, tmp_path):
        """El StackingClassifier debe usar CV=5."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        model = trainer.build_stacking_model()

        assert model.cv == 5

    def test_build_model_returns_stacking_classifier(self, tmp_path):
        """build_stacking_model debe retornar un StackingClassifier."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)
        model = trainer.build_stacking_model()

        assert isinstance(model, StackingClassifier)

    def test_internal_trainer_uses_same_data_path(self, tmp_path):
        """El NBAModelTrainer interno debe usar exactamente la misma ruta."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        assert trainer.trainer.data_path == path

    def test_train_and_evaluate_saves_model_to_correct_path(self, tmp_path):
        """El modelo debe guardarse en 'models/nba_best_model_stacking.joblib'."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        mock_model = MagicMock()
        sim_df = _make_sim_df()
        dumped_paths = []

        def capture_dump(obj, p):
            dumped_paths.append(p)

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric"), \
             patch("joblib.dump", side_effect=capture_dump), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=mock_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.64), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.60):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert "models/nba_best_model_stacking.joblib" in dumped_paths

    def test_train_and_evaluate_logs_accuracy_and_logloss(self, tmp_path):
        """train_and_evaluate debe loguear accuracy y log_loss a MLflow."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        mock_model = MagicMock()
        sim_df = _make_sim_df()
        logged = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric", side_effect=lambda k, v: logged.update({k: v})), \
             patch("joblib.dump"), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=mock_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.639), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.58):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert logged.get("accuracy") == pytest.approx(0.639)
        assert logged.get("log_loss") == pytest.approx(0.58)

    def test_train_and_evaluate_logs_roi_and_win_rate(self, tmp_path):
        """train_and_evaluate debe loguear roi_percentage y bet_win_rate."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        mock_model = MagicMock()
        # 2 apuestas ganadas → win_rate=100%, ROI = (182/200)*100 = 91%
        sim_df = pd.DataFrame({
            "BET_PLACED":  [1, 1],
            "TARGET":      [1, 1],
            "PREDICTION":  [1, 1],
            "PROFIT":      [91.0, 91.0],
        })
        logged = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric", side_effect=lambda k, v: logged.update({k: v})), \
             patch("joblib.dump"), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=mock_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.64), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.60):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert "roi_percentage" in logged
        assert "bet_win_rate" in logged
        assert logged["roi_percentage"] == pytest.approx(91.0)
        assert logged["bet_win_rate"] == pytest.approx(100.0)

    def test_train_and_evaluate_roi_zero_when_no_bets(self, tmp_path):
        """roi_percentage debe ser 0 cuando total_bets == 0."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        mock_model = MagicMock()
        sim_df_no_bets = pd.DataFrame({
            "BET_PLACED": [0, 0],
            "TARGET":     [1, 0],
            "PREDICTION": [0, 1],
            "PROFIT":     [0.0, 0.0],
        })
        logged = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric", side_effect=lambda k, v: logged.update({k: v})), \
             patch("joblib.dump"), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=mock_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.5), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.7):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df_no_bets

            trainer.train_and_evaluate()

        assert logged.get("roi_percentage") == 0

    def test_train_and_evaluate_returns_fitted_model(self, tmp_path):
        """train_and_evaluate debe retornar el modelo entrenado."""
        from src.models.stacking_trainer import NBAStackingTrainer
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        sentinel_model = MagicMock()
        sim_df = _make_sim_df()

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric"), \
             patch("joblib.dump"), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=sentinel_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.6), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.65):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            result = trainer.train_and_evaluate()

        assert result is sentinel_model
        sentinel_model.fit.assert_called_once()

    def test_train_and_evaluate_uses_mlflow_env_uri(self, tmp_path, monkeypatch):
        """set_tracking_uri debe respetar la variable MLFLOW_TRACKING_URI."""
        from src.models.stacking_trainer import NBAStackingTrainer
        custom_uri = "http://mlflow-stacking.test:5000"
        monkeypatch.setenv("MLFLOW_TRACKING_URI", custom_uri)
        path = _make_parquet(tmp_path)
        trainer = NBAStackingTrainer(data_path=path)

        mock_model = MagicMock()
        sim_df = _make_sim_df()
        captured_uris = []

        with patch("mlflow.set_tracking_uri", side_effect=lambda u: captured_uris.append(u)), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_metric"), \
             patch("joblib.dump"), \
             patch("os.makedirs"), \
             patch.object(trainer, "build_stacking_model", return_value=mock_model), \
             patch("src.models.stacking_trainer.NBAProfitSim") as mock_sim_cls, \
             patch("src.models.stacking_trainer.accuracy_score", return_value=0.6), \
             patch("src.models.stacking_trainer.log_loss", return_value=0.65):

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            trainer.train_and_evaluate()

        assert custom_uri in captured_uris


# ─────────────────────────────────────────────────────────────────────────────
# NBAHyperTuner
# ─────────────────────────────────────────────────────────────────────────────

class TestNBAHyperTuner:

    def test_init_stores_data_path(self, tmp_path):
        """El tuner debe almacenar la ruta de datos y compartirla con el trainer."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        assert tuner.data_path == path
        assert tuner.trainer.data_path == path

    def test_objective_returns_non_negative_float(self, tmp_path):
        """objective() debe retornar un float >= 0 (log_loss)."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [100, 5]
        mock_trial.suggest_float.side_effect = [0.05, 0.8, 0.7, 1e-4]

        result = tuner.objective(mock_trial)

        assert isinstance(result, float)
        assert result >= 0.0

    def test_objective_calls_suggest_int_for_n_estimators_and_max_depth(self, tmp_path):
        """objective debe llamar suggest_int para n_estimators y max_depth."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [100, 5]
        mock_trial.suggest_float.side_effect = [0.05, 0.8, 0.7, 1e-4]

        tuner.objective(mock_trial)

        suggest_int_calls = [c[0][0] for c in mock_trial.suggest_int.call_args_list]
        assert "n_estimators" in suggest_int_calls
        assert "max_depth" in suggest_int_calls

    def test_objective_calls_suggest_float_for_lr_subsample_colsample_gamma(self, tmp_path):
        """objective debe llamar suggest_float para los 4 hiperparámetros flotantes."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_trial = MagicMock()
        mock_trial.suggest_int.side_effect = [100, 5]
        mock_trial.suggest_float.side_effect = [0.05, 0.8, 0.7, 1e-4]

        tuner.objective(mock_trial)

        suggest_float_calls = [c[0][0] for c in mock_trial.suggest_float.call_args_list]
        assert "learning_rate" in suggest_float_calls
        assert "subsample" in suggest_float_calls
        assert "colsample_bytree" in suggest_float_calls
        assert "gamma" in suggest_float_calls

    def test_run_tuning_calls_optimize_with_n_trials(self, tmp_path):
        """run_tuning debe llamar study.optimize con el n_trials correcto."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.62
        mock_study.best_params = {
            "n_estimators": 100, "max_depth": 4,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.7, "gamma": 1e-4,
        }
        sim_df = _make_sim_df()

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=7)

        call_kwargs = mock_study.optimize.call_args
        assert call_kwargs[1].get("n_trials") == 7 or call_kwargs[0][1] == 7

    def test_run_tuning_returns_best_params(self, tmp_path):
        """run_tuning debe retornar study.best_params."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        expected = {
            "n_estimators": 128, "max_depth": 4,
            "learning_rate": 0.03, "subsample": 0.89,
            "colsample_bytree": 0.66, "gamma": 5.9e-5,
        }
        mock_study = MagicMock()
        mock_study.best_value = 0.61
        mock_study.best_params = expected
        sim_df = _make_sim_df()

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            result = tuner.run_tuning(n_trials=2)

        assert result == expected

    def test_run_tuning_saves_model_to_correct_path(self, tmp_path):
        """El modelo tuneado debe guardarse en 'models/nba_best_model_tuned.joblib'."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.63
        mock_study.best_params = {
            "n_estimators": 100, "max_depth": 3,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.7, "gamma": 1e-4,
        }
        sim_df = _make_sim_df()
        dumped_paths = []

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump", side_effect=lambda obj, p: dumped_paths.append(p)), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=2)

        assert "models/nba_best_model_tuned.joblib" in dumped_paths

    def test_run_tuning_logs_best_params_to_mlflow(self, tmp_path):
        """run_tuning debe llamar mlflow.log_params con study.best_params."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        best_params = {
            "n_estimators": 200, "max_depth": 6,
            "learning_rate": 0.02, "subsample": 0.75,
            "colsample_bytree": 0.65, "gamma": 0.001,
        }
        mock_study = MagicMock()
        mock_study.best_value = 0.60
        mock_study.best_params = best_params
        sim_df = _make_sim_df()
        logged_params = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params", side_effect=lambda p: logged_params.update(p)), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=2)

        assert logged_params == best_params

    def test_run_tuning_logs_best_logloss_and_roi(self, tmp_path):
        """run_tuning debe loguear best_log_loss y tuned_roi a MLflow."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.605
        mock_study.best_params = {
            "n_estimators": 100, "max_depth": 4,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.7, "gamma": 1e-4,
        }
        # 1 apuesta ganada → roi = (91/100)*100 = 91
        sim_df = pd.DataFrame({
            "BET_PLACED": [1],
            "TARGET":     [1],
            "PREDICTION": [1],
            "PROFIT":     [91.0],
        })
        logged = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric", side_effect=lambda k, v: logged.update({k: v})), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=2)

        assert logged.get("best_log_loss") == pytest.approx(0.605)
        assert "tuned_roi" in logged
        assert logged["tuned_roi"] == pytest.approx(91.0)

    def test_run_tuning_roi_zero_when_no_bets(self, tmp_path):
        """tuned_roi debe ser 0 cuando no hay apuestas realizadas."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.68
        mock_study.best_params = {
            "n_estimators": 50, "max_depth": 3,
            "learning_rate": 0.1, "subsample": 0.6,
            "colsample_bytree": 0.6, "gamma": 0.1,
        }
        sim_df_no_bets = pd.DataFrame({
            "BET_PLACED": [0, 0],
            "TARGET":     [1, 0],
            "PREDICTION": [0, 1],
            "PROFIT":     [0.0, 0.0],
        })
        logged = {}

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric", side_effect=lambda k, v: logged.update({k: v})), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df_no_bets

            tuner.run_tuning(n_trials=2)

        assert logged.get("tuned_roi") == 0

    def test_run_tuning_creates_study_with_minimize_direction(self, tmp_path):
        """optuna.create_study debe usarse con direction='minimize'."""
        from src.models.tuner import NBAHyperTuner
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.65
        mock_study.best_params = {
            "n_estimators": 100, "max_depth": 4,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.7, "gamma": 1e-4,
        }
        sim_df = _make_sim_df()
        captured_kwargs = {}

        def capture_study(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_study

        with patch("mlflow.set_tracking_uri"), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", side_effect=capture_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=2)

        assert captured_kwargs.get("direction") == "minimize"

    def test_run_tuning_uses_mlflow_env_uri(self, tmp_path, monkeypatch):
        """run_tuning debe usar la variable MLFLOW_TRACKING_URI."""
        from src.models.tuner import NBAHyperTuner
        custom_uri = "http://mlflow-tuner.test:5000"
        monkeypatch.setenv("MLFLOW_TRACKING_URI", custom_uri)
        path = _make_parquet(tmp_path)
        tuner = NBAHyperTuner(data_path=path)

        mock_study = MagicMock()
        mock_study.best_value = 0.63
        mock_study.best_params = {
            "n_estimators": 100, "max_depth": 4,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.7, "gamma": 1e-4,
        }
        sim_df = _make_sim_df()
        captured_uris = []

        with patch("mlflow.set_tracking_uri", side_effect=lambda u: captured_uris.append(u)), \
             patch("mlflow.set_experiment"), \
             patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_params"), \
             patch("mlflow.log_metric"), \
             patch("optuna.create_study", return_value=mock_study), \
             patch("os.makedirs"), \
             patch("joblib.dump"), \
             patch("src.models.tuner.NBAProfitSim") as mock_sim_cls:

            mock_ctx = MagicMock()
            mock_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_run.return_value.__exit__ = MagicMock(return_value=False)
            mock_sim_cls.return_value.run_simulation.return_value = sim_df

            tuner.run_tuning(n_trials=2)

        assert custom_uri in captured_uris
