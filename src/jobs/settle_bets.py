"""
Settle Bets: liquida las apuestas de Paper Trading usando stats reales de BallDontLie.

Ejecuta a las 09:00 UTC (después de que todos los partidos NBA terminen).
Para cada apuesta PENDING, busca las stats reales del jugador en BDL y determina WIN/LOSS.
"""
from datetime import datetime, timedelta
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.bdl_client import BallDontLieClient
from src.utils.logger import logger


_MARKET_TO_STAT = {
    'REB_OVER':  ('REB', 'OVER'),
    'REB_UNDER': ('REB', 'UNDER'),
    'AST_OVER':  ('AST', 'OVER'),
    'AST_UNDER': ('AST', 'UNDER'),
    'PTS_OVER':  ('PTS', 'OVER'),
    'PTS_UNDER': ('PTS', 'UNDER'),
}


def _parse_market(market: str):
    """'REB_OVER' → ('REB', 'OVER'). Fallback: primer token = stat, OVER."""
    if market in _MARKET_TO_STAT:
        return _MARKET_TO_STAT[market]
    parts = market.rsplit('_', 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (market, 'OVER')


def _match_player(stats_df, player_name: str):
    """
    Busca el jugador en el DataFrame de stats de BDL.
    Intenta coincidencia exacta primero, luego parcial (primer + último nombre).
    """
    name_lower = player_name.lower().strip()
    exact = stats_df[stats_df['_name_lower'] == name_lower]
    if not exact.empty:
        return exact.iloc[0]

    parts = name_lower.split()
    if len(parts) >= 2:
        # Intenta que el primer nombre Y el último nombre estén presentes (orden no estricto)
        # O que el nombre buscado sea un subconjunto de lo que hay en BDL
        partial = stats_df[
            stats_df['_name_lower'].str.contains(parts[0], na=False) &
            (stats_df['_name_lower'].str.contains(parts[-1], na=False) | 
             stats_df['_name_lower'].str.contains(parts[1], na=False))
        ]
        if not partial.empty:
            return partial.iloc[0]

    return None


def main():
    logger.info("Settle Bets: liquidando apuestas de Paper Trading con stats reales de BDL...")
    bq  = NBABigQueryClient()
    bdl = BallDontLieClient()

    if not bq.client:
        logger.error("Sin cliente de BigQuery. Abortando liquidación.")
        return

    # 1. Obtener apuestas PENDING
    query_pending = f"""
        SELECT bet_id, player_name, market, line, stake_usd, odds_open,
               DATE(timestamp) AS bet_date
        FROM `{bq.project_id}.{bq.dataset_id_v2}.bet_history`
        WHERE result = 'PENDING'
        ORDER BY timestamp
    """
    try:
        pending = list(bq.client.query(query_pending).result())
    except Exception as e:
        logger.error(f"Error consultando apuestas pendientes: {e}")
        return

    if not pending:
        logger.info("No hay apuestas pendientes. Nada que liquidar.")
        return

    logger.info(f"Encontradas {len(pending)} apuestas pendientes.")

    # 2. Obtener stats de BDL para las fechas únicas de las apuestas
    # Si no hay stats para la fecha exacta, prueba +1 día (partidos de costa oeste)
    unique_dates = {str(bet.bet_date) for bet in pending}
    stats_by_date = {}  # {date_str: DataFrame}

    for date_str in unique_dates:
        df = bdl.get_player_stats(start_date=date_str)
        if not df.empty:
            df['_name_lower'] = df['PLAYER_NAME'].str.lower().str.strip()
            stats_by_date[date_str] = df
        else:
            # Intentar con el día siguiente (cobertura de partidos tardíos PT)
            next_day = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            df_next = bdl.get_player_stats(start_date=next_day)
            if not df_next.empty:
                df_next['_name_lower'] = df_next['PLAYER_NAME'].str.lower().str.strip()
                stats_by_date[date_str] = df_next
                logger.info(f"Stats de {date_str} encontradas en {next_day} (partido tardío).")
            else:
                stats_by_date[date_str] = None
                logger.warning(f"Sin stats de BDL para {date_str} ni {next_day}. Apuestas quedan PENDING.")

    # 3. Liquidar cada apuesta
    current_bankroll = bq.get_virtual_bankroll()
    settled = 0
    skipped = 0

    for bet in pending:
        date_str   = str(bet.bet_date)
        stats_df   = stats_by_date.get(date_str)
        stat_key, direction = _parse_market(bet.market)

        if stats_df is None or stats_df.empty:
            skipped += 1
            continue

        player_row = _match_player(stats_df, bet.player_name)

        if player_row is None:
            logger.warning(f"Jugador no encontrado en BDL: '{bet.player_name}' ({date_str}). Queda PENDING.")
            skipped += 1
            continue

        actual_stat = float(player_row.get(stat_key, 0) or 0)
        line        = float(bet.line)
        stake       = float(bet.stake_usd)
        odds        = float(bet.odds_open)

        # Si por algún error previo el stake fue negativo o cero, no actualizamos el bankroll
        if stake <= 0:
            logger.warning(f"  {bet.player_name} | Stake inválido (${stake}). Saltando ajuste de banca.")
            payout = 0
            is_win = actual_stat > line if direction == 'OVER' else actual_stat < line
            result = 'WIN' if is_win else 'LOSS'
        else:
            is_win      = actual_stat > line if direction == 'OVER' else actual_stat < line
            result      = 'WIN' if is_win else 'LOSS'
            payout      = stake * (odds - 1) if is_win else -stake
            current_bankroll += payout

        # Garantizar que el bankroll nunca sea negativo por errores de cálculo
        current_bankroll = max(0, current_bankroll)

        update_query = f"""
            UPDATE `{bq.project_id}.{bq.dataset_id_v2}.bet_history`
            SET result = '{result}',
                payout = {payout:.4f},
                odds_close = {odds:.4f}
            WHERE bet_id = '{bet.bet_id}'
        """
        try:
            bq.client.query(update_query).result()
            logger.info(
                f"  {bet.player_name} | {bet.market} {line:.1f} | "
                f"Real: {actual_stat:.0f} → {result} | Payout: ${payout:+.2f}"
            )
            settled += 1
        except Exception as e:
            logger.error(f"Error actualizando bet {bet.bet_id}: {e}")
            current_bankroll -= payout  # revertir para mantener consistencia

    # 4. Registrar nuevo saldo en BigQuery
    if settled > 0:
        insert_balance = f"""
            INSERT INTO `{bq.project_id}.{bq.dataset_id_v2}.virtual_bankroll`
            (current_balance, last_updated)
            VALUES ({current_bankroll:.4f}, CURRENT_TIMESTAMP())
        """
        try:
            bq.client.query(insert_balance).result()
            logger.info(
                f"Liquidación completa: {settled} apuestas resueltas, "
                f"{skipped} pendientes sin datos. "
                f"Saldo virtual: ${current_bankroll:.2f}"
            )
        except Exception as e:
            logger.error(f"Error actualizando virtual_bankroll: {e}")
    else:
        logger.warning(f"0 apuestas liquidadas ({skipped} sin datos de BDL).")


if __name__ == "__main__":
    main()
