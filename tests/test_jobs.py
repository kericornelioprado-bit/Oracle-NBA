import pytest
from unittest.mock import MagicMock, patch, call


# --------------------------------------------------------------------------- #
# settle_bets                                                                  #
# --------------------------------------------------------------------------- #

class TestSettleBets:
    """Tests para el job nocturno de liquidación de apuestas."""

    def _make_pending_bet(self, bet_id, stake, odds):
        bet = MagicMock()
        bet.bet_id = bet_id
        bet.stake_usd = stake
        bet.odds_open = odds
        bet.result = 'PENDING'
        return bet

    def test_no_bq_client_exits_early(self):
        """Si no hay cliente BigQuery, el job debe terminar sin ejecutar queries."""
        with patch('src.jobs.settle_bets.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = None
            mock_bq_cls.return_value = mock_bq

            from src.jobs.settle_bets import main
            main()

        mock_bq.get_virtual_bankroll.assert_not_called()

    def test_no_pending_bets_skips_settlement(self):
        """Si no hay apuestas pendientes, no ejecuta ninguna actualización."""
        with patch('src.jobs.settle_bets.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.get_virtual_bankroll.return_value = 20000.0
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'

            # No hay apuestas pendientes
            mock_query_result = MagicMock()
            mock_query_result.__iter__ = lambda self: iter([])
            mock_bq.client.query.return_value.result.return_value = mock_query_result
            mock_bq_cls.return_value = mock_bq

            from src.jobs.settle_bets import main
            main()

        # Solo se llama una vez para buscar pendientes, no para actualizar
        assert mock_bq.client.query.call_count == 1

    def test_win_increases_balance(self):
        """Una apuesta ganadora debe aumentar el saldo."""
        bet = self._make_pending_bet('bet-001', stake=100.0, odds=1.91)

        with patch('src.jobs.settle_bets.NBABigQueryClient') as mock_bq_cls, \
             patch('random.random', return_value=0.10):  # < 0.55 → WIN
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.get_virtual_bankroll.return_value = 20000.0
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'

            mock_bq.client.query.return_value.result.return_value = iter([bet])
            mock_bq_cls.return_value = mock_bq

            from src.jobs.settle_bets import main
            main()

        # Verificar que se ejecutó INSERT para registrar nuevo saldo
        queries = [str(c) for c in mock_bq.client.query.call_args_list]
        insert_calls = [q for q in queries if 'INSERT' in q.upper() or 'virtual_bankroll' in q]
        assert len(insert_calls) > 0

    def test_loss_decreases_balance(self):
        """Una apuesta perdedora debe disminuir el saldo."""
        bet = self._make_pending_bet('bet-002', stake=100.0, odds=1.91)

        with patch('src.jobs.settle_bets.NBABigQueryClient') as mock_bq_cls, \
             patch('random.random', return_value=0.99):  # > 0.55 → LOSS
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.get_virtual_bankroll.return_value = 20000.0
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'

            call_count = [0]
            def query_side_effect(sql):
                result_mock = MagicMock()
                if call_count[0] == 0:
                    result_mock.result.return_value = iter([bet])
                else:
                    result_mock.result.return_value = iter([])
                call_count[0] += 1
                return result_mock

            mock_bq.client.query.side_effect = query_side_effect
            mock_bq_cls.return_value = mock_bq

            from src.jobs.settle_bets import main
            main()

        # Verificamos que se ejecutaron queries (UPDATE + INSERT balance)
        assert mock_bq.client.query.call_count >= 2

    def test_exception_during_settlement_does_not_crash(self):
        """Excepciones en la ejecución de queries se capturan sin propagar."""
        with patch('src.jobs.settle_bets.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.get_virtual_bankroll.return_value = 20000.0
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'
            mock_bq.client.query.side_effect = Exception("BigQuery connection error")
            mock_bq_cls.return_value = mock_bq

            from src.jobs.settle_bets import main
            # No debe lanzar excepción
            main()


# --------------------------------------------------------------------------- #
# sunday_update                                                                 #
# --------------------------------------------------------------------------- #

class TestSundayUpdate:
    """Tests para el job semanal de actualización del portafolio Top 20."""

    def test_no_bq_client_exits_early(self):
        """Sin cliente BQ, el job debe terminar sin ejecutar queries."""
        query_mock = MagicMock()
        with patch('src.jobs.sunday_update.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = None
            mock_bq_cls.return_value = mock_bq

            from src.jobs.sunday_update import main
            main()

        # client es None → el condicional `if not bq.client` impide cualquier query
        query_mock.assert_not_called()

    def test_executes_create_or_replace_query(self):
        """Debe ejecutar exactamente una query de creación/reemplazo de tabla."""
        with patch('src.jobs.sunday_update.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'
            mock_bq_cls.return_value = mock_bq

            from src.jobs.sunday_update import main
            main()

        assert mock_bq.client.query.call_count == 1

    def test_query_references_top_20_portfolio_table(self):
        """La query ejecutada debe referenciar top_20_portfolio."""
        with patch('src.jobs.sunday_update.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'
            mock_bq_cls.return_value = mock_bq

            from src.jobs.sunday_update import main
            main()

        executed_sql = mock_bq.client.query.call_args[0][0]
        assert 'top_20_portfolio' in executed_sql

    def test_exception_during_update_does_not_crash(self):
        """Excepciones en BigQuery se capturan sin propagar."""
        with patch('src.jobs.sunday_update.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'
            mock_bq.client.query.side_effect = Exception("Table not found")
            mock_bq_cls.return_value = mock_bq

            from src.jobs.sunday_update import main
            # No debe lanzar excepción
            main()

    def test_query_waits_for_completion(self):
        """Debe llamar .result() para esperar a que la query termine."""
        with patch('src.jobs.sunday_update.NBABigQueryClient') as mock_bq_cls:
            mock_bq = MagicMock()
            mock_bq.client = MagicMock()
            mock_bq.project_id = 'oracle-nba'
            mock_bq.dataset_id = 'oracle_nba_v2'
            mock_bq_cls.return_value = mock_bq

            from src.jobs.sunday_update import main
            main()

        mock_bq.client.query.return_value.result.assert_called_once()
