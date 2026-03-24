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
    # Probabilidades formateadas según recomendación
    assert "63.0%" in html
    assert "55.0%" in html # 1 - 0.45 = 0.55 (AWAY win prob)


def test_generate_html_contains_recommendations(predictions_df):
    """El HTML debe contener las recomendaciones correctas."""
    html = NBAReportGenerator.generate_html_report(predictions_df)
    assert "HOME" in html
    assert "AWAY" in html


def test_generate_html_recommendation_css_classes(predictions_df):
    """El HTML debe incluir clases CSS para cada tipo de recomendación."""
    html = NBAReportGenerator.generate_html_report(predictions_df)
    assert "recommendation-HOME" in html
    assert "recommendation-AWAY" in html


def test_generate_html_no_bet_recommendation():
    """Debe manejar la recomendación NO BET correctamente."""
    df = pd.DataFrame({
        'HOME_ID': [1610612738],
        'AWAY_ID': [1610612743],
        'PROB_HOME_WIN': [0.50],
        'ODDS': [1.90],
        'EV': [-0.05],
        'KELLY_PCT': [0.0],
        'UNITS_SUGGESTED': [0.0],
        'BOOKMAKER': ['N/A'],
        'RECOMMENDATION': ['NO BET'],
    })
    html = NBAReportGenerator.generate_html_report(df)
    assert "recommendation-NO_BET" in html
    assert "NO BET" in html


def test_generate_html_contains_team_names(predictions_df):
    """El HTML debe contener los nombres de equipos reales (via mapping)."""
    html = NBAReportGenerator.generate_html_report(predictions_df)
    assert "Boston Celtics" in html
    assert "Denver Nuggets" in html


def test_generate_html_single_game():
    """Con un solo partido debe generar HTML válido con métricas v2."""
    df = pd.DataFrame({
        'HOME_ID': [1610612747],
        'AWAY_ID': [1610612738],
        'PROB_HOME_WIN': [0.55],
        'ODDS': [2.0],
        'EV': [0.10],
        'KELLY_PCT': [0.05],
        'UNITS_SUGGESTED': [50.0],
        'BOOKMAKER': ['Betway'],
        'RECOMMENDATION': ['HOME'],
    })
    html = NBAReportGenerator.generate_html_report(df)
    assert "<tr>" in html
    assert "55.0%" in html
    assert "$50.00" in html
    assert "10.00%" in html # EV formatted
