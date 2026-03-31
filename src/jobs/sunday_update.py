"""
Sunday Update: recalcula el portafolio Top 20 basado en datos reales de BDL.

Selecciona bench players (15-27 min promedio) con alta varianza de minutos
y mayor 'minute_swing' (diferencia de minutos en blowouts vs. partidos cerrados).
Estos son los jugadores donde el edge del game script es más grande.
"""
from datetime import datetime
import pandas as pd
from src.utils.bigquery_client import NBABigQueryClient
from src.data.player_ingestion import PlayerStatsIngestion
from src.utils.logger import logger

# Criterios de selección
MIN_LOW         = 15.0   # minutos mínimos para rotación estable
MIN_HIGH        = 27.0   # por debajo del umbral de titular
STD_MIN         = 3.0    # alta variabilidad de minutos
MIN_GAMES       = 15     # muestra mínima estadística
BLOWOUT_THR     = 12.0   # margen para clasificar como blowout
CLOSE_THR       = 6.0    # margen para clasificar como partido cerrado
PORTFOLIO_SIZE  = 20


def _compute_minute_swing(group, game_margin_col='GAME_MARGIN', min_col='MIN'):
    """Diferencia entre minutos en blowouts y minutos en partidos cerrados."""
    blowout_min = group.loc[group[game_margin_col].abs() >= BLOWOUT_THR, min_col].mean()
    close_min   = group.loc[group[game_margin_col].abs() <= CLOSE_THR,   min_col].mean()
    blowout_min = blowout_min if pd.notna(blowout_min) else 0.0
    close_min   = close_min   if pd.notna(close_min)   else 0.0
    return blowout_min - close_min


def main():
    logger.info("Sunday Update: recalculando portafolio Top 20...")
    bq = NBABigQueryClient()

    if not bq.client:
        logger.error("Sin cliente de BigQuery. Abortando Sunday Update.")
        return

    # 1. Player logs + features (temporada actual)
    ingestion    = PlayerStatsIngestion(season=2025)
    player_logs  = ingestion.get_player_logs()

    if player_logs.empty:
        logger.error("Sin logs de jugadores de BDL. Abortando.")
        return

    player_data = ingestion.calculate_rolling_features(player_logs)

    # 2. Enriquecer con márgenes reales de partido (necesario para minute_swing)
    player_data = ingestion.enrich_with_game_context(player_data)

    # 3. Calcular minute_swing por jugador
    # Usamos groupby + apply sobre las columnas GAME_MARGIN y MIN reales
    minute_swings = (
        player_data
        .groupby('PLAYER_ID')
        .apply(_compute_minute_swing)
        .reset_index()
    )
    minute_swings.columns = ['PLAYER_ID', 'minute_swing']

    # 4. Resumen por jugador
    player_summary = (
        player_data
        .groupby(['PLAYER_ID', 'PLAYER_NAME'])
        .agg(
            avg_min      = ('MIN', 'mean'),
            std_min      = ('L10_STD_MIN', 'last'),
            games_played = ('MIN', 'count'),
        )
        .reset_index()
        .merge(minute_swings, on='PLAYER_ID', how='left')
    )
    player_summary['minute_swing'] = player_summary['minute_swing'].fillna(0.0)

    # 5. Filtrar candidatos
    candidates = (
        player_summary[
            player_summary['avg_min'].between(MIN_LOW, MIN_HIGH) &
            (player_summary['std_min'] >= STD_MIN) &
            (player_summary['games_played'] >= MIN_GAMES)
        ]
        .sort_values('minute_swing', ascending=False)
        .head(PORTFOLIO_SIZE)
    )

    if candidates.empty:
        logger.warning("Sin candidatos que cumplan los criterios. Portafolio no actualizado.")
        return

    logger.info(f"Top {len(candidates)} jugadores seleccionados:")
    for _, r in candidates.iterrows():
        tier = 1 if r['minute_swing'] >= 8 else 2
        logger.info(
            f"  [T{tier}] {r['PLAYER_NAME']} — "
            f"avg={r['avg_min']:.1f}min, std={r['std_min']:.1f}, "
            f"swing={r['minute_swing']:.1f}, n={int(r['games_played'])}"
        )

    # 6. Actualizar BigQuery (DELETE + INSERT para idempotencia)
    table_ref = f"`{bq.project_id}.{bq.dataset_id_v2}.top_20_portfolio`"

    rows = [
        {
            "player_id":    int(r['PLAYER_ID']),
            "tier":         1 if r['minute_swing'] >= 8 else 2,
            "minute_swing": round(float(r['minute_swing']), 2),
            "updated_at":   datetime.now().isoformat(),
        }
        for _, r in candidates.iterrows()
    ]

    try:
        bq.client.query(f"DELETE FROM {table_ref} WHERE TRUE").result()
        errors = bq.client.insert_rows_json(
            f"{bq.project_id}.{bq.dataset_id_v2}.top_20_portfolio", rows
        )
        if errors:
            logger.error(f"Errores al insertar portafolio: {errors}")
        else:
            logger.info(f"Portafolio Top {len(rows)} actualizado en BigQuery.")
    except Exception as e:
        logger.error(f"Error actualizando portafolio en BigQuery: {e}")


if __name__ == "__main__":
    main()
