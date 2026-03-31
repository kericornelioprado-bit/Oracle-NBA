"""
Profitability tests for PlayerPropsModel — tres capas:

  Layer 1: Mathematical soundness  — EV / Kelly math (PASS expected)
  Layer 2: Calibrated simulation   — profitable when el modelo es preciso (PASS expected)
  Layer 3: Real backtest 2025-26   — valida los resultados históricos reales (FAIL si no es rentable)

Los tests de Layer 3 documentan el estado actual del modelo con precisión.
Si el modelo no gana dinero, estos tests fallan y describen exactamente por qué.
"""
import os
import numpy as np
import pytest

from src.models.props_model import PlayerPropsModel

BREAKEVEN_RATE_190 = 1.0 / 1.90   # ≈ 52.63 %
MIN_ROI = 0.0
REAL_BACKTEST_CSV = "data/results/backtest_props_2026_results.csv"


@pytest.fixture
def model():
    return PlayerPropsModel()


# ---------------------------------------------------------------------------
# Layer 1 — Mathematical soundness
# ---------------------------------------------------------------------------

class TestMathematicalSoundness:
    """Los primitivos matemáticos del modelo deben ser correctos."""

    def test_ev_positive_when_prob_above_breakeven(self, model):
        """prob=0.60 con odds 1.90 → EV = (0.60×1.90)−1 = 0.14 > 0."""
        ev = model.calculate_ev(0.60, 1.90)
        assert ev == pytest.approx(0.60 * 1.90 - 1.0)
        assert ev > 0.0

    def test_ev_negative_when_prob_below_breakeven(self, model):
        """prob=0.45 con odds 1.90 → EV negativo."""
        ev = model.calculate_ev(0.45, 1.90)
        assert ev < 0.0

    def test_ev_zero_at_exact_breakeven(self, model):
        """prob = 1/odds → EV ≈ 0 (punto de equilibrio exacto)."""
        prob = BREAKEVEN_RATE_190
        ev = model.calculate_ev(prob, 1.90)
        assert abs(ev) < 1e-9

    def test_kelly_fraction_non_negative_for_any_prob(self, model):
        """Kelly nunca debe ser negativa (sin apuesta = 0)."""
        odds = 1.90
        b = odds - 1
        for prob in [0.0, 0.30, BREAKEVEN_RATE_190, 0.60, 0.90, 1.0]:
            kelly_raw = (prob * b - (1 - prob)) / b if b > 0 else 0
            kelly = max(0.0, kelly_raw * 0.25)
            assert kelly >= 0.0, f"Kelly negativo para prob={prob}"

    def test_kelly_increases_monotonically_with_edge(self, model):
        """Mayor ventaja → mayor apuesta Kelly (fracción constante)."""
        odds = 1.90
        b = odds - 1
        probs = [0.56, 0.62, 0.70, 0.80]
        kellys = [max(0.0, ((p * b - (1 - p)) / b) * 0.25) for p in probs]
        assert kellys == sorted(kellys), f"Kelly no monótono: {kellys}"

    def test_prob_over_is_calibrated_near_line(self, model):
        """Cuando expected ≈ line, P(Over) ≈ 0.50 (distribución simétrica)."""
        prob = model.calculate_prob_over(expected_stat=7.0, line=7.0, stat_type='REB')
        assert 0.45 < prob < 0.55

    def test_predict_stat_scales_linearly_with_minutes(self, model):
        """E[stat] es lineal en minutos proyectados (ritmo constante)."""
        stats = {'L10_MIN': 30.0, 'L10_REB': 9.0}  # ritmo 0.30 reb/min
        e25 = model.predict_stat('REB', 25.0, stats)
        e35 = model.predict_stat('REB', 35.0, stats)
        assert e35 / e25 == pytest.approx(35.0 / 25.0)


# ---------------------------------------------------------------------------
# Layer 2 — Simulación calibrada (modelo preciso = rentable)
# ---------------------------------------------------------------------------

