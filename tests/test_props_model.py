import pytest
from src.models.props_model import PlayerPropsModel


@pytest.fixture
def model():
    return PlayerPropsModel()


# --------------------------------------------------------------------------- #
# predict_stat                                                                 #
# --------------------------------------------------------------------------- #

def test_predict_stat_basic_reb(model):
    """Calcula E[REB] correctamente: (L10_REB/L10_MIN) × projected_min."""
    stats = {'L10_MIN': 30.0, 'L10_REB': 6.0}
    result = model.predict_stat('REB', projected_minutes=30.0, player_stats=stats)
    assert result == pytest.approx(6.0)  # ritmo 0.2/min × 30 min


def test_predict_stat_scaled_minutes(model):
    """Si los minutos proyectados aumentan, la predicción escala proporcionalmente."""
    stats = {'L10_MIN': 30.0, 'L10_AST': 6.0}
    result_30 = model.predict_stat('AST', projected_minutes=30.0, player_stats=stats)
    result_36 = model.predict_stat('AST', projected_minutes=36.0, player_stats=stats)
    assert result_36 == pytest.approx(result_30 * (36.0 / 30.0))


def test_predict_stat_zero_base_min_returns_zero(model):
    """Si L10_MIN es 0, devuelve 0.0 para evitar división por cero."""
    stats = {'L10_MIN': 0.0, 'L10_REB': 5.0}
    result = model.predict_stat('REB', projected_minutes=25.0, player_stats=stats)
    assert result == 0.0


def test_predict_stat_zero_projected_min_returns_zero(model):
    """Si los minutos proyectados son 0, devuelve 0.0."""
    stats = {'L10_MIN': 30.0, 'L10_PTS': 15.0}
    result = model.predict_stat('PTS', projected_minutes=0.0, player_stats=stats)
    assert result == 0.0


def test_predict_stat_missing_stat_key(model):
    """Si falta L10_STAT en el dict, asume 0 y devuelve 0.0."""
    stats = {'L10_MIN': 30.0}  # Sin L10_REB
    result = model.predict_stat('REB', projected_minutes=30.0, player_stats=stats)
    assert result == 0.0


def test_predict_stat_pts(model):
    """Verifica PTS con ritmo alto."""
    stats = {'L10_MIN': 34.0, 'L10_PTS': 25.5}
    result = model.predict_stat('PTS', projected_minutes=34.0, player_stats=stats)
    assert result == pytest.approx(25.5)


# --------------------------------------------------------------------------- #
# calculate_prob_over                                                           #
# --------------------------------------------------------------------------- #

def test_calculate_prob_over_expected_equals_line(model):
    """Cuando expected_stat == line, prob ≈ 0.5 (distribución simétrica)."""
    prob = model.calculate_prob_over(expected_stat=6.0, line=6.0, stat_type='REB')
    assert 0.45 < prob < 0.55


def test_calculate_prob_over_expected_well_above_line(model):
    """Cuando la expectativa es muy superior a la línea, prob > 0.8."""
    prob = model.calculate_prob_over(expected_stat=12.0, line=5.5, stat_type='REB')
    assert prob > 0.80


def test_calculate_prob_over_expected_well_below_line(model):
    """Cuando la expectativa es muy inferior a la línea, prob < 0.2."""
    prob = model.calculate_prob_over(expected_stat=2.0, line=8.5, stat_type='REB')
    assert prob < 0.20


def test_calculate_prob_over_zero_expected_stat(model):
    """Si expected_stat <= 0, devuelve 0.0."""
    prob = model.calculate_prob_over(expected_stat=0.0, line=4.5, stat_type='AST')
    assert prob == 0.0


def test_calculate_prob_over_negative_expected(model):
    """Expectativa negativa también debe devolver 0.0."""
    prob = model.calculate_prob_over(expected_stat=-1.0, line=4.5, stat_type='REB')
    assert prob == 0.0


def test_calculate_prob_over_range_valid(model):
    """La probabilidad siempre debe estar en [0, 1]."""
    for line in [2.5, 5.5, 10.5, 20.0]:
        prob = model.calculate_prob_over(expected_stat=7.0, line=line, stat_type='PTS')
        assert 0.0 <= prob <= 1.0


