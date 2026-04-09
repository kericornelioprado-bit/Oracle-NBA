import os
import requests
from src.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

_PROPS_MARKETS = "player_points,player_rebounds,player_assists,player_threes"
_PROPS_BOOKMAKERS = "draftkings,fanduel,betmgm"  # US books con cobertura de props NBA
_MARKET_TO_STAT = {
    "player_points":   "PTS",
    "player_rebounds": "REB",
    "player_assists":  "AST",
    "player_threes":   "3PM",
}


class OddsAPIClient:
    """Cliente para interactuar con The Odds API v4."""

    _BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"

    def __init__(self):
        self.api_key = os.getenv("THE_ODDS_API_KEY")
        self.bookmakers = os.getenv("BOOKMAKERS", "pinnacle,bet365,betway").split(",")

        if not self.api_key:
            logger.warning("THE_ODDS_API_KEY no configurada. Las cuotas no estarán disponibles.")

    # ------------------------------------------------------------------
    # Métodos base
    # ------------------------------------------------------------------

    def get_events(self):
        """Lista los eventos NBA de hoy (solo metadata, sin cuotas — cuota baja)."""
        if not self.api_key:
            return []
        try:
            logger.info("Consultando eventos NBA del día...")
            resp = requests.get(
                f"{self._BASE}/events",
                params={"apiKey": self.api_key},
                timeout=20,
            )
            resp.raise_for_status()
            events = resp.json()
            logger.info(f"{len(events)} eventos NBA encontrados hoy.")
            self._log_quota(resp)
            return events
        except Exception as e:
            logger.error(f"Error al obtener eventos: {e}")
            return []

    def get_latest_odds(self):
        """Cuotas moneyline (h2h) para los partidos de hoy."""
        if not self.api_key:
            return None
        try:
            logger.info("Consultando The Odds API (Moneyline)...")
            resp = requests.get(
                f"{self._BASE}/odds",
                params={
                    "apiKey": self.api_key,
                    "regions": "us,eu",
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                    "bookmakers": ",".join(self.bookmakers),
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Cuotas ML obtenidas para {len(data)} eventos.")
            self._log_quota(resp)
            return data
        except Exception as e:
            logger.error(f"Error al consultar cuotas ML: {e}")
            return None

    def get_player_props(self, event_id, markets=_PROPS_MARKETS):
        """Cuotas de player props para un evento específico."""
        if not self.api_key:
            return None
        try:
            logger.info(f"Consultando Props para evento {event_id}...")
            resp = requests.get(
                f"{self._BASE}/events/{event_id}/odds",
                params={
                    "apiKey": self.api_key,
                    "regions": "us",
                    "markets": markets,
                    "oddsFormat": "decimal",
                    "bookmakers": _PROPS_BOOKMAKERS,
                },
                timeout=20,
            )
            resp.raise_for_status()
            self._log_quota(resp)
            return resp.json()
        except Exception as e:
            logger.error(f"Error al consultar Props para {event_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Método de conveniencia: agrega todos los props del día en un solo dict
    # ------------------------------------------------------------------

    def get_all_player_props_today(self):
        """
        Devuelve un dict consolidado con los mejores Over de cada jugador:
            {
                "lebron james": {
                    "PTS": {"line": 25.5, "odds": 1.87, "bookmaker": "Pinnacle"},
                    "REB": {...},
                }
            }
        Itera todos los eventos de hoy y elige la mejor cuota Over por stat.
        """
        events = self.get_events()
        if not events:
            return {}

        result: dict = {}

        for event in events:
            event_id = event.get("id")
            if not event_id:
                continue

            props_data = self.get_player_props(event_id)
            if not props_data:
                continue

            for bookmaker in props_data.get("bookmakers", []):
                bookie_title = bookmaker.get("title", "")
                for market in bookmaker.get("markets", []):
                    stat = _MARKET_TO_STAT.get(market.get("key", ""))
                    if not stat:
                        continue
                    for outcome in market.get("outcomes", []):
                        # API format: name="Over"/"Under", description=player name
                        if outcome.get("name", "").lower() != "over":
                            continue
                        player_key = outcome.get("description", "").lower()
                        price = float(outcome.get("price", 0.0))
                        point = float(outcome.get("point", 0.0))
                        if not player_key or price <= 1.0:
                            continue

                        player_entry = result.setdefault(player_key, {})
                        existing = player_entry.get(stat)
                        if not existing or price > existing["odds"]:
                            player_entry[stat] = {
                                "line": point,
                                "odds": price,
                                "bookmaker": bookie_title,
                            }

        logger.info(f"Props consolidados para {len(result)} jugadores.")
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_quota(response):
        remaining = response.headers.get("x-requests-remaining")
        used = response.headers.get("x-requests-used")
        if remaining is not None:
            logger.info(f"Odds API quota — usado: {used}, restante: {remaining}")

    @staticmethod
    def get_best_odds(event_data):
        """Extrae la mejor cuota moneyline para local y visitante de un evento."""
        best_home_odds = 0
        best_away_odds = 0
        best_home_bookie = ""
        best_away_bookie = ""

        home_team = event_data.get("home_team", "").lower().strip()

        for bookmaker in event_data.get("bookmakers", []):
            market = bookmaker.get("markets", [{}])[0]
            outcomes = market.get("outcomes", [])

            for outcome in outcomes:
                price = outcome.get("price", 0)
                name = outcome.get("name", "").lower().strip()

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
            "best_away_bookie": best_away_bookie,
        }
