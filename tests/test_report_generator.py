import pytest
import pandas as pd
from src.utils.report_generator import NBAReportGenerator


@pytest.fixture
def predictions_df():
    return pd.DataFrame({
        'HOME_ID': [1610612738, 1610612745],
        'AWAY_ID': [1610612743, 1610612747],
        'PROB_HOME_WIN': [0.63, 0.45],
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
    assert "63.00%" in html
    assert "45.00%" in html


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


def test_generate_html_skip_recommendation():
    """Debe manejar la recomendación SKIP correctamente."""
    df = pd.DataFrame({
        'HOME_ID': [1610612738],
        'AWAY_ID': [1610612743],
        'PROB_HOME_WIN': [0.50],
        'RECOMMENDATION': ['SKIP'],
    })
    html = NBAReportGenerator.generate_html_report(df)
    assert "recommendation-SKIP" in html
    assert "SKIP" in html


def test_generate_html_contains_team_ids(predictions_df):
    """El HTML debe contener los IDs de equipos."""
    html = NBAReportGenerator.generate_html_report(predictions_df)
    assert "1610612738" in html
    assert "1610612743" in html


def test_generate_html_single_game():
    """Con un solo partido debe generar HTML válido."""
    df = pd.DataFrame({
        'HOME_ID': [1610612747],
        'AWAY_ID': [1610612738],
        'PROB_HOME_WIN': [0.55],
        'RECOMMENDATION': ['HOME'],
    })
    html = NBAReportGenerator.generate_html_report(df)
    assert "<tr>" in html
    assert "55.00%" in html