class TestCalibratedSimulation:
    """
    Simula una temporada donde la probabilidad predicha == probabilidad real.
    En este escenario ideal el modelo DEBE ser rentable.
    """

    def _simulate(
        self,
        model,
        bets,          # lista de (model_prob, true_prob)
        bankroll=1000.0,
        kelly_fraction=0.25,
        odds=1.90,
        min_ev=0.05,
        seed=42,
    ):
        """
        Ejecuta simulación de apuestas.
        Devuelve (bankroll_final, roi, n_bets_placed).
        """
        rng = np.random.default_rng(seed=seed)
        b = odds - 1
        total_staked = 0.0
        n_placed = 0

        for model_prob, true_prob in bets:
            ev = model.calculate_ev(model_prob, odds)
            if ev <= min_ev:
                continue
            kelly_raw = (model_prob * b - (1 - model_prob)) / b
            stake = bankroll * max(0.0, kelly_raw * kelly_fraction)
            if stake <= 0:
                continue
            won = rng.random() < true_prob
            bankroll += stake * b if won else -stake
            total_staked += stake
            n_placed += 1

        roi = (bankroll - 1000.0) / total_staked if total_staked > 0 else 0.0
        return bankroll, roi, n_placed

    def test_profitable_with_clear_edge(self, model):
        """
        500 apuestas con prob real=0.70 (EV ≈ 33 %).
        Un modelo calibrado debe terminar con ROI positivo.
        """
        bets = [(0.70, 0.70)] * 500
        final_bk, roi, n = self._simulate(model, bets)
        assert n > 0, "Ninguna apuesta superó el umbral de EV"
        assert roi > 0.0, f"ROI esperado positivo, obtenido {roi:.2%}"
        assert final_bk > 1000.0, f"Bankroll debería crecer; terminó en ${final_bk:.2f}"

    def test_profitable_mixed_edge(self, model):
        """Mezcla de ventajas moderada (0.60) y alta (0.75) — ambas rentables."""
        bets = [(0.60, 0.60)] * 250 + [(0.75, 0.75)] * 250
        _, roi, n = self._simulate(model, bets)
        assert n > 0
        assert roi > 0.0, f"Mezcla de ventajas debería ser rentable; ROI={roi:.2%}"

    def test_high_ev_outperforms_marginal_ev(self, model):
        """ROI con ventaja alta (0.75) debe superar al de ventaja marginal (0.57)."""
        bets_marginal = [(0.57, 0.57)] * 500
        bets_high = [(0.75, 0.75)] * 500
        _, roi_marginal, _ = self._simulate(model, bets_marginal)
        _, roi_high, _ = self._simulate(model, bets_high)
        assert roi_high > roi_marginal, (
            f"ROI alta ventaja ({roi_high:.2%}) ≤ ROI marginal ({roi_marginal:.2%})"
        )

    def test_quarter_kelly_survives_losing_streak(self, model):
        """
        Quarter-Kelly debe sobrevivir una racha de 30 pérdidas consecutivas
        sin llevar la banca a cero.
        """
        bankroll = 1000.0
        max_stake_fraction = 0.25  # worst-case Kelly completo (no quarter)
        for _ in range(30):
            stake = bankroll * max_stake_fraction
            bankroll -= stake
        assert bankroll > 0.0, "Quarter-Kelly no debería causar ruina en 30 pérdidas"

    def test_no_bets_placed_when_all_ev_negative(self, model):
        """Si todas las apuestas tienen EV negativo, el modelo no debe apostar nada."""
        bets = [(0.40, 0.40)] * 200  # EV = 0.40×1.90−1 = −0.24
        _, _, n = self._simulate(model, bets)
        assert n == 0, f"El modelo no debe apostar con EV negativo; apostó {n} veces"


