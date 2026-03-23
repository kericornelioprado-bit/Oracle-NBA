import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


def make_games_df():
    return pd.DataFrame({
        'GAME_ID': ['001', '002', '003'],
        'TEAM_ID': [1, 2, 3],
        'WL': ['W', 'L', 'W'],
        'PTS': [110, 105, 115],
        'GAME_DATE': ['2023-01-01', '2023-01-02', '2023-01-03'],
    })


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #
def test_upload_to_gcs_skipped_when_no_bucket(tmp_path):
    """Si GCS_BUCKET_NAME no está configurado, no debe intentar subir."""
    with patch.dict('os.environ', {}, clear=True):
        from src.data.ingestion import NBADataIngestor
        ingestor = NBADataIngestor(raw_data_path=str(tmp_path))
        ingestor.bucket_name = None

    with patch('google.cloud.storage.Client') as mock_storage:
        ingestor.upload_to_gcs("/some/file.parquet", "raw/file.parquet")
        mock_storage.assert_not_called()


def test_upload_to_gcs_success(tmp_path):
    """Debe llamar a blob.upload_from_filename cuando el bucket está configurado."""
    local_file = tmp_path / "test.parquet"
    local_file.touch()

    with patch.dict('os.environ', {'GCS_BUCKET_NAME': 'my-test-bucket'}):
        from src.data.ingestion import NBADataIngestor
        ingestor = NBADataIngestor(raw_data_path=str(tmp_path))

    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage_client = MagicMock()
    mock_storage_client.bucket.return_value = mock_bucket

    with patch('google.cloud.storage.Client', return_value=mock_storage_client):
        ingestor.upload_to_gcs(str(local_file), "raw/test.parquet")

    mock_blob.upload_from_filename.assert_called_once_with(str(local_file))


def test_upload_to_gcs_error_handling(tmp_path):
    """Debe manejar excepciones de GCS sin propagar el error."""
    with patch.dict('os.environ', {'GCS_BUCKET_NAME': 'my-test-bucket'}):
        from src.data.ingestion import NBADataIngestor
        ingestor = NBADataIngestor(raw_data_path=str(tmp_path))

    with patch('google.cloud.storage.Client', side_effect=Exception("GCS error")):
        # No debe lanzar excepción
        ingestor.upload_to_gcs("/some/file.parquet", "raw/file.parquet")


def test_run_ingestion_with_successful_seasons(tmp_path):
    """run_ingestion debe combinar datos de múltiples temporadas y guardarlos."""
    from src.data.ingestion import NBADataIngestor
    ingestor = NBADataIngestor(raw_data_path=str(tmp_path))
    games_df = make_games_df()

    with patch.object(ingestor, 'fetch_season_games', return_value=games_df), \
         patch.object(ingestor, 'save_to_parquet') as mock_save, \
         patch('time.sleep'):
        result = ingestor.run_ingestion(seasons=['2023-24', '2022-23'])

    assert result is not None
    assert len(result) == 6  # 3 games * 2 seasons
    mock_save.assert_called_once()


def test_run_ingestion_all_seasons_fail(tmp_path):
    """Si todas las temporadas fallan, debe retornar None."""
    from src.data.ingestion import NBADataIngestor
    ingestor = NBADataIngestor(raw_data_path=str(tmp_path))

    with patch.object(ingestor, 'fetch_season_games', return_value=None), \
         patch('time.sleep'):
        result = ingestor.run_ingestion(seasons=['2023-24', '2022-23'])

    assert result is None


def test_run_ingestion_partial_failure(tmp_path):
    """Si solo algunas temporadas fallan, debe combinar las exitosas."""
    from src.data.ingestion import NBADataIngestor
    ingestor = NBADataIngestor(raw_data_path=str(tmp_path))
    games_df = make_games_df()

    call_count = [0]

    def fetch_side_effect(season):
        call_count[0] += 1
        return games_df if call_count[0] == 1 else None

    with patch.object(ingestor, 'fetch_season_games', side_effect=fetch_side_effect), \
         patch.object(ingestor, 'save_to_parquet'), \
         patch('time.sleep'):
        result = ingestor.run_ingestion(seasons=['2023-24', '2022-23'])

    assert result is not None
    assert len(result) == 3


def test_run_ingestion_default_seasons(tmp_path):
    """Sin especificar temporadas debe usar las 3 por defecto."""
    from src.data.ingestion import NBADataIngestor
    ingestor = NBADataIngestor(raw_data_path=str(tmp_path))

    fetched_seasons = []

    def capture_season(season):
        fetched_seasons.append(season)
        return None

    with patch.object(ingestor, 'fetch_season_games', side_effect=capture_season), \
         patch('time.sleep'):
        ingestor.run_ingestion()

    assert '2021-22' in fetched_seasons
    assert '2022-23' in fetched_seasons
    assert '2023-24' in fetched_seasons


def test_save_to_parquet_calls_upload(tmp_path):
    """save_to_parquet debe intentar subir a GCS tras guardar localmente."""
    from src.data.ingestion import NBADataIngestor
    raw_path = tmp_path / "raw"
    raw_path.mkdir()
    ingestor = NBADataIngestor(raw_data_path=str(raw_path))

    with patch.object(ingestor, 'upload_to_gcs') as mock_upload:
        ingestor.save_to_parquet(make_games_df(), "test.parquet")

    mock_upload.assert_called_once()
