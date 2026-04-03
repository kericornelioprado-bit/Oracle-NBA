import requests
import time
import pandas as pd
from src.utils.logger import logger
import os
from dotenv import load_dotenv

load_dotenv()

class BallDontLieClient:
    """
    Cliente para interactuar con la API de BallDontLie (balldontlie.io).
    Maneja la paginación y el mapeo de datos al formato esperado por el Oráculo.
    """
    BASE_URL = "https://api.balldontlie.io/v1"
    
    TEAM_MAP = {
        "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739, "NOP": 1610612740,
        "CHI": 1610612741, "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
        "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747, "MIA": 1610612748,
        "MIL": 1610612749, "MIN": 1610612750, "BKN": 1610612751, "NYK": 1610612752,
        "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755, "PHX": 1610612756,
        "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "OKC": 1610612760,
        "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763, "WAS": 1610612764,
        "DET": 1610612765, "CHA": 1610612766
    }
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("BDL_API_KEY")
        self.headers = {"Authorization": self.api_key} if self.api_key else {}
        if not self.api_key:
            logger.warning("BDL_API_KEY no configurado. Usando límites de nivel gratuito.")

    def get_games(self, seasons=None, start_date=None, end_date=None, team_ids=None):
        """Obtiene juegos y los mapea al formato nba_api."""
        params = {"per_page": 100}
        if seasons: params["seasons[]"] = seasons if isinstance(seasons, list) else [seasons]
        if start_date: params["dates[]"] = [start_date] if isinstance(start_date, str) else start_date

        all_games = []
        cursor = None
        while True:
            if cursor: params["cursor"] = cursor
            try:
                response = requests.get(f"{self.BASE_URL}/games", params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                all_games.extend(data.get("data", []))
                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor: break
                time.sleep(1.5 if not self.api_key else 0.05)
            except Exception as e:
                logger.error(f"Error /games: {e}")
                break
        
        return self._map_games_to_nba_api_format(all_games) if all_games else pd.DataFrame()

    def get_player_stats(self, seasons=None, player_ids=None, start_date=None, end_date=None):
        """Obtiene stats de jugadores y las mapea."""
        params = {"per_page": 100}
        if seasons: params["seasons[]"] = seasons if isinstance(seasons, list) else [seasons]
        if player_ids: params["player_ids[]"] = player_ids if isinstance(player_ids, list) else [player_ids]
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date

        all_stats = []
        cursor = None
        while True:
            if cursor: params["cursor"] = cursor
            try:
                response = requests.get(f"{self.BASE_URL}/stats", params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                all_stats.extend(data.get("data", []))
                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor: break
                time.sleep(1.5 if not self.api_key else 0.05)
            except Exception as e:
                logger.error(f"Error /stats: {e}")
                break
        
        return self._map_stats_to_nba_api_format(all_stats) if all_stats else pd.DataFrame()

    def _map_games_to_nba_api_format(self, bdl_games):
        mapped = []
        for g in bdl_games:
            common = {"GAME_ID": str(g["id"]), "GAME_DATE": g["date"].split("T")[0], "SEASON_ID": str(g["season"])}
            h_abbr, v_abbr = g["home_team"]["abbreviation"], g["visitor_team"]["abbreviation"]
            
            # Nota: En BDL V1 /games no trae FG_PCT directo. 
            # Como compromiso para el backtest, usaremos valores simulados o 0 
            # si no queremos hacer 1000 llamadas adicionales a /stats por ahora.
            # O mejor: El backtester debería usar /stats desde el inicio.
            
            # Home
            h_row = common.copy()
            h_row.update({
                "TEAM_ID": self.TEAM_MAP.get(h_abbr, g["home_team"]["id"]), 
                "TEAM_ABBREVIATION": h_abbr, 
                "MATCHUP": f"{h_abbr} vs. {v_abbr}", 
                "PTS": g["home_team_score"],
                "FG_PCT": 0.45, "FG3_PCT": 0.35, "FT_PCT": 0.75, # Placeholders para el MVP del backtest
                "REB": 45, "AST": 25, "TOV": 12, "PLUS_MINUS": g["home_team_score"] - g["visitor_team_score"],
                "WL": "W" if g["home_team_score"] > g["visitor_team_score"] else "L"
            })
            # Visitor
            v_row = common.copy()
            v_row.update({
                "TEAM_ID": self.TEAM_MAP.get(v_abbr, g["visitor_team"]["id"]), 
                "TEAM_ABBREVIATION": v_abbr, 
                "MATCHUP": f"{v_abbr} @ {h_abbr}", 
                "PTS": g["visitor_team_score"],
                "FG_PCT": 0.45, "FG3_PCT": 0.35, "FT_PCT": 0.75,
                "REB": 45, "AST": 25, "TOV": 12, "PLUS_MINUS": g["visitor_team_score"] - g["home_team_score"],
                "WL": "W" if g["visitor_team_score"] > g["home_team_score"] else "L"
            })
            mapped.extend([h_row, v_row])
        return pd.DataFrame(mapped)

    def _map_stats_to_nba_api_format(self, bdl_stats):
        mapped = []
        for s in bdl_stats:
            p, g, t = s["player"], s["game"], s["team"]
            mapped.append({
                "PLAYER_ID": p["id"], "PLAYER_NAME": f"{p['first_name']} {p['last_name']}",
                "TEAM_ID": self.TEAM_MAP.get(t["abbreviation"], t["id"]), "TEAM_ABBREVIATION": t["abbreviation"],
                "GAME_ID": str(g["id"]), "GAME_DATE": g["date"].split("T")[0],
                "MIN": s["min"], "PTS": s["pts"], "REB": s["reb"], "AST": s["ast"]
            })
        return pd.DataFrame(mapped)
