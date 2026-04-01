import pytest
import pandas as pd
from src.utils.report_generator import NBAReportGenerator


@pytest.fixture
def predictions_df():
    return pd.DataFrame({
        'HOME_ID': [1610612738, 1610612745],
        'AWAY_ID': [1610612743, 1610612747],
        'PROB_HOME_WIN': [0.63, 0.45],
        'ODDS': [2.10, 2.50],
        'EV': [0.05, 0.08],
        'KELLY_PCT': [0.02, 0.03],
        'UNITS_SUGGESTED': [20.0, 30.0],
        'BOOKMAKER': ['Bet365', 'Pinnacle'],
        'RECOMMENDATION': ['HOME', 'AWAY'],
    })


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_generate_html_none_input():
    """Con None debe retornar mensaje de sin partidos."""
    html = NBAReportGenerator.generate_html_report(None)
    assert "No hay partidos" in html


def test_generate_html_empty_dataframe():
    """Con DataFrame vacío debe retornar mensaje de sin partidos."""
    html = NBAReportGenerator.generate_html_report(pd.DataFrame())
    assert "No hay partidos" in html


def test_generate_html_valid_data(predictions_df):
    """Con datos válidos debe generar HTML con tabla."""
    html = NBAReportGenerator.generate_html_report(predictions_df)
    assert "<html>" in html
    assert "<table>" in html
    assert "63.0%" in html
    assert "55.0%" in html


def test_generate_props_report_no_data():
    """generate_props_report debe manejar inputs nulos."""
    html = NBAReportGenerator.generate_props_report(None)
    assert "No hay picks" in html


def test_generate_props_report_with_data():
    """Debe generar reporte de Props."""
    props_df = pd.DataFrame({
        'player_name': ['LeBron James'], 'market': ['PTS_OVER'],
        'line': [25.5], 'odds_open': [1.90], 'ev': [0.15], 'kelly_pct': [0.05],
        'stake_usd': [100.0], 'bookmaker': 'DraftKings'
    })
    html = NBAReportGenerator.generate_props_report(props_df)
    assert "LeBron James" in html
    assert "PTS_OVER" in html
    assert "25.5" in html
    assert "15.00%" in html
