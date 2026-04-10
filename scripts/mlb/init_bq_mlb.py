import os
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from dotenv import load_dotenv

load_dotenv()

# Forzar credenciales correctas si no están cargadas
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/oracle-nba-e8452340a8c8.json'

def init_mlb_bigquery():
    project_id = "oracle-nba"
    client = bigquery.Client(project=project_id)
    
    datasets = ["oracle_mlb_ds", "oracle_mlb_v2"]
    
    for ds_id in datasets:
        ds_ref = f"{project_id}.{ds_id}"
        try:
            client.get_dataset(ds_ref)
            print(f"✅ Dataset {ds_id} ya existe.")
        except NotFound:
            print(f"✨ Creando dataset {ds_id}...")
            dataset = bigquery.Dataset(ds_ref)
            dataset.location = "US"
            client.create_dataset(dataset)

    # 1. Tabla: mlb_pitcher_game_logs
    table_logs = f"{project_id}.oracle_mlb_ds.mlb_pitcher_game_logs"
    schema_logs = [
        bigquery.SchemaField("pitcher_id", "INT64"),
        bigquery.SchemaField("pitcher_name", "STRING"),
        bigquery.SchemaField("game_id", "INT64"),
        bigquery.SchemaField("game_date", "DATE"),
        bigquery.SchemaField("season", "INT64"),
        bigquery.SchemaField("team_id", "INT64"),
        bigquery.SchemaField("team_name", "STRING"),
        bigquery.SchemaField("opponent_team_id", "INT64"),
        bigquery.SchemaField("strikeouts", "INT64"),
        bigquery.SchemaField("ip", "FLOAT64"),
        bigquery.SchemaField("hits_allowed", "INT64"),
        bigquery.SchemaField("runs_allowed", "INT64"),
        bigquery.SchemaField("earned_runs", "INT64"),
        bigquery.SchemaField("walks", "INT64"),
        bigquery.SchemaField("pitch_count", "INT64"),
        bigquery.SchemaField("batters_faced", "INT64"),
        bigquery.SchemaField("games_started", "BOOLEAN"),
        bigquery.SchemaField("is_home", "BOOLEAN"),
        bigquery.SchemaField("ingested_at", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP")
    ]
    
    # 2. Tabla: mlb_paper_trades
    table_trades = f"{project_id}.oracle_mlb_v2.bet_history"
    schema_trades = [
        bigquery.SchemaField("bet_id", "STRING"),
        bigquery.SchemaField("player_id", "INT64"),
        bigquery.SchemaField("player_name", "STRING"),
        bigquery.SchemaField("game_id", "INT64"),
        bigquery.SchemaField("game_date", "DATE"),
        bigquery.SchemaField("market", "STRING"),
        bigquery.SchemaField("line", "FLOAT64"),
        bigquery.SchemaField("bet_direction", "STRING"),
        bigquery.SchemaField("odds_at_bet", "INT64"),
        bigquery.SchemaField("model_prediction", "FLOAT64"),
        bigquery.SchemaField("edge", "FLOAT64"),
        bigquery.SchemaField("stake_usd", "FLOAT64"),
        bigquery.SchemaField("result", "STRING"),
        bigquery.SchemaField("actual_value", "FLOAT64"),
        bigquery.SchemaField("payout", "FLOAT64"),
        bigquery.SchemaField("clv_at_close", "FLOAT64"),
        bigquery.SchemaField("timestamp", "TIMESTAMP", default_value_expression="CURRENT_TIMESTAMP")
    ]

    for table_id, schema in [(table_logs, schema_logs), (table_trades, schema_trades)]:
        try:
            client.get_table(table_id)
            print(f"✅ Tabla {table_id} ya existe.")
        except NotFound:
            print(f"✨ Creando tabla {table_id}...")
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)

if __name__ == "__main__":
    init_mlb_bigquery()
