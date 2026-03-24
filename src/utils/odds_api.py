import os
import requests
from src.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

class OddsAPIClient:
    """Cliente para interactuar con The Odds API."""
    
    BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    
    def __init__(self):
        self.api_key = os.getenv("THE_ODDS_API_KEY")
        self.bookmakers = os.getenv("BOOKMAKERS", "pinnacle,bet365,betway").split(",")
        
        if not self.api_key:
            logger.warning("THE_ODDS_API_KEY no configurada. Las cuotas no estarán disponibles.")

    def get_latest_odds(self):
        """Obtiene las cuotas más recientes para los partidos de hoy."""
        if not self.api_key:
            return None
            
        params = {
            "apiKey": self.api_key,
            "regions": "us,eu", # Cubre la mayoría de las casas populares
            "markets": "h2h",   # Moneyline (Gana Local/Visitante)
            "oddsFormat": "decimal",
            "bookmakers": ",".join(self.bookmakers)
        }
        
        try:
            logger.info("Consultando The Odds API...")
            response = requests.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Se obtuvieron cuotas para {len(data)} eventos.")
            return data
        except Exception as e:
            logger.error(f"Error al consultar The Odds API: {e}")
            return None

    @staticmethod
    def get_best_odds(event_data):
        """Extrae la mejor cuota para local y visitante de un evento específico."""
        best_home_odds = 0
        best_away_odds = 0
        best_home_bookie = ""
        best_away_bookie = ""
        
        home_team = event_data.get("home_team")
        
        for bookmaker in event_data.get("bookmakers", []):
            market = bookmaker.get("markets", [{}])[0]
            outcomes = market.get("outcomes", [])
            
            for outcome in outcomes:
                price = outcome.get("price", 0)
                name = outcome.get("name")
                
                if name == home_team:
                    if price > best_home_odds:
                        best_home_odds = price
                        best_home_bookie = bookmaker.get("title")
                else:
                    if price > best_away_odds:
                        best_away_odds = price
                        best_away_bookie = bookmaker.get("title")
                        
        return {
            "best_home_odds": best_home_odds,
            "best_home_bookie": best_home_bookie,
            "best_away_odds": best_away_odds,
            "best_away_bookie": best_away_bookie
        }