def test_calculate_prob_over_uses_stat_std_dev(model):
    """REB tiene std=2.5, PTS tiene std=5.5 — mismo offset da distintas probabilidades."""
    # Mismo offset relativo (expected - line = 3) pero diferentes std
    prob_reb = model.calculate_prob_over(expected_stat=10.0, line=7.0, stat_type='REB')
    prob_pts = model.calculate_prob_over(expected_stat=10.0, line=7.0, stat_type='PTS')
    # REB (std pequeña) → más certeza → mayor prob
    assert prob_reb > prob_pts


def test_calculate_prob_over_player_std_overrides_default(model):
    """player_std pasado explícitamente reemplaza DEFAULT_STD_DEV."""
    # Con DEFAULT_STD_DEV['REB'] = 2.5
    prob_default = model.calculate_prob_over(expected_stat=10.0, line=7.0, stat_type='REB')
    # Con player_std más pequeña (jugador consistente) → mayor certeza → mayor prob
    prob_tight = model.calculate_prob_over(expected_stat=10.0, line=7.0, stat_type='REB', player_std=1.0)
    # Con player_std más grande (jugador errático) → menor certeza → menor prob
    prob_loose = model.calculate_prob_over(expected_stat=10.0, line=7.0, stat_type='REB', player_std=5.0)

    assert prob_tight > prob_default > prob_loose


def test_calculate_prob_over_player_std_none_uses_default(model):
    """player_std=None debe comportarse igual que no pasar el argumento."""
    prob_no_arg = model.calculate_prob_over(expected_stat=8.0, line=6.0, stat_type='AST')
    prob_none = model.calculate_prob_over(expected_stat=8.0, line=6.0, stat_type='AST', player_std=None)
    assert prob_no_arg == pytest.approx(prob_none)


def test_calculate_prob_over_player_std_zero_uses_default(model):
    """player_std=0 debe caer al DEFAULT_STD_DEV (evitar división por cero)."""
    prob_default = model.calculate_prob_over(expected_stat=8.0, line=6.0, stat_type='AST')
    prob_zero_std = model.calculate_prob_over(expected_stat=8.0, line=6.0, stat_type='AST', player_std=0.0)
    assert prob_default == pytest.approx(prob_zero_std)


# --------------------------------------------------------------------------- #
# calculate_ev                                                                  #
# --------------------------------------------------------------------------- #

def test_calculate_ev_positive(model):
    """Apuesta con EV positivo: prob=0.60, odds=1.91 → EV > 0."""
    ev = model.calculate_ev(prob_model=0.60, odds_decimal=1.91)
    assert ev > 0.0
    assert ev == pytest.approx(0.60 * 1.91 - 1.0)


def test_calculate_ev_negative(model):
    """Apuesta con EV negativo: prob=0.45, odds=1.91."""
    ev = model.calculate_ev(prob_model=0.45, odds_decimal=1.91)
    assert ev < 0.0


def test_calculate_ev_odds_le_one_returns_minus_one(model):
    """Odds <= 1.0 no tiene sentido; devuelve -1.0."""
    assert model.calculate_ev(0.90, odds_decimal=1.0) == -1.0
    assert model.calculate_ev(0.90, odds_decimal=0.5) == -1.0


def test_calculate_ev_zero_prob_returns_minus_one(model):
    """Prob <= 0 no tiene sentido; devuelve -1.0."""
    assert model.calculate_ev(prob_model=0.0, odds_decimal=2.0) == -1.0


def test_calculate_ev_breakeven(model):
    """Con prob = 1/odds, EV ≈ 0 (punto de equilibrio)."""
    odds = 1.91
    breakeven_prob = 1.0 / odds
    ev = model.calculate_ev(prob_model=breakeven_prob, odds_decimal=odds)
    assert abs(ev) < 0.001


def test_calculate_ev_formula(model):
    """Verifica la fórmula completa: EV = (prob × odds) - 1."""
    prob = 0.55
    odds = 2.10
    expected_ev = (prob * odds) - 1.0
    assert model.calculate_ev(prob, odds) == pytest.approx(expected_ev)
