import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# --------------------------------------------------------------------------- #
# settle_bets                                                                  #
# --------------------------------------------------------------------------- #

class TestSettleBets:
    """Tests para el job nocturno de liquidación de apuestas."""

    def _make_pending_bet(self, bet_id, player_name, market, line, stake, odds):
        bet = MagicMock()
        bet.bet_id = bet_id
        bet.player_name = player_name
        bet.market = market
        bet.line = line
        bet.stake_usd = stake
        bet.odds_open = odds
        bet.bet_date = '2024-01-01'
        return bet

    @patch('src.jobs.settle_bets.NBABigQueryClient')
    @patch('src.jobs.settle_bets.BallDontLieClient')
    def test_no_bq_client_exits_early(self, mock_bdl_cls, mock_bq_cls):
        """Si no hay cliente BigQuery, el job debe terminar sin ejecutar queries."""
        mock_bq = MagicMock()
        mock_bq.client = None
        mock_bq_cls.return_value = mock_bq

        from src.jobs.settle_bets import main
        main()

        mock_bq.get_virtual_bankroll.assert_not_called()

    @patch('src.jobs.settle_bets.NBABigQueryClient')
    @patch('src.jobs.settle_bets.BallDontLieClient')
    def test_no_pending_bets_skips_settlement(self, mock_bdl_cls, mock_bq_cls):
        """Si no hay apuestas pendientes, no ejecuta ninguna actualización."""
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq.project_id = 'oracle-nba'
        mock_bq.dataset_id_v2 = 'oracle_nba_v2'
        
        # No hay apuestas pendientes
        mock_bq.client.query.return_value.result.return_value = []
        mock_bq_cls.return_value = mock_bq

        from src.jobs.settle_bets import main
        main()

        assert mock_bq.client.query.call_count == 1

    @patch('src.jobs.settle_bets.NBABigQueryClient')
    @patch('src.jobs.settle_bets.BallDontLieClient')
    def test_full_settlement_loop(self, mock_bdl_cls, mock_bq_cls):
        """Prueba un ciclo completo de liquidación: una gana, una pierde, una falta datos."""
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq.project_id = 'oracle-nba'
        mock_bq.dataset_id_v2 = 'oracle_nba_v2'
        mock_bq.get_virtual_bankroll.return_value = 1000.0
        mock_bq_cls.return_value = mock_bq

        mock_bdl = MagicMock()
        # Stats para la fecha
        stats_df = pd.DataFrame([
            {'PLAYER_NAME': 'LeBron James', 'PTS': 30, 'REB': 10, 'AST': 8},
            {'PLAYER_NAME': 'Kevin Durant', 'PTS': 15, 'REB': 5, 'AST': 2}
        ])
        stats_df['_name_lower'] = stats_df['PLAYER_NAME'].str.lower()
        
        mock_bdl.get_player_stats.return_value = stats_df
        mock_bdl_cls.return_value = mock_bdl

        bet1 = self._make_pending_bet('b1', 'LeBron James', 'PTS_OVER', 25.5, 100.0, 1.90)
        bet2 = self._make_pending_bet('b2', 'Kevin Durant', 'PTS_OVER', 20.5, 100.0, 1.90)
        bet3 = self._make_pending_bet('b3', 'Stephen Curry', 'PTS_OVER', 20.5, 100.0, 1.90)
        
        mock_bq.client.query.return_value.result.side_effect = [
            [bet1, bet2, bet3], # query_pending
            MagicMock(), # update bet1
            MagicMock(), # update bet2
            MagicMock(), # insert balance
        ]

        from src.jobs.settle_bets import main
        main()

        assert mock_bq.client.query.call_count == 4
        last_query = mock_bq.client.query.call_args_list[-1][0][0]
        assert "990.0000" in last_query

    @patch('src.jobs.settle_bets.NBABigQueryClient')
    @patch('src.jobs.settle_bets.BallDontLieClient')
    def test_error_handling_in_loop(self, mock_bdl_cls, mock_bq_cls):
        """Prueba manejo de errores al consultar pendientes y al actualizar una apuesta."""
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq.project_id = 'oracle-nba'
        mock_bq.dataset_id_v2 = 'oracle_nba_v2'
        mock_bq_cls.return_value = mock_bq

        # Caso 1: Error en query_pending
        mock_bq.client.query.side_effect = Exception("BQ Error")
        from src.jobs.settle_bets import main
        main()
        
        # Caso 2: Error en update_query e insert_balance
        mock_bq.client.query.side_effect = None
        bet = self._make_pending_bet('b1', 'LeBron James', 'PTS_OVER', 25.5, 100.0, 1.90)
        
        stats_df = pd.DataFrame([{'PLAYER_NAME': 'LeBron James', 'PTS': 30, '_name_lower': 'lebron james'}])
        mock_bdl = MagicMock()
        mock_bdl.get_player_stats.return_value = stats_df
        mock_bdl_cls.return_value = mock_bdl

        # side_effect para query: [query_pending_result, update_error, insert_error]
        mock_bq.client.query.return_value.result.side_effect = [[bet], Exception("Update error"), Exception("Insert error")]
        main()

    @patch('src.jobs.settle_bets.NBABigQueryClient')
    @patch('src.jobs.settle_bets.BallDontLieClient')
    def test_next_day_stats_fallback(self, mock_bdl_cls, mock_bq_cls):
        """Prueba que si no hay stats hoy, busca mañana."""
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq.project_id = 'oracle-nba'
        mock_bq.dataset_id_v2 = 'oracle_nba_v2'
        mock_bq.get_virtual_bankroll.return_value = 1000.0
        mock_bq_cls.return_value = mock_bq

        mock_bdl = MagicMock()
        stats_df = pd.DataFrame([{'PLAYER_NAME': 'LeBron James', 'PTS': 30, '_name_lower': 'lebron james'}])
        mock_bdl.get_player_stats.side_effect = [pd.DataFrame(), stats_df]
        mock_bdl_cls.return_value = mock_bdl

        bet = self._make_pending_bet('b1', 'LeBron James', 'PTS_OVER', 25.5, 100.0, 1.90)
        mock_bq.client.query.return_value.result.side_effect = [[bet], MagicMock(), MagicMock()]

        from src.jobs.settle_bets import main
        main()
        
        assert mock_bdl.get_player_stats.call_count == 2

    def test_parse_market_fallback(self):
        from src.jobs.settle_bets import _parse_market
        assert _parse_market('PTS_OVER') == ('PTS', 'OVER')
        assert _parse_market('REB_UNDER') == ('REB', 'UNDER')
        assert _parse_market('UNKNOWN_VALUE') == ('UNKNOWN', 'VALUE')
        assert _parse_market('SINGLE') == ('SINGLE', 'OVER')

    def test_match_player(self):
        from src.jobs.settle_bets import _match_player
        df = pd.DataFrame([{'PLAYER_NAME': 'LeBron James', '_name_lower': 'lebron james', 'ID': 1}])
        
        assert _match_player(df, 'LeBron James')['ID'] == 1
        assert _match_player(df, 'lebron james')['ID'] == 1
        assert _match_player(df, 'LeBron James Jr') is not None
        assert _match_player(df, 'LeBron') is None # parts < 2

