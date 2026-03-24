import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.ensemble import StackingClassifier
from sklearn.metrics import accuracy_score, log_loss
from src.utils.logger import logger
from src.models.trainer import NBAModelTrainer
from src.models.evaluator import NBAProfitSim
import mlflow
import joblib
import os

class NBAStackingTrainer:
    def __init__(self, data_path="data/processed/nba_games_features.parquet"):
        self.data_path = data_path
        self.trainer = NBAModelTrainer(data_path=data_path)
        
        # Mejores parámetros encontrados por Optuna
        self.best_xgb_params = {
            'n_estimators': 128, 
            'max_depth': 4, 
            'learning_rate': 0.029966102946042298, 
            'subsample': 0.8945709928165497, 
            'colsample_bytree': 0.665405675704292, 
            'gamma': 5.8756107803183025e-05
        }

    def build_stacking_model(self):
        base_models = [
            ('lr', LogisticRegression(max_iter=1000)),
            ('xgb', XGBClassifier(**self.best_xgb_params))
        ]
        
        # Meta-modelo: Una regresión logística simple suele ser el mejor "blender"
        stacking_model = StackingClassifier(
            estimators=base_models,
            final_estimator=LogisticRegression(),
            cv=5 # Cross-validation interna para evitar overfitting
        )
        return stacking_model

    def train_and_evaluate(self):
        X_train, X_test, y_train, y_test, _ = self.trainer.prepare_data()
        
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///data/mlflow/mlflow.db"))
        mlflow.set_experiment("NBA_Oracle_Stacking_Ensemble")
        
        with mlflow.start_run(run_name="Stacking_LR_XGBoost"):
            logger.info("Entrenando Stacking Ensemble (LR + XGBoost)...")
            model = self.build_stacking_model()
            model.fit(X_train, y_train)
            
            # Evaluación Técnica
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]
            acc = accuracy_score(y_test, y_pred)
            loss = log_loss(y_test, y_proba)
            
            mlflow.log_metric("accuracy", acc)
            mlflow.log_metric("log_loss", loss)
            
            # Guardar modelo
            os.makedirs("models", exist_ok=True)
            model_path = "models/nba_best_model_stacking.joblib"
            joblib.dump(model, model_path)
            
            # Evaluación de ROI
            sim = NBAProfitSim(model_path=model_path)
            sim_results = sim.run_simulation()
            
            total_bets = sim_results['BET_PLACED'].sum()
            total_profit = sim_results['PROFIT'].sum()
            roi = (total_profit / (total_bets * 100)) * 100 if total_bets > 0 else 0
            win_rate = (sim_results[sim_results['BET_PLACED'] == 1]['TARGET'] == 
                        sim_results[sim_results['BET_PLACED'] == 1]['PREDICTION']).mean() * 100

            mlflow.log_metric("roi_percentage", roi)
            mlflow.log_metric("bet_win_rate", win_rate)
            
            logger.info(f"--- RESULTADOS STACKING ---")
            logger.info(f"Accuracy: {acc:.4f} | Win Rate: {win_rate:.2f}% | ROI: {roi:.2f}%")
            
        return model

if __name__ == "__main__":
    stacker = NBAStackingTrainer()
    stacker.train_and_evaluate()
