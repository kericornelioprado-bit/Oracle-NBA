import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


@pytest.fixture
def app():
    """Crear la app Flask para tests."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import main as app_module
    app_module.app.config['TESTING'] = True
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


def make_predictions_df():
    return pd.DataFrame({
        'GAME_ID': ['0022300001'],
        'HOME_ID': [1610612738],
        'AWAY_ID': [1610612743],
        'PROB_HOME_WIN': [0.63],
        'RECOMMENDATION': ['HOME'],
    })


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_run_oracle_success(client):
    """Endpoint / debe retornar 200 con predicciones."""
    mock_oracle = MagicMock()
    # predict_today ahora retorna TUPLA (ml_df, props_df)
    mock_oracle.predict_today.return_value = (make_predictions_df(), pd.DataFrame())

    with patch('main.NBAOracleInference', return_value=mock_oracle), \
         patch('main.NBABigQueryClient') as mock_bq_cls, \
         patch('main.NBAReportGenerator.generate_html_report', return_value='<html></html>'), \
         patch('main.NBAEmailService') as mock_email_cls:

        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq
        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        response = client.get('/')

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    mock_bq.insert_predictions.assert_called_once()
    mock_email.send_prediction_report.assert_called_once()


def test_run_oracle_no_predictions(client):
    """Cuando no hay partidos debe retornar 200 con status warning y enviar email."""
    mock_oracle = MagicMock()
    # Sin partidos: predict_today retorna (None, None)
    mock_oracle.predict_today.return_value = (None, None)

    with patch('main.NBAOracleInference', return_value=mock_oracle), \
         patch('main.NBABigQueryClient'), \
         patch('main.NBAEmailService') as mock_email_cls:

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        response = client.get('/')

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'warning'
    mock_email.send_email.assert_called_once()


def test_run_oracle_empty_predictions(client):
    """Con DataFrame vacío debe retornar status warning y enviar email."""
    mock_oracle = MagicMock()
    mock_oracle.predict_today.return_value = (pd.DataFrame(), pd.DataFrame())

    with patch('main.NBAOracleInference', return_value=mock_oracle), \
         patch('main.NBABigQueryClient'), \
         patch('main.NBAEmailService') as mock_email_cls:

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        response = client.get('/')

    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'warning'
    mock_email.send_email.assert_called_once()


def test_run_oracle_exception(client):
    """Cuando hay una excepción debe retornar 500 y enviar alerta de error."""
    with patch('main.NBAOracleInference', side_effect=Exception("Error crítico")), \
         patch('main.NBABigQueryClient'), \
         patch('main.NBAEmailService') as mock_email_cls:

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        response = client.get('/')

    assert response.status_code == 500
    data = response.get_json()
    assert data['status'] == 'error'
    mock_email.send_error_alert.assert_called_once()


def test_run_oracle_post_method(client):
    """El endpoint debe aceptar POST también."""
    mock_oracle = MagicMock()
    mock_oracle.predict_today.return_value = (make_predictions_df(), pd.DataFrame())

    with patch('main.NBAOracleInference', return_value=mock_oracle), \
         patch('main.NBABigQueryClient'), \
         patch('main.NBAReportGenerator.generate_html_report', return_value='<html></html>'), \
         patch('main.NBAEmailService') as mock_email_cls:

        mock_email = MagicMock()
        mock_email_cls.return_value = mock_email

        response = client.post('/')

    assert response.status_code == 200


def test_email_service_send_prediction_report():
    """send_prediction_report debe usar el subject correcto y is_html=True."""
    with patch.dict('os.environ', {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'pwd'}):
        from src.utils.email_service import NBAEmailService
        service = NBAEmailService()

    with patch.object(service, 'send_email', return_value=True) as mock_send:
        service.send_prediction_report('<html>test</html>')
        mock_send.assert_called_once()
        call = mock_send.call_args
        subject = call[0][0]
        is_html = call[0][2] if len(call[0]) > 2 else call[1].get('is_html')
        assert 'NBA' in subject
        assert is_html is True


def test_email_service_send_error_alert():
    """send_error_alert debe enviar en modo texto plano."""
    with patch.dict('os.environ', {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'pwd'}):
        from src.utils.email_service import NBAEmailService
        service = NBAEmailService()

    with patch.object(service, 'send_email', return_value=False) as mock_send:
        service.send_error_alert('Traceback ...\nError line')
        mock_send.assert_called_once()
        call = mock_send.call_args
        subject = call[0][0]
        is_html = call[0][2] if len(call[0]) > 2 else call[1].get('is_html', False)
        assert 'ALERT' in subject or 'Fallo' in subject
        assert is_html is False


def test_email_service_smtp_exception():
    """Cuando SMTP lanza excepción debe retornar False."""
    with patch.dict('os.environ', {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'pwd'}):
        from src.utils.email_service import NBAEmailService
        service = NBAEmailService()

    with patch('smtplib.SMTP', side_effect=Exception("SMTP connection failed")):
        result = service.send_email("Subject", "Body")

    assert result is False
