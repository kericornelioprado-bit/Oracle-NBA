import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.utils.bdl_client import BallDontLieClient

@pytest.fixture
def bdl_client():
    return BallDontLieClient(api_key="test_key")

@patch('requests.get')
def test_get_games_success(mock_get, bdl_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "id": 1, "date": "2024-01-01T00:00:00", "season": 2024,
                "home_team": {"id": 10, "abbreviation": "ATL"},
                "visitor_team": {"id": 20, "abbreviation": "BOS"},
                "home_team_score": 110, "visitor_team_score": 100
            }
        ],
        "meta": {"next_cursor": None}
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    df = bdl_client.get_games(seasons=2024)
    assert not df.empty
    assert len(df) == 2 # Una fila por equipo
    assert df.iloc[0]['TEAM_ABBREVIATION'] == 'ATL'
    assert df.iloc[1]['TEAM_ABBREVIATION'] == 'BOS'

@patch('requests.get')
def test_get_player_stats_success(mock_get, bdl_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "player": {"id": 1, "first_name": "LeBron", "last_name": "James"},
                "game": {"id": 100, "date": "2024-01-01T00:00:00"},
                "team": {"id": 14, "abbreviation": "LAL"},
                "min": "35:00", "pts": 30, "reb": 10, "ast": 8
            }
        ],
        "meta": {"next_cursor": None}
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    df = bdl_client.get_player_stats(player_ids=[1])
    assert not df.empty
    assert df.iloc[0]['PLAYER_NAME'] == 'LeBron James'
    assert df.iloc[0]['PTS'] == 30

@patch('requests.get')
def test_get_games_pagination(mock_get, bdl_client):
    # Simular dos páginas
    mock_response_1 = MagicMock()
    mock_response_1.json.return_value = {
        "data": [{"id": 1, "date": "2024-01-01T00:00:00", "season": 2024, "home_team": {"id": 1, "abbreviation": "ATL"}, "visitor_team": {"id": 2, "abbreviation": "BOS"}, "home_team_score": 1, "visitor_team_score": 0}],
        "meta": {"next_cursor": 123}
    }
    mock_response_2 = MagicMock()
    mock_response_2.json.return_value = {
        "data": [{"id": 2, "date": "2024-01-01T00:00:00", "season": 2024, "home_team": {"id": 1, "abbreviation": "ATL"}, "visitor_team": {"id": 2, "abbreviation": "BOS"}, "home_team_score": 1, "visitor_team_score": 0}],
        "meta": {"next_cursor": None}
    }
    mock_get.side_effect = [mock_response_1, mock_response_2]

    df = bdl_client.get_games(seasons=2024)
    assert len(df) == 4 # 2 juegos * 2 equipos/juego

@patch('requests.get')
def test_api_error_handling(mock_get, bdl_client):
    mock_get.side_effect = Exception("Connection error")
    
    df_games = bdl_client.get_games(seasons=2024)
    assert df_games.empty
    
    df_stats = bdl_client.get_player_stats(player_ids=[1])
    assert df_stats.empty

def test_client_init_no_key():
    with patch('os.getenv', return_value=None):
        client = BallDontLieClient()
        assert client.api_key is None
        assert client.headers == {}
