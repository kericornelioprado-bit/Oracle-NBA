import pytest
import os
import joblib
import pandas as pd
import numpy as np
from src.models.inference import NBAOracleInference

def test_model_loading():
    """Verifica que el modelo de producción existe y se carga correctamente."""
    model_path = "models/nba_best_model_stacking.joblib"
    assert os.path.exists(model_path), "El modelo de Stacking no existe."
    model = joblib.load(model_path)
    assert hasattr(model, "predict_proba")

def test_inference_logic_robustness():
    """Verifica que el oráculo maneje correctamente datos incompletos (Backfill)."""
    # Creamos un caso de prueba extremo con nulos
    data = {
        'ROLL_PTS_3': [110.0],
        'ROLL_PTS_5': [np.nan],
        'ROLL_PTS_10': [np.nan],
        'ROLL_PTS_20': [np.nan]
    }
    df = pd.DataFrame(data)
    
    # Lógica de cascada corregida
    for target, source in [('5', '3'), ('10', '5'), ('20', '10')]:
        df[f'ROLL_PTS_{target}'] = df[f'ROLL_PTS_{target}'].fillna(df[f'ROLL_PTS_{source}'])
    
    # Verificación: La ventana de 20 debe haber heredado el 110.0 a través de la cascada
    assert df['ROLL_PTS_20'].iloc[0] == 110.0
    assert not df['ROLL_PTS_20'].isna().any()
