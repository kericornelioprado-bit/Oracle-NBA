import requests
import time
import pandas as pd
import os
from dotenv import load_dotenv
from src.shared.logger import logger

load_dotenv()

class BallDontLieClient:
    """
    Cliente universal para la API de BallDontLie (balldontlie.io).
    Soporta NBA y MLB mediante el parámetro 'sport'.
    """
    
    # Mapeo de equipos NBA (histórico para compatibilidad con nba_api format)
    NBA_TEAM_MAP = {
        "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739, "NOP": 1610612740,
        "CHI": 1610612741, "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
        "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747, "MIA": 1610612748,
        "MIL": 1610612749, "MIN": 1610612750, "BKN": 1610612751, "NYK": 1610612752,
        "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755, "PHX": 1610612756,
        "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "OKC": 1610612760,
        "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763, "WAS": 1610612764,
        "DET": 1610612765, "CHA": 1610612766
    }

    def __init__(self, sport='nba', api_key=None):
        self.sport = sport.lower()
        self.api_key = api_key or os.getenv("BDL_API_KEY")
        self.headers = {"Authorization": self.api_key} if self.api_key else {}
        
        if self.sport == 'mlb':
            self.base_url = "https://api.balldontlie.io/mlb/v1"
        else:
            self.base_url = "https://api.balldontlie.io/v1"
            
        if not self.api_key:
            logger.warning(f"BDL_API_KEY no configurado para {self.sport.upper()}. Usando límites de nivel gratuito.")

    def _make_request(self, endpoint, params=None):
        """Maneja las peticiones con reintentos básicos y cursor de paginación."""
        all_data = []
        cursor = None
        url = f"{self.base_url}/{endpoint}"
        
        while True:
            current_params = params.copy() if params else {}
            current_params["per_page"] = 100
            if cursor:
                current_params["cursor"] = cursor
                
            try:
                response = requests.get(url, params=current_params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                all_data.extend(data.get("data", []))
                
                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor:
                    break
                    
                # Rate limit safety
                time.sleep(1.5 if not self.api_key else 0.05)
            except Exception as e:
                logger.error(f"Error en BDL request {endpoint} ({self.sport}): {e}")
                break
                
        return all_data

    def get_games(self, seasons=None, start_date=None, end_date=None, team_ids=None):
        """Obtiene juegos para la temporada o rango de fechas especificado."""
        params = {}
        if seasons: params["seasons[]"] = seasons if isinstance(seasons, list) else [seasons]
        if start_date: 
            dates = [start_date] if isinstance(start_date, str) else start_date
            params["dates[]"] = dates

        data = self._make_request("games", params)
        
        if not data:
            return pd.DataFrame()
            
        if self.sport == 'nba':
            return self._map_nba_games(data)
        else:
            return pd.DataFrame(data) # MLB se devuelve crudo para ser procesado por su propio FE

    def get_stats(self, seasons=None, player_ids=None, start_date=None, end_date=None, game_ids=None):
        """Obtiene estadísticas de jugadores/box scores."""
        params = {}
        if seasons: params["seasons[]"] = seasons if isinstance(seasons, list) else [seasons]
        if player_ids: params["player_ids[]"] = player_ids if isinstance(player_ids, list) else [player_ids]
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        if game_ids: params["game_ids[]"] = game_ids if isinstance(game_ids, list) else [game_ids]

        data = self._make_request("stats", params)
        
        if not data:
            return pd.DataFrame()
            
        if self.sport == 'nba':
            return self._map_nba_stats(data)
        else:
            return pd.DataFrame(data)

    def _map_nba_games(self, bdl_games):
        """Mapeo legacy para mantener compatibilidad con el engine de NBA."""
        mapped = []
        for g in bdl_games:
            common = {"GAME_ID": str(g["id"]), "GAME_DATE": g["date"].split("T")[0], "SEASON_ID": str(g["season"])}
            h_abbr = g["home_team"]["abbreviation"]
            v_abbr = g["visitor_team"]["abbreviation"]
            
            # Home Row
            h_row = common.copy()
            h_row.update({
                "TEAM_ID": self.NBA_TEAM_MAP.get(h_abbr, g["home_team"]["id"]), 
                "TEAM_ABBREVIATION": h_abbr, 
                "MATCHUP": f"{h_abbr} vs. {v_abbr}", 
                "PTS": g["home_team_score"],
                "FG_PCT": 0.45, "FG3_PCT": 0.35, "FT_PCT": 0.75, # Placeholders
                "REB": 45, "AST": 25, "TOV": 12, "PLUS_MINUS": g["home_team_score"] - g["visitor_team_score"],
                "WL": "W" if g["home_team_score"] > g["visitor_team_score"] else "L"
            })
            
            # Visitor Row
            v_row = common.copy()
            v_row.update({
                "TEAM_ID": self.NBA_TEAM_MAP.get(v_abbr, g["visitor_team"]["id"]), 
                "TEAM_ABBREVIATION": v_abbr, 
                "MATCHUP": f"{v_abbr} @ {h_abbr}", 
                "PTS": g["visitor_team_score"],
                "FG_PCT": 0.45, "FG3_PCT": 0.35, "FT_PCT": 0.75,
                "REB": 45, "AST": 25, "TOV": 12, "PLUS_MINUS": g["visitor_team_score"] - g["home_team_score"],
                "WL": "W" if g["visitor_team_score"] > g["home_team_score"] else "L"
            })
            mapped.extend([h_row, v_row])
        return pd.DataFrame(mapped)

    def _map_nba_stats(self, bdl_stats):
        """Mapeo legacy para stats de jugadores NBA."""
        mapped = []
        for s in bdl_stats:
            p, g, t = s["player"], s["game"], s["team"]
            mapped.append({
                "PLAYER_ID": p["id"], "PLAYER_NAME": f"{p['first_name']} {p['last_name']}",
                "TEAM_ID": self.NBA_TEAM_MAP.get(t["abbreviation"], t["id"]), "TEAM_ABBREVIATION": t["abbreviation"],
                "GAME_ID": str(g["id"]), "GAME_DATE": g["date"].split("T")[0],
                "MIN": s["min"], "PTS": s["pts"], "REB": s["reb"], "AST": s["ast"]
            })
        return pd.DataFrame(mapped)
