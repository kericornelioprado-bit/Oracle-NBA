import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


def make_predictions_df():
    return pd.DataFrame({
        'GAME_ID': ['0022300001', '0022300002'],
        'HOME_ID': [1610612738, 1610612745],
        'AWAY_ID': [1610612743, 1610612747],
        'PROB_HOME_WIN': [0.63, 0.45],
        'RECOMMENDATION': ['HOME', 'AWAY'],
    })


# --------------------------------------------------------------------------- #
# Fixture: client sin credenciales GCP                                        #
# --------------------------------------------------------------------------- #
@pytest.fixture
def client_no_creds():
    with patch.dict('os.environ', {}, clear=True):
        from src.utils.bigquery_client import NBABigQueryClient
        return NBABigQueryClient()


# --------------------------------------------------------------------------- #
# Fixture: client con credenciales GCP mockeadas                               #
# --------------------------------------------------------------------------- #
@pytest.fixture
def client_with_creds():
    with patch.dict('os.environ', {'GCP_PROJECT_ID': 'test-project'}):
        with patch('google.cloud.bigquery.Client') as mock_bq:
            mock_bq.return_value = MagicMock()
            from importlib import reload
            import src.utils.bigquery_client as bqmod
            reload(bqmod)
            client = bqmod.NBABigQueryClient()
            client.client = mock_bq.return_value
            yield client


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_init_without_gcp_project_id():
    """Sin GCP_PROJECT_ID, el cliente interno debe ser None."""
    with patch.dict('os.environ', {}, clear=True):
        from importlib import reload
        import src.utils.bigquery_client as bqmod
        with patch('google.cloud.bigquery.Client') as mock_bq:
            client = bqmod.NBABigQueryClient()
            # client.client debe ser None porque project_id es None
            assert client.client is None


def test_insert_predictions_no_client(client_no_creds):
    """Debe retornar False cuando no hay cliente BQ configurado."""
    result = client_no_creds.insert_predictions(make_predictions_df())
    assert result is False


def test_insert_predictions_success(client_with_creds):
    """Debe retornar True cuando BQ no reporta errores."""
    client_with_creds.client.insert_rows_json.return_value = []
    result = client_with_creds.insert_predictions(make_predictions_df())
    assert result is True
    client_with_creds.client.insert_rows_json.assert_called_once()


def test_insert_predictions_bq_errors(client_with_creds):
    """Debe retornar False cuando BQ reporta errores de inserción."""
    client_with_creds.client.insert_rows_json.return_value = [{'index': 0, 'errors': ['bad row']}]
    result = client_with_creds.insert_predictions(make_predictions_df())
    assert result is False


def test_insert_predictions_exception(client_with_creds):
    """Debe retornar False cuando se lanza una excepción inesperada."""
    client_with_creds.client.insert_rows_json.side_effect = Exception("Conexión fallida")
    result = client_with_creds.insert_predictions(make_predictions_df())
    assert result is False


def test_insert_predictions_row_structure(client_with_creds):
    """Las filas insertadas deben tener la estructura correcta."""
    captured_rows = []

    def capture(table_ref, rows):
        captured_rows.extend(rows)
        return []

    client_with_creds.client.insert_rows_json.side_effect = capture
    client_with_creds.insert_predictions(make_predictions_df(), model_version="v2", experiment_id="exp_1")

    assert len(captured_rows) == 2
    row = captured_rows[0]
    assert 'game_id' in row
    assert 'game_date' in row
    assert 'home_team_id' in row
    assert 'away_team_id' in row
    assert 'prob_home_win' in row
    assert 'recommendation' in row
    assert row['model_version'] == 'v2'
    assert row['experiment_id'] == 'exp_1'


def test_insert_predictions_custom_version(client_with_creds):
    """Debe usar el model_version personalizado en los datos insertados."""
    client_with_creds.client.insert_rows_json.return_value = []
    result = client_with_creds.insert_predictions(
        make_predictions_df(), model_version="stacking_v2", experiment_id="run_42"
    )
    assert result is True
    call_args = client_with_creds.client.insert_rows_json.call_args
    rows = call_args[0][1]
    assert rows[0]['model_version'] == 'stacking_v2'
    assert rows[0]['experiment_id'] == 'run_42'

# --------------------------------------------------------------------------- #
# Tests V2                                                                     #
# --------------------------------------------------------------------------- #

def test_get_virtual_bankroll_success(client_with_creds):
    mock_job = MagicMock()
    mock_job.result.return_value = [MagicMock(current_balance=25000.5)]
    client_with_creds.client.query.return_value = mock_job
    
    result = client_with_creds.get_virtual_bankroll()
    assert result == 25000.5

def test_get_virtual_bankroll_empty(client_with_creds):
    mock_job = MagicMock()
    mock_job.result.return_value = []
    client_with_creds.client.query.return_value = mock_job
    
    result = client_with_creds.get_virtual_bankroll()
    assert result == 20000.0

def test_get_virtual_bankroll_exception(client_with_creds):
    client_with_creds.client.query.side_effect = Exception("Query error")
    result = client_with_creds.get_virtual_bankroll()
    assert result == 20000.0

def test_insert_prop_bets_success(client_with_creds):
    client_with_creds.client.insert_rows_json.return_value = []
    bets = [{'player_name': 'Test', 'market': 'PTS_OVER', 'line': 20.5, 'odds_open': 1.90, 'stake_usd': 100}]
    result = client_with_creds.insert_prop_bets(bets)
    assert result is True

def test_insert_prop_bets_errors(client_with_creds):
    client_with_creds.client.insert_rows_json.return_value = [{'error': 'failed'}]
    bets = [{'player_name': 'Test'}]
    result = client_with_creds.insert_prop_bets(bets)
    assert result is False

def test_insert_prop_bets_exception(client_with_creds):
    client_with_creds.client.insert_rows_json.side_effect = Exception("BQ error")
    bets = [{'player_name': 'Test'}]
    result = client_with_creds.insert_prop_bets(bets)
    assert result is False

def test_get_top_20_portfolio_success(client_with_creds):
    client_with_creds.client.query.return_value = [MagicMock(player_id=10), MagicMock(player_id=20)]
    result = client_with_creds.get_top_20_portfolio()
    assert result == [10, 20]

def test_get_top_20_portfolio_exception(client_with_creds):
    client_with_creds.client.query.side_effect = Exception("BQ error")
    result = client_with_creds.get_top_20_portfolio()
    assert result == []
