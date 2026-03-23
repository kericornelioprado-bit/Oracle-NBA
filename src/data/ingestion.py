import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder
from src.utils.logger import logger
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

class NBADataIngestor:
    def __init__(self, raw_data_path="data/raw"):
        self.raw_data_path = raw_data_path
        os.makedirs(self.raw_data_path, exist_ok=True)
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")

    def upload_to_gcs(self, local_file_path, destination_blob_name):
        """Sube un archivo a Google Cloud Storage si el bucket está configurado."""
        if not self.bucket_name:
            logger.info("GCS_BUCKET_NAME no configurado. Saltando subida a la nube.")
            return

        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(local_file_path)
            logger.info(f"Archivo subido a GCS: {self.bucket_name}/{destination_blob_name}")
        except Exception as e:
            logger.error(f"Error al subir a GCS: {str(e)}")

    def fetch_season_games(self, season_year):
        """
        Extrae los juegos de una temporada específica (ej. '2023-24').
        """
        try:
            logger.info(f"Iniciando extracción para la temporada {season_year}...")
            # LeagueGameFinder permite buscar juegos de la temporada regular
            game_finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season_year,
                league_id_nullable='00',  # NBA
                season_type_nullable='Regular Season'
            )
            games = game_finder.get_data_frames()[0]
            logger.info(f"Extracción completada: {len(games)} juegos encontrados.")
            return games
        except Exception as e:
            logger.error(f"Error al extraer temporada {season_year}: {str(e)}")
            return None

    def save_to_parquet(self, df, filename):
        """Guarda el DataFrame en formato Parquet local y sube a GCS."""
        try:
            full_path = os.path.join(self.raw_data_path, filename)
            df.to_parquet(full_path, index=False)
            logger.info(f"Datos guardados localmente en {full_path}")
            
            # Intentar subir a la nube
            self.upload_to_gcs(full_path, f"raw/{filename}")
        except Exception as e:
            logger.error(f"Error al guardar Parquet {filename}: {str(e)}")

    def run_ingestion(self, seasons=None):
        """Ejecuta el pipeline de extracción para varias temporadas."""
        if seasons is None:
            # Por defecto, las últimas 3 temporadas
            seasons = ['2021-22', '2022-23', '2023-24']
        
        all_games = []
        for season in seasons:
            games = self.fetch_season_games(season)
            if games is not None:
                all_games.append(games)
            # Respetar rate limit de la API
            time.sleep(2)
        
        if all_games:
            combined_df = pd.concat(all_games, ignore_index=True)
            self.save_to_parquet(combined_df, "nba_games_raw.parquet")
            return combined_df
        else:
            logger.warning("No se extrajeron datos.")
            return None

if __name__ == "__main__":
    ingestor = NBADataIngestor()
    ingestor.run_ingestion()
