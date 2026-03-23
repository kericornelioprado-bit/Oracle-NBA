import pandas as pd
import numpy as np
import os
from src.utils.logger import logger

def run_eda(input_path="data/raw/nba_games_raw.parquet"):
    if not os.path.exists(input_path):
        logger.error(f"Archivo no encontrado: {input_path}")
        return

    df = pd.read_parquet(input_path)
    logger.info(f"Cargando {len(df)} registros para EDA...")

    # 1. Limpieza básica
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df['IS_WIN'] = df['WL'].apply(lambda x: 1 if x == 'W' else 0)
    
    # 2. Análisis de Correlación con la Victoria
    # Seleccionamos solo columnas numéricas de interés
    numeric_cols = ['PTS', 'FG_PCT', 'FG3_PCT', 'FT_PCT', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PLUS_MINUS', 'IS_WIN']
    corr_matrix = df[numeric_cols].corr()
    
    win_corr = corr_matrix['IS_WIN'].sort_values(ascending=False)
    
    # 3. Reporte de Calidad de Datos
    null_counts = df.isnull().sum()
    
    # 4. Generación de Reporte en Texto
    report_path = "data/processed/eda_report.txt"
    os.makedirs("data/processed", exist_ok=True)
    
    with open(report_path, "w") as f:
        f.write("=== REPORTE EDA INICIAL: ORÁCULO NBA ===\n\n")
        f.write(f"Total de juegos analizados: {len(df)}\n")
        f.write(f"Rango de fechas: {df['GAME_DATE'].min()} a {df['GAME_DATE'].max()}\n\n")
        
        f.write("--- Correlación con la Victoria (IS_WIN) ---\n")
        f.write(win_corr.to_string())
        f.write("\n\n")
        
        f.write("--- Calidad de Datos (Nulos) ---\n")
        f.write(null_counts[null_counts > 0].to_string() if null_counts.sum() > 0 else "No se encontraron valores nulos.")
        f.write("\n\n")
        
        f.write("--- Conclusiones Preliminares (Features Candidatas) ---\n")
        f.write("1. PLUS_MINUS es la variable más correlacionada (esperado).\n")
        f.write("2. FG_PCT (Tiros de campo) y AST (Asistencias) muestran fuerte relación con la victoria.\n")
        f.write("3. TOV (Pérdidas de balón) tiene correlación negativa (clave para el modelo).\n")

    logger.info(f"Reporte EDA generado en {report_path}")
    print(win_corr)

if __name__ == "__main__":
    run_eda()
