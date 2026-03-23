import pytest
from unittest.mock import MagicMock, patch
from src.utils.email_service import NBAEmailService

@pytest.fixture
def email_service():
    with patch.dict('os.environ', {'GMAIL_USER': 'test@gmail.com', 'GMAIL_APP_PASSWORD': 'password'}):
        return NBAEmailService()

def test_send_email_success(email_service):
    with patch('smtplib.SMTP') as mock_smtp:
        # Configurar mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = email_service.send_email("Subject", "Body")
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@gmail.com', 'password')
        mock_server.sendmail.assert_called_once()

def test_send_email_no_creds():
    with patch.dict('os.environ', {'GMAIL_USER': '', 'GMAIL_APP_PASSWORD': ''}):
        service = NBAEmailService()
        result = service.send_email("Subject", "Body")
        assert result is False
