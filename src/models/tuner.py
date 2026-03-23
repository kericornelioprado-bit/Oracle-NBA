import optuna
import pandas as pd
import xgboost as xgb
from sklearn.metrics import log_loss, accuracy_score
from src.utils.logger import logger
from src.models.trainer import NBAModelTrainer
from src.models.evaluator import NBAProfitSim
import mlflow
import joblib
import os

class NBAHyperTuner:
    def __init__(self, data_path="data/processed/nba_games_features.parquet"):
        self.data_path = data_path
        self.trainer = NBAModelTrainer(data_path=data_path)

    def objective(self, trial):
        X_train, X_test, y_train, y_test, _ = self.trainer.prepare_data()

        # Definir el espacio de búsqueda de parámetros
        param = {
            'verbosity': 0,
            'objective': 'binary:logistic',
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.1, log=True),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
        }

        model = xgb.XGBClassifier(**param)
        model.fit(X_train, y_train)
        
        preds_proba = model.predict_proba(X_test)[:, 1]
        loss = log_loss(y_test, preds_proba)
        
        return loss

    def run_tuning(self, n_trials=20):
        logger.info(f"Iniciando optimización Bayesiana con Optuna ({n_trials} trials)...")
        
        mlflow.set_experiment("NBA_Oracle_Optuna_Tuning")
        
        study = optuna.create_study(direction='minimize')
        
        with mlflow.start_run(run_name="Optuna_XGBoost_Study"):
            study.optimize(self.objective, n_trials=n_trials)
            
            logger.info("Tuning completado.")
            logger.info(f"Mejor LogLoss: {study.best_value:.4f}")
            logger.info(f"Mejores Parámetros: {study.best_params}")
            
            # Log de los mejores parámetros en MLflow
            mlflow.log_params(study.best_params)
            mlflow.log_metric("best_log_loss", study.best_value)
            
            # Re-entrenar el mejor modelo y evaluar ROI
            X_train, X_test, y_train, y_test, _ = self.trainer.prepare_data()
            best_model = xgb.XGBClassifier(**study.best_params)
            best_model.fit(X_train, y_train)
            
            os.makedirs("models", exist_ok=True)
            joblib.dump(best_model, "models/nba_best_model_tuned.joblib")
            
            # Evaluar ROI del modelo tuneado
            sim = NBAProfitSim(model_path="models/nba_best_model_tuned.joblib")
            sim_results = sim.run_simulation()
            
            total_bets = sim_results['BET_PLACED'].sum()
            total_profit = sim_results['PROFIT'].sum()
            roi = (total_profit / (total_bets * 100)) * 100 if total_bets > 0 else 0
            
            mlflow.log_metric("tuned_roi", roi)
            logger.info(f"ROI del modelo tuneado: {roi:.2f}%")
            
        return study.best_params

if __name__ == "__main__":
    tuner = NBAHyperTuner()
    tuner.run_tuning()