# ---------------------------------------------------------------------------
# Layer 3 — Backtest real 2025-26 (integración)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRealBacktest2026:
    """
    Valida los resultados históricos del backtest guardado en CSV.

    ESTADO ACTUAL (2026-03-30):
      - Win rate : 35.61 %  (necesario > 52.63 %)
      - ROI      : -37.87 %
      - Bankroll : $0.00   (ruina completa)

    Causa raíz documentada:
      El backtest simula un "edge" aplicando un boost artificial del 15 % en minutos,
      pero no verifica si ese boost ocurrió realmente. La casa mantiene la línea en
      el L10 histórico, por lo que el modelo no tiene ventaja informacional real.
    """

    @pytest.fixture(autouse=True)
    def load_csv(self):
        if not os.path.exists(REAL_BACKTEST_CSV):
            pytest.skip(f"CSV de backtest no encontrado: {REAL_BACKTEST_CSV}")
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas no disponible — instalar para tests de integración")

        df = pd.read_csv(REAL_BACKTEST_CSV)
        assert len(df) > 0, "El CSV está vacío"

        self.df = df
        self.n_bets = len(df)
        self.wins = int((df['profit'] > 0).sum())
        self.win_rate = self.wins / self.n_bets
        self.total_staked = float(df['stake'].sum())
        self.total_profit = float(df['profit'].sum())
        self.roi = self.total_profit / self.total_staked if self.total_staked > 0 else -1.0
        self.final_bankroll = float(df['bankroll'].iloc[-1])

    # --- Tests que deben pasar independientemente de la rentabilidad ---

    def test_minimum_sample_size(self):
        """El backtest debe tener al menos 100 apuestas para ser estadísticamente válido."""
        assert self.n_bets >= 100, f"Solo {self.n_bets} apuestas — muestra insuficiente"

    def test_all_bets_respected_ev_threshold(self):
        """
        Cada apuesta registrada debió superar el umbral EV ≥ 5 %.
        Un fallo aquí indica un bug en el filtro del backtester.
        """
        min_ev = float(self.df['ev'].min())
        assert min_ev >= 0.05, (
            f"Se encontraron apuestas con EV < 5 %: EV mínimo = {min_ev:.4f}. "
            f"El filtro de EV del backtester está roto."
        )

    def test_stakes_are_positive(self):
        """No debe haber apuestas con stake ≤ 0."""
        bad = (self.df['stake'] <= 0).sum()
        assert bad == 0, f"{bad} apuestas con stake inválido (≤ 0)"

    # --- Tests de rentabilidad (documentan si el modelo gana dinero) ---

    def test_win_rate_exceeds_breakeven(self):
        """
        Win rate debe superar 52.63 % (break-even a odds 1.90).

        FALLA ACTUALMENTE: win_rate = 35.61 %.
        El boost del 15 % en minutos no corresponde a una ventaja real
        sobre la línea que ofrece la casa.
        """
        assert self.win_rate > BREAKEVEN_RATE_190, (
            f"Win rate {self.win_rate:.2%} < break-even {BREAKEVEN_RATE_190:.2%}. "
            f"El modelo no tiene ventaja real en datos históricos. "
            f"Total apuestas: {self.n_bets}, victorias: {self.wins}."
        )

    def test_roi_positive(self):
        """
        ROI debe ser > 0 %.

        FALLA ACTUALMENTE: ROI = -37.87 %.
        """
        assert self.roi > MIN_ROI, (
            f"ROI {self.roi:.2%} — el modelo pierde dinero en el backtest 2025-26. "
            f"Profit total: ${self.total_profit:+.2f} sobre ${self.total_staked:.2f} apostados."
        )

    def test_bankroll_survives(self):
        """
        La banca no debe llegar a cero (ruina).

        FALLA ACTUALMENTE: bankroll final = $0.00.
        """
        assert self.final_bankroll > 0.0, (
            f"La banca llegó a ${self.final_bankroll:.2f}. "
            f"El sizing de Kelly no puede proteger contra un modelo sin edge real."
        )

    def test_ev_correlates_with_win_rate(self):
        """
        Las apuestas con EV alto deben ganar más frecuentemente que las de EV bajo.
        Si esto falla, el modelo no está calibrado — predice probabilidades incorrectas.
        """
        high_ev = self.df[self.df['ev'] > 0.20]
        low_ev = self.df[(self.df['ev'] >= 0.05) & (self.df['ev'] <= 0.10)]

        if len(high_ev) < 30 or len(low_ev) < 30:
            pytest.skip(
                f"Muestras insuficientes: high_ev={len(high_ev)}, low_ev={len(low_ev)}"
            )

        wr_high = (high_ev['profit'] > 0).mean()
        wr_low = (low_ev['profit'] > 0).mean()

        assert wr_high > wr_low, (
            f"EV alto win rate ({wr_high:.2%}) ≤ EV bajo ({wr_low:.2%}). "
            f"Las probabilidades predichas no están correlacionadas con resultados reales — "
            f"el modelo no está calibrado."
        )
