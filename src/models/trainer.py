import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss
from src.utils.logger import logger
from src.models.evaluator import NBAProfitSim
import os
import joblib
import mlflow
import mlflow.sklearn

class NBAModelTrainer:
    def __init__(self, data_path="data/processed/nba_games_features.parquet"):
        self.data_path = data_path
        self.models = {
            "logistic_regression": LogisticRegression(max_iter=1000),
            "xgboost": XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42)
        }

    def prepare_data(self):
        df = pd.read_parquet(self.data_path)
        df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values('GAME_DATE')
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        feature_cols = [col for col in df.columns if 'ROLL_' in col or 'DAYS_REST' in col]
        X_train = train_df[feature_cols]
        y_train = train_df['TARGET']
        X_test = test_df[feature_cols]
        y_test = test_df['TARGET']
        return X_train, X_test, y_train, y_test, feature_cols

    def train_and_evaluate(self):
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_data()
        
        # Configurar MLflow
        mlflow.set_experiment("NBA_Oracle_Predictive_Model")

        for name, model in self.models.items():
            with mlflow.start_run(run_name=name):
                logger.info(f"Iniciando experimento MLflow para: {name}...")
                
                # Entrenar
                model.fit(X_train, y_train)
                
                # Métricas Técnicas
                y_pred = model.predict(X_test)
                y_proba = model.predict_proba(X_test)[:, 1]
                acc = accuracy_score(y_test, y_pred)
                loss = log_loss(y_test, y_proba)
                
                # Log en MLflow
                mlflow.log_params(model.get_params() if hasattr(model, 'get_params') else {})
                mlflow.log_metric("accuracy", acc)
                mlflow.log_metric("log_loss", loss)
                
                # Ejecutar Simulación de ROI para este modelo específico
                self.save_temp_model(model)
                sim = NBAProfitSim(model_path="models/temp_model.joblib")
                sim_results = sim.run_simulation()
                
                # Calcular métricas de negocio
                total_bets = sim_results['BET_PLACED'].sum()
                total_profit = sim_results['PROFIT'].sum()
                roi = (total_profit / (total_bets * 100)) * 100 if total_bets > 0 else 0
                win_rate = (sim_results[sim_results['BET_PLACED'] == 1]['TARGET'] == 
                            sim_results[sim_results['BET_PLACED'] == 1]['PREDICTION']).mean() * 100

                # Log Métricas Financieras en MLflow
                mlflow.log_metric("roi_percentage", roi)
                mlflow.log_metric("bet_win_rate", win_rate)
                mlflow.log_metric("total_profit_usd", total_profit)
                
                # Guardar Artefacto del Modelo
                mlflow.sklearn.log_model(model, "model")
                
                logger.info(f"[{name}] Acc: {acc:.4f} | ROI: {roi:.2f}% | WinRate: {win_rate:.2f}%")

        logger.info("Todos los experimentos han sido registrados en MLflow.")

    def save_temp_model(self, model):
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/temp_model.joblib")

if __name__ == "__main__":
    trainer = NBAModelTrainer()
    trainer.train_and_evaluate()

if __name__ == "__main__":
    trainer = NBAModelTrainer()
    trainer.train_and_evaluate()
