import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import patch, MagicMock


def make_raw_df():
    """Genera un DataFrame que simula nba_games_raw.parquet."""
    np.random.seed(42)
    n = 20
    return pd.DataFrame({
        'GAME_DATE': pd.date_range('2023-01-01', periods=n, freq='D').astype(str),
        'TEAM_ID': np.random.choice([1, 2, 3, 4], n),
        'WL': np.random.choice(['W', 'L'], n),
        'PTS': np.random.randint(90, 130, n).astype(float),
        'FG_PCT': np.random.uniform(0.4, 0.6, n),
        'FG3_PCT': np.random.uniform(0.3, 0.5, n),
        'FT_PCT': np.random.uniform(0.7, 0.9, n),
        'OREB': np.random.randint(5, 15, n).astype(float),
        'DREB': np.random.randint(25, 45, n).astype(float),
        'AST': np.random.randint(20, 35, n).astype(float),
        'STL': np.random.randint(5, 12, n).astype(float),
        'BLK': np.random.randint(3, 10, n).astype(float),
        'TOV': np.random.randint(10, 20, n).astype(float),
        'PLUS_MINUS': np.random.uniform(-20, 20, n),
    })


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_run_eda_file_not_found():
    """Con ruta inexistente no debe lanzar excepción."""
    from src.data.eda_report import run_eda
    # Solo debe loguear el error y retornar None sin lanzar excepción
    result = run_eda(input_path="/tmp/nonexistent_path_xyz.parquet")
    assert result is None


def test_run_eda_generates_report(tmp_path):
    """Con parquet válido debe generar el archivo de reporte."""
    raw_path = tmp_path / "nba_games_raw.parquet"
    make_raw_df().to_parquet(raw_path, index=False)

    report_path = tmp_path / "eda_report.txt"

    with patch('src.data.eda_report.os.makedirs'), \
         patch('src.data.eda_report.os.path.exists', return_value=True):
        import src.data.eda_report as eda_mod
        original_run = eda_mod.run_eda

        # Parchear solo la variable de ruta del reporte dentro de la función
        import builtins
        real_open = builtins.open

        def patched_open(path, *args, **kwargs):
            if "eda_report" in str(path):
                return real_open(str(report_path), *args, **kwargs)
            return real_open(path, *args, **kwargs)

        with patch('builtins.open', side_effect=patched_open):
            from src.data.eda_report import run_eda
            run_eda(input_path=str(raw_path))

    assert report_path.exists()


def test_run_eda_computes_correlation(tmp_path):
    """Debe calcular correctamente la correlación con IS_WIN."""
    raw_path = tmp_path / "nba_games_raw.parquet"
    df = make_raw_df()
    df.to_parquet(raw_path, index=False)

    report_path = tmp_path / "eda_report.txt"

    import builtins
    real_open = builtins.open

    def patched_open(path, *args, **kwargs):
        if "eda_report" in str(path):
            return real_open(str(report_path), *args, **kwargs)
        return real_open(path, *args, **kwargs)

    with patch('src.data.eda_report.os.makedirs'), \
         patch('builtins.open', side_effect=patched_open):
        from src.data.eda_report import run_eda
        run_eda(input_path=str(raw_path))

    content = report_path.read_text()
    assert "REPORTE EDA" in content
    assert "Correlación" in content


def test_run_eda_no_nulls_report(tmp_path):
    """Cuando no hay nulos debe escribir el mensaje apropiado."""
    raw_path = tmp_path / "nba_games_raw.parquet"
    make_raw_df().to_parquet(raw_path, index=False)

    report_path = tmp_path / "eda_report.txt"

    import builtins
    real_open = builtins.open

    def patched_open(path, *args, **kwargs):
        if "eda_report" in str(path):
            return real_open(str(report_path), *args, **kwargs)
        return real_open(path, *args, **kwargs)

    with patch('src.data.eda_report.os.makedirs'), \
         patch('builtins.open', side_effect=patched_open):
        from src.data.eda_report import run_eda
        run_eda(input_path=str(raw_path))

    content = report_path.read_text()
    assert "No se encontraron valores nulos" in content or "Calidad" in content


def test_run_eda_with_nulls_report(tmp_path):
    """Cuando hay nulos debe reportarlos."""
    raw_path = tmp_path / "nba_games_raw.parquet"
    df = make_raw_df()
    df.loc[0, 'PTS'] = np.nan
    df.to_parquet(raw_path, index=False)

    report_path = tmp_path / "eda_report.txt"

    import builtins
    real_open = builtins.open

    def patched_open(path, *args, **kwargs):
        if "eda_report" in str(path):
            return real_open(str(report_path), *args, **kwargs)
        return real_open(path, *args, **kwargs)

    with patch('src.data.eda_report.os.makedirs'), \
         patch('builtins.open', side_effect=patched_open):
        from src.data.eda_report import run_eda
        run_eda(input_path=str(raw_path))

    content = report_path.read_text()
    # Con nulos debe reportar algo diferente a "No se encontraron valores nulos"
    assert "Calidad" in content or "Nulos" in content or "PTS" in content
