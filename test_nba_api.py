from nba_api.stats.endpoints import playergamelogs
import pandas as pd

logs = playergamelogs.PlayerGameLogs(season_nullable='2024-25')
df = logs.get_data_frames()[0]
print(df[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'MIN', 'REB', 'AST']].head())
