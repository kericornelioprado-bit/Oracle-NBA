import pytest
from unittest.mock import MagicMock, patch
from src.utils.odds_api import OddsAPIClient


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture
def client_with_key(monkeypatch):
    monkeypatch.setenv('THE_ODDS_API_KEY', 'test-key-123')
    monkeypatch.setenv('BOOKMAKERS', 'pinnacle,bet365')
    return OddsAPIClient()


@pytest.fixture
def client_no_key(monkeypatch):
    monkeypatch.delenv('THE_ODDS_API_KEY', raising=False)
    return OddsAPIClient()


def make_event_data():
    return {
        "id": "event_001",
        "home_team": "Boston Celtics",
        "away_team": "Miami Heat",
        "bookmakers": [
            {
                "key": "pinnacle",
                "title": "Pinnacle",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Boston Celtics", "price": 1.85},
                            {"name": "Miami Heat", "price": 2.05},
                        ]
                    }
                ]
            },
            {
                "key": "bet365",
                "title": "Bet365",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Boston Celtics", "price": 1.90},
                            {"name": "Miami Heat", "price": 2.00},
                        ]
                    }
                ]
            }
        ]
    }


# --------------------------------------------------------------------------- #
# __init__                                                                     #
# --------------------------------------------------------------------------- #

def test_init_no_api_key(client_no_key):
    """Sin API key, el atributo api_key debe ser None."""
    assert client_no_key.api_key is None


def test_init_with_api_key(client_with_key):
    """Con API key, el atributo api_key debe estar configurado."""
    assert client_with_key.api_key == 'test-key-123'


def test_init_bookmakers_default(monkeypatch):
    """Sin variable BOOKMAKERS, usa la lista por defecto."""
    monkeypatch.setenv('THE_ODDS_API_KEY', 'key')
    monkeypatch.delenv('BOOKMAKERS', raising=False)
    client = OddsAPIClient()
    assert 'pinnacle' in client.bookmakers
    assert 'bet365' in client.bookmakers
    assert 'betway' in client.bookmakers


def test_init_bookmakers_custom(client_with_key):
    """BOOKMAKERS custom se parsea correctamente."""
    assert client_with_key.bookmakers == ['pinnacle', 'bet365']


# --------------------------------------------------------------------------- #
# get_latest_odds                                                               #
# --------------------------------------------------------------------------- #

def test_get_latest_odds_no_key_returns_none(client_no_key):
    """Sin API key, devuelve None sin hacer ninguna petición."""
    with patch('requests.get') as mock_get:
        result = client_no_key.get_latest_odds()
    mock_get.assert_not_called()
    assert result is None


def test_get_latest_odds_success(client_with_key):
    """Respuesta 200 devuelve la lista de eventos JSON."""
    mock_response = MagicMock()
    mock_response.json.return_value = [make_event_data()]
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get:
        result = client_with_key.get_latest_odds()

    mock_get.assert_called_once()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['home_team'] == 'Boston Celtics'


def test_get_latest_odds_includes_api_key_in_params(client_with_key):
    """La petición debe incluir apiKey en los parámetros."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get:
        client_with_key.get_latest_odds()

    call_kwargs = mock_get.call_args
    params = call_kwargs[1].get('params') or call_kwargs[0][1]
    assert params['apiKey'] == 'test-key-123'


def test_get_latest_odds_request_error_returns_none(client_with_key):
    """Si requests.get lanza excepción, devuelve None."""
    with patch('requests.get', side_effect=Exception("Connection timeout")):
        result = client_with_key.get_latest_odds()
    assert result is None


def test_get_latest_odds_http_error_returns_none(client_with_key):
    """Si raise_for_status lanza HTTPError, devuelve None."""
    import requests
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

    with patch('requests.get', return_value=mock_response):
        result = client_with_key.get_latest_odds()
    assert result is None


# --------------------------------------------------------------------------- #
# get_player_props                                                              #
# --------------------------------------------------------------------------- #

def test_get_player_props_no_key_returns_none(client_no_key):
    """Sin API key, devuelve None."""
    with patch('requests.get') as mock_get:
        result = client_no_key.get_player_props('event_001')
    mock_get.assert_not_called()
    assert result is None


def test_get_player_props_success(client_with_key):
    """Respuesta 200 devuelve el JSON de props."""
    props_data = {'id': 'event_001', 'bookmakers': []}
    mock_response = MagicMock()
    mock_response.json.return_value = props_data
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response):
        result = client_with_key.get_player_props('event_001')

    assert result == props_data


def test_get_player_props_uses_event_id_in_url(client_with_key):
    """La URL debe incluir el event_id."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get:
        client_with_key.get_player_props('event_abc_123')

    call_url = mock_get.call_args[0][0]
    assert 'event_abc_123' in call_url


def test_get_player_props_error_returns_none(client_with_key):
    """Excepción en la petición devuelve None."""
    with patch('requests.get', side_effect=Exception("Timeout")):
        result = client_with_key.get_player_props('event_001')
    assert result is None


# --------------------------------------------------------------------------- #
# get_best_odds (método estático)                                               #
# --------------------------------------------------------------------------- #

def test_get_best_odds_selects_highest_home_price():
    """Debe devolver la cuota más alta para el local entre todas las casas."""
    event = make_event_data()
    result = OddsAPIClient.get_best_odds(event)
    # Pinnacle: 1.85, Bet365: 1.90 → mejor = 1.90
    assert result['best_home_odds'] == pytest.approx(1.90)


def test_get_best_odds_selects_highest_away_price():
    """Debe devolver la cuota más alta para el visitante."""
    event = make_event_data()
    result = OddsAPIClient.get_best_odds(event)
    # Pinnacle: 2.05, Bet365: 2.00 → mejor = 2.05
    assert result['best_away_odds'] == pytest.approx(2.05)


def test_get_best_odds_returns_correct_bookmaker_names():
    """Deve retornar el nombre del bookmaker con la mejor cuota."""
    event = make_event_data()
    result = OddsAPIClient.get_best_odds(event)
    assert result['best_home_bookie'] == 'Bet365'
    assert result['best_away_bookie'] == 'Pinnacle'


def test_get_best_odds_empty_bookmakers():
    """Sin bookmakers, todas las cuotas deben ser 0."""
    event = {'home_team': 'Team A', 'bookmakers': []}
    result = OddsAPIClient.get_best_odds(event)
    assert result['best_home_odds'] == 0
    assert result['best_away_odds'] == 0
    assert result['best_home_bookie'] == ''
    assert result['best_away_bookie'] == ''


def test_get_best_odds_single_bookmaker():
    """Con un solo bookmaker, devuelve sus cuotas."""
    event = {
        'home_team': 'Lakers',
        'bookmakers': [
            {
                'title': 'DraftKings',
                'markets': [
                    {
                        'outcomes': [
                            {'name': 'Lakers', 'price': 2.10},
                            {'name': 'Celtics', 'price': 1.75},
                        ]
                    }
                ]
            }
        ]
    }
    result = OddsAPIClient.get_best_odds(event)
    assert result['best_home_odds'] == pytest.approx(2.10)
    assert result['best_home_bookie'] == 'DraftKings'