# --------------------------------------------------------------------------- #
# sunday_update                                                                 #
# --------------------------------------------------------------------------- #

class TestSundayUpdate:
    """Tests para el job semanal de actualización del portafolio Top 20."""

    @patch('src.jobs.sunday_update.NBABigQueryClient')
    def test_no_bq_client_exits_early(self, mock_bq_cls):
        """Sin cliente BQ, el job debe terminar sin ejecutar queries."""
        mock_bq = MagicMock()
        mock_bq.client = None
        mock_bq_cls.return_value = mock_bq

        from src.jobs.sunday_update import main
        main()
        mock_bq_cls.assert_called_once()

    @patch('src.jobs.sunday_update.NBABigQueryClient')
    @patch('src.jobs.sunday_update.PlayerStatsIngestion')
    def test_full_update_flow_with_errors(self, mock_ingestion_cls, mock_bq_cls):
        """Prueba el flujo completo y manejo de errores en inserción."""
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq.project_id = 'oracle-nba'
        mock_bq.dataset_id_v2 = 'oracle_nba_v2'
        mock_bq_cls.return_value = mock_bq

        # Mocking ingestion
        mock_ingestion = MagicMock()
        logs = pd.DataFrame([
            {'PLAYER_ID': 1, 'PLAYER_NAME': 'P1', 'MIN': 20, 'GAME_MARGIN': 15},
            {'PLAYER_ID': 1, 'PLAYER_NAME': 'P1', 'MIN': 10, 'GAME_MARGIN': 2},
        ])
        features = logs.copy()
        features['L10_STD_MIN'] = 5.0
        mock_ingestion.get_player_logs.return_value = logs
        mock_ingestion.calculate_rolling_features.return_value = features
        mock_ingestion.enrich_with_game_context.return_value = features
        mock_ingestion_cls.return_value = mock_ingestion

        from src.jobs.sunday_update import main
        # Caso 1: Éxito
        with patch('src.jobs.sunday_update.MIN_GAMES', 1), patch('src.jobs.sunday_update.MIN_LOW', 5):
            mock_bq.client.insert_rows_json.return_value = [] # No errors
            main()
            
            # Caso 2: Errores en insert_rows_json
            mock_bq.client.insert_rows_json.return_value = [{'error': 'failed'}]
            main()
            
            # Caso 3: Excepción en query DELETE
            mock_bq.client.query.side_effect = Exception("Delete fail")
            main()

        # Caso 4: Sin logs
        mock_ingestion.get_player_logs.return_value = pd.DataFrame()
        main()

    def test_compute_minute_swing(self):
        from src.jobs.sunday_update import _compute_minute_swing
        # Test con datos que generen NaN (sin close games por ejemplo)
        df = pd.DataFrame([{'GAME_MARGIN': 15, 'MIN': 20}])
        assert _compute_minute_swing(df) == 20.0
        
        df_empty = pd.DataFrame(columns=['GAME_MARGIN', 'MIN'])
        assert _compute_minute_swing(df_empty) == 0.0

    @patch('src.jobs.sunday_update.NBABigQueryClient')
    @patch('src.jobs.sunday_update.PlayerStatsIngestion')
    def test_no_candidates_skips_insert(self, mock_ingestion_cls, mock_bq_cls):
        mock_ingestion = MagicMock()
        df = pd.DataFrame([{'PLAYER_ID': 1, 'PLAYER_NAME': 'Too Good', 'MIN': 35, 'L10_STD_MIN': 1.0, 'GAME_MARGIN': 0}])
        mock_ingestion.get_player_logs.return_value = df
        mock_ingestion.calculate_rolling_features.return_value = df
        mock_ingestion.enrich_with_game_context.return_value = df
        mock_ingestion_cls.return_value = mock_ingestion
        
        mock_bq = MagicMock()
        mock_bq.client = MagicMock()
        mock_bq_cls.return_value = mock_bq

        from src.jobs.sunday_update import main
        main()

        mock_bq.client.insert_rows_json.assert_not_called()
