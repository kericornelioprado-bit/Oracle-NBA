import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.data.ingestion import NBADataIngestor
import os

@pytest.fixture
def mock_ingestor(tmp_path):
    """Fixture para crear un ingestor con un path temporal y cliente mockeado."""
    with patch('src.data.ingestion.BallDontLieClient') as mock_bdl_cls:
        mock_bdl = MagicMock()
        mock_bdl_cls.return_value = mock_bdl
        ingestor = NBADataIngestor(raw_data_path=str(tmp_path))
        # Guardamos el mock en el objeto para poder configurar side_effects/returns en cada test
        ingestor.mock_bdl = mock_bdl
        return ingestor

def test_fetch_season_games_success(mock_ingestor):
    """Prueba que el ingestor extraiga juegos de la temporada correctamente."""
    mock_df = pd.DataFrame([
        {'GAME_ID': 1, 'GAME_DATE': '2023-10-24', 'SEASON_ID': 2023, 'TEAM_ID': 1610612743, 'WL': 'W'},
        {'GAME_ID': 1, 'GAME_DATE': '2023-10-24', 'SEASON_ID': 2023, 'TEAM_ID': 1610612747, 'WL': 'L'}
    ])
    mock_ingestor.mock_bdl.get_games.return_value = mock_df

    # Caso 1: String '2023-24'
    result = mock_ingestor.fetch_season_games("2023-24")
    assert len(result) == 2
    mock_ingestor.mock_bdl.get_games.assert_called_with(seasons=[2023])

def test_ingestor_api_error_handling(mock_ingestor):
    """Prueba que el ingestor maneje errores de la API sin romperse."""
    mock_ingestor.mock_bdl.get_games.side_effect = Exception("API Timeout")

    # El método debe devolver None en caso de error y no lanzar la excepción
    result = mock_ingestor.fetch_season_games(2023)
    assert result is None

def test_save_to_parquet(mock_ingestor, tmp_path):
    """Prueba el guardado de datos en formato Parquet."""
    df = pd.DataFrame({'test': [1, 2, 3]})
    filename = "test_data.parquet"
    
    with patch.object(mock_ingestor, 'upload_to_gcs') as mock_upload:
        mock_ingestor.save_to_parquet(df, filename)
        
        expected_path = os.path.join(str(tmp_path), filename)
        assert os.path.exists(expected_path)
        mock_upload.assert_called_once()

@patch('google.cloud.storage.Client')
def test_upload_to_gcs(mock_storage_cls, mock_ingestor):
    """Prueba la subida a GCS."""
    mock_ingestor.bucket_name = "test-bucket"
    mock_client = MagicMock()
    mock_storage_cls.return_value = mock_client
    
    mock_ingestor.upload_to_gcs("local.path", "dest.blob")
    mock_client.bucket.assert_called_with("test-bucket")
