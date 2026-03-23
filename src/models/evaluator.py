import pandas as pd
import numpy as np
import joblib
from src.utils.logger import logger
import os

class NBAProfitSim:
    def __init__(self, model_path="models/nba_best_model.joblib", data_path="data/processed/nba_games_features.parquet"):
        self.model = joblib.load(model_path)
        self.df = pd.read_parquet(data_path)
        
    def run_simulation(self, unit_size=100, odds=1.91):
        """
        Simula una estrategia de apuestas de unidad fija.
        odds = 1.91 es el estándar (-110 American) para hándicaps/totales equilibrados.
        """
        logger.info("Iniciando simulación de ROI...")
        
        # Preparar datos de prueba (último 20% cronológico)
        self.df['GAME_DATE'] = pd.to_datetime(self.df['GAME_DATE'])
        self.df = self.df.sort_values('GAME_DATE')
        split_idx = int(len(self.df) * 0.8)
        test_df = self.df.iloc[split_idx:].copy()
        
        # Features
        feature_cols = [col for col in self.df.columns if 'ROLL_' in col or 'DAYS_REST' in col]
        X_test = test_df[feature_cols]
        
        # Predicciones y Probabilidades
        test_df['PRED_PROBA'] = self.model.predict_proba(X_test)[:, 1]
        test_df['PREDICTION'] = self.model.predict(X_test)
        
        # Lógica de apuesta: Apostamos si la probabilidad del modelo es > 52.4% 
        # (Break-even para cuotas 1.91)
        test_df['BET_PLACED'] = test_df['PRED_PROBA'].apply(lambda x: 1 if x > 0.524 or x < 0.476 else 0)
        
        # Resultado de la apuesta
        def calculate_profit(row):
            if row['BET_PLACED'] == 0:
                return 0
            
            # Si apostamos al local (PRED_PROBA > 0.5) y gana el local (TARGET=1)
            if row['PRED_PROBA'] > 0.5 and row['TARGET'] == 1:
                return unit_size * (odds - 1)
            # Si apostamos al visitante (PRED_PROBA < 0.5) y gana el visitante (TARGET=0)
            elif row['PRED_PROBA'] <= 0.5 and row['TARGET'] == 0:
                return unit_size * (odds - 1)
            # Si perdemos la apuesta
            else:
                return -unit_size

        test_df['PROFIT'] = test_df.apply(calculate_profit, axis=1)
        test_df['CUM_PROFIT'] = test_df['PROFIT'].cumsum()
        
        # Métricas Finales
        total_bets = test_df['BET_PLACED'].sum()
        total_profit = test_df['PROFIT'].sum()
        roi = (total_profit / (total_bets * unit_size)) * 100 if total_bets > 0 else 0
        win_rate = (test_df[test_df['BET_PLACED'] == 1]['TARGET'] == test_df[test_df['BET_PLACED'] == 1]['PREDICTION']).mean() * 100

        logger.info(f"--- RESULTADOS DE LA SIMULACIÓN ---")
        logger.info(f"Total de juegos en prueba: {len(test_df)}")
        logger.info(f"Apuestas realizadas: {total_bets}")
        logger.info(f"Win Rate en apuestas: {win_rate:.2f}%")
        logger.info(f"Beneficio Total: ${total_profit:.2f}")
        logger.info(f"ROI Estimado: {roi:.2f}%")
        
        # Guardar resultados
        os.makedirs("data/results", exist_ok=True)
        test_df.to_csv("data/results/simulation_results.csv", index=False)
        return test_df

if __name__ == "__main__":
    sim = NBAProfitSim()
    sim.run_simulation()
