import os
import json
import pandas as pd
import requests
from src.shared.bdl_client import BallDontLieClient
from src.shared.logger import logger
from dotenv import load_dotenv

load_dotenv()

def explore_mlb_api_quick():
    """Explora una sola página de cada endpoint para ver la estructura."""
    client = BallDontLieClient(sport='mlb')
    headers = {"Authorization": client.api_key}
    
    endpoints = {
        "stats": "https://api.balldontlie.io/mlb/v1/stats?seasons[]=2024&per_page=10",
        "season_stats": "https://api.balldontlie.io/mlb/v1/season_stats?season=2024&per_page=5",
        "player_splits": "https://api.balldontlie.io/mlb/v1/player_splits?season=2024&player_id=643338&per_page=5" # Ohtani ID approx or similar
    }
    
    os.makedirs('docs/mlb/api_samples', exist_ok=True)

    for name, url in endpoints.items():
        logger.info(f"⚾ Fetching sample: {name}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json().get("data", [])
            
            with open(f'docs/mlb/api_samples/{name}_sample.json', 'w') as f:
                json.dump(data[:5], f, indent=2)
            logger.info(f"✅ Guardado sample de {name}.")
        except Exception as e:
            logger.error(f"Error en {name}: {e}")

if __name__ == "__main__":
    explore_mlb_api_quick()
