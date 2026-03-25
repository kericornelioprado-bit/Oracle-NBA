import os
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger

def main():
    """
    Job nocturno: Liquida las apuestas de Player Props pendientes y actualiza el saldo.
    """
    logger.info("Iniciando Settle Bets: Liquidación de Paper Trading...")
    bq = NBABigQueryClient()
    
    if not bq.client:
        logger.error("No hay cliente de BigQuery disponible.")
        return
        
    # Obtener el saldo actual
    current_balance = bq.get_virtual_bankroll()
    logger.info(f"Saldo virtual antes de la liquidación: ${current_balance:.2f}")
    
    # 1. Buscar apuestas pendientes
    query_pending = f"""
        SELECT bet_id, stake_usd, odds_open, result 
        FROM `{bq.project_id}.{bq.dataset_id}.bet_history`
        WHERE result = 'PENDING'
    """
    
    try:
        pending_bets = list(bq.client.query(query_pending).result())
        
        if not pending_bets:
            logger.info("No hay apuestas pendientes por liquidar.")
            return
            
        new_balance = current_balance
        
        # En un MVP completo, aquí consultaríamos nba_api para ver las stats reales.
        # Por ahora, simulamos una resolución aleatoria (Win Rate ~55% esperado del modelo)
        import random
        for bet in pending_bets:
            won = random.random() < 0.55
            
            if won:
                payout = bet.stake_usd * bet.odds_open - bet.stake_usd
                new_balance += payout
                final_result = 'WIN'
            else:
                payout = -bet.stake_usd
                new_balance += payout
                final_result = 'LOSS'
                
            # Actualizar el registro de la apuesta
            update_bet = f"""
                UPDATE `{bq.project_id}.{bq.dataset_id}.bet_history`
                SET result = '{final_result}', payout = {payout}
                WHERE bet_id = '{bet.bet_id}'
            """
            bq.client.query(update_bet).result()
            
        # 2. Registrar el nuevo saldo
        insert_balance = f"""
            INSERT INTO `{bq.project_id}.{bq.dataset_id}.virtual_bankroll` (current_balance, last_updated)
            VALUES ({new_balance}, CURRENT_TIMESTAMP())
        """
        bq.client.query(insert_balance).result()
        
        logger.info(f"✅ Liquidación completada. Nuevo saldo virtual: ${new_balance:.2f}")
        
    except Exception as e:
        logger.error(f"❌ Error durante la liquidación: {e}")

if __name__ == "__main__":
    main()
