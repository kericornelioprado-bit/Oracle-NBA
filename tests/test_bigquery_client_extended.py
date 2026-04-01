import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.utils.bigquery_client import NBABigQueryClient

@pytest.fixture
def mock_bq_client():
    with patch('google.cloud.bigquery.Client') as mock_client:
        with patch.dict('os.environ', {'GCP_PROJECT_ID': 'test-project'}):
            client = NBABigQueryClient()
            client.client = mock_client.return_value
            return client

def test_get_virtual_bankroll_success(mock_bq_client):
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = [MagicMock(current_balance=1500.50)]
    mock_bq_client.client.query.return_value = mock_query_job
    
    balance = mock_bq_client.get_virtual_bankroll()
    assert balance == 1500.50

def test_get_virtual_bankroll_default(mock_bq_client):
    # Caso 1: No hay filas en la tabla
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_bq_client.client.query.return_value = mock_query_job
    
    balance = mock_bq_client.get_virtual_bankroll()
    assert balance == 20000.0 # Default V2

    # Caso 2: Exception
    mock_bq_client.client.query.side_effect = Exception("BQ Error")
    balance = mock_bq_client.get_virtual_bankroll()
    assert balance == 20000.0

def test_get_top_20_portfolio_success(mock_bq_client):
    mock_query_job = MagicMock()
    # Mocking rows directly because NBABigQueryClient iterates over query_job
    row1 = MagicMock()
    row1.player_id = 1
    row2 = MagicMock()
    row2.player_id = 2
    mock_query_job.__iter__.return_value = [row1, row2]
    mock_bq_client.client.query.return_value = mock_query_job
    
    portfolio = mock_bq_client.get_top_20_portfolio()
    assert portfolio == [1, 2]

def test_get_top_20_portfolio_empty(mock_bq_client):
    mock_query_job = MagicMock()
    mock_query_job.__iter__.return_value = []
    mock_bq_client.client.query.return_value = mock_query_job
    
    portfolio = mock_bq_client.get_top_20_portfolio()
    assert portfolio == []

def test_get_top_20_portfolio_no_client():
    with patch.dict('os.environ', {}, clear=True):
        client = NBABigQueryClient()
        assert client.get_top_20_portfolio() == [1629013, 1630162]

def test_insert_prop_bets_success(mock_bq_client):
    mock_bq_client.client.insert_rows_json.return_value = []
    bets = [
        {
            'player_name': 'P1', 
            'market': 'PTS_OVER', 'line': 20.5, 'stake_usd': 100, 
            'odds_open': 1.90
        }
    ]
    result = mock_bq_client.insert_prop_bets(bets)
    assert result is True

def test_insert_prop_bets_no_client():
    with patch.dict('os.environ', {}, clear=True):
        client = NBABigQueryClient()
        assert client.insert_prop_bets([]) is False

def test_insert_prop_bets_errors(mock_bq_client):
    mock_bq_client.client.insert_rows_json.return_value = [{'error': 'failed'}]
    result = mock_bq_client.insert_prop_bets([{'id': 1}])
    assert result is False

def test_insert_predictions_no_client_v2():
    with patch.dict('os.environ', {}, clear=True):
        client = NBABigQueryClient()
        df = pd.DataFrame({'GAME_ID': [1], 'HOME_ID': [10], 'AWAY_ID': [20], 'PROB_HOME_WIN': [0.5], 'RECOMMENDATION': ['HOME']})
        assert client.insert_predictions(df) is False
