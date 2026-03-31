import pytest
from src.models.minutes_projector import MinutesProjector


@pytest.fixture
def projector():
    return MinutesProjector()


# --------------------------------------------------------------------------- #
# project_minutes — casos base                                                 #
# --------------------------------------------------------------------------- #

def test_project_minutes_base_no_adjustments(projector):
    """Sin blowout ni lesión, devuelve exactamente L10_MIN."""
    stats = {'L10_MIN': 30.0}
    result = projector.project_minutes(stats, game_script_margin=5.0)
    assert result == pytest.approx(30.0)


def test_project_minutes_zero_base_returns_zero(projector):
    """Si L10_MIN es 0, devuelve 0.0 sin importar el contexto."""
    stats = {'L10_MIN': 0.0}
    result = projector.project_minutes(stats, game_script_margin=20.0, is_starter_out=True, starter_avg_min=35.0)
    assert result == 0.0


def test_project_minutes_missing_l10_min_returns_zero(projector):
    """Si el diccionario no tiene L10_MIN, devuelve 0.0."""
    result = projector.project_minutes({}, game_script_margin=0.0)
    assert result == 0.0


# --------------------------------------------------------------------------- #
# Blowout — umbral 15 puntos                                                   #
# --------------------------------------------------------------------------- #

def test_project_minutes_bench_blowout_boost(projector):
    """Jugador de banca (L10_MIN < 28) con margen >= 15 recibe ×1.25."""
    stats = {'L10_MIN': 20.0}
    result = projector.project_minutes(stats, game_script_margin=15.0)
    assert result == pytest.approx(20.0 * 1.25)


def test_project_minutes_bench_blowout_negative_margin(projector):
    """El ajuste de blowout aplica con margen negativo (visitante gana fácil)."""
    stats = {'L10_MIN': 20.0}
    result = projector.project_minutes(stats, game_script_margin=-15.0)
    assert result == pytest.approx(20.0 * 1.25)


def test_project_minutes_starter_blowout_penalty(projector):
    """Titular (L10_MIN >= 28) con margen >= 15 recibe ×0.85."""
    stats = {'L10_MIN': 32.0}
    result = projector.project_minutes(stats, game_script_margin=20.0)
    assert result == pytest.approx(32.0 * 0.85)


def test_project_minutes_no_blowout_below_threshold(projector):
    """Margen exactamente en 14.9 NO activa el ajuste de blowout."""
    stats = {'L10_MIN': 20.0}
    result = projector.project_minutes(stats, game_script_margin=14.9)
    assert result == pytest.approx(20.0)


def test_project_minutes_exact_blowout_threshold(projector):
    """Margen exactamente en 15.0 SÍ activa el ajuste."""
    stats = {'L10_MIN': 20.0}
    result = projector.project_minutes(stats, game_script_margin=15.0)
    assert result == pytest.approx(20.0 * 1.25)


# --------------------------------------------------------------------------- #
# Injury Heir                                                                  #
# --------------------------------------------------------------------------- #

def test_project_minutes_injury_heir_bench_player(projector):
    """Suplente hereda el 60% de los minutos del titular lesionado."""
    stats = {'L10_MIN': 18.0}
    result = projector.project_minutes(
        stats, game_script_margin=0.0,
        is_starter_out=True, starter_avg_min=34.0
    )
    expected = 18.0 + 34.0 * 0.60
    assert result == pytest.approx(expected)


def test_project_minutes_injury_heir_starter_not_affected(projector):
    """Un titular NO hereda minutos aunque otro titular esté lesionado."""
    stats = {'L10_MIN': 30.0}
    result = projector.project_minutes(
        stats, game_script_margin=0.0,
        is_starter_out=True, starter_avg_min=34.0
    )
    # No es banca (L10_MIN >= 28), así que no hereda
    assert result == pytest.approx(30.0)


def test_project_minutes_injury_heir_no_starter_min(projector):
    """Si starter_avg_min es 0, no se redistribuyen minutos."""
    stats = {'L10_MIN': 18.0}
    result = projector.project_minutes(
        stats, game_script_margin=0.0,
        is_starter_out=True, starter_avg_min=0.0
    )
    assert result == pytest.approx(18.0)


# --------------------------------------------------------------------------- #
# Límite máximo de 48 minutos                                                  #
# --------------------------------------------------------------------------- #

def test_project_minutes_capped_at_48(projector):
    """La proyección nunca supera 48 minutos."""
    stats = {'L10_MIN': 40.0}
    # Banca con boost (40 < 28 es falso, pero probamos con suplente heredero + blowout)
    stats_bench = {'L10_MIN': 22.0}
    result = projector.project_minutes(
        stats_bench, game_script_margin=20.0,
        is_starter_out=True, starter_avg_min=40.0
    )
    # 22×1.25 + 40×0.60 = 27.5 + 24 = 51.5 → debe ser 48.0
    assert result == pytest.approx(48.0)


# --------------------------------------------------------------------------- #
# should_skip_game                                                              #
# --------------------------------------------------------------------------- #

def test_should_skip_questionable(projector):
    assert projector.should_skip_game('Questionable') is True


def test_should_skip_gtd(projector):
    assert projector.should_skip_game('GTD') is True


def test_should_skip_doubtful(projector):
    assert projector.should_skip_game('Doubtful') is True


def test_should_not_skip_out(projector):
    """'Out' no está en la lista de incertidumbre; el jugador simplemente no juega."""
    assert projector.should_skip_game('Out') is False


def test_should_not_skip_active(projector):
    assert projector.should_skip_game('Active') is False


def test_should_not_skip_empty_string(projector):
    assert projector.should_skip_game('') is False
