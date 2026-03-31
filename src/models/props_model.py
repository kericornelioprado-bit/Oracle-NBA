import numpy as np
from src.utils.logger import logger

class PlayerPropsModel:
    """Modelo de predicción de estadísticas (Props) basado en minutos proyectados."""
    
    def __init__(self):
        # Parámetros para calcular la probabilidad de Over (distribución normal asumida)
        # En una versión madura, esto se reemplaza con la varianza real del jugador
        self.DEFAULT_STD_DEV = {'REB': 2.5, 'AST': 2.0, 'PTS': 5.5}

    def predict_stat(self, stat_type, projected_minutes, player_stats):
        """
        Predice una estadística esperada (Ej. E[REB]) usando el ritmo histórico y los minutos proyectados.
        
        Args:
            stat_type (str): 'REB', 'AST', o 'PTS'.
            projected_minutes (float): Minutos proyectados por el MinutesProjector.
            player_stats (dict): Diccionario con 'L10_MIN' y la estadística 'L10_REB', etc.
            
        Returns:
            float: Estadística esperada.
        """
        base_min = player_stats.get('L10_MIN', 0.0)
        base_stat = player_stats.get(f'L10_{stat_type}', 0.0)
        
        if base_min <= 0 or projected_minutes <= 0:
            return 0.0
            
        # Ritmo de producción por minuto (Per-Minute Rate)
        per_minute_rate = base_stat / base_min
        
        # Predicción = Ritmo * Minutos Proyectados
        expected_stat = per_minute_rate * projected_minutes
        
        logger.debug(f"Predicción {stat_type}: Ritmo {per_minute_rate:.3f}/min * {projected_minutes:.1f} min = {expected_stat:.2f}")
        return expected_stat

    def calculate_prob_over(self, expected_stat, line, stat_type, player_std=None):
        """
        Calcula la probabilidad P(Over) asumiendo distribución normal.

        Args:
            expected_stat (float): Estadística esperada predicha.
            line (float): Línea de la casa.
            stat_type (str): 'REB', 'AST' o 'PTS'.
            player_std (float | None): Desviación estándar histórica del jugador (L10_STD_*).
                Si se proporciona y es > 0, reemplaza el DEFAULT_STD_DEV genérico,
                calibrando la distribución a la variabilidad real del jugador.
        """
        from scipy.stats import norm

        if expected_stat <= 0:
            return 0.0

        if player_std is not None and player_std > 0:
            std_dev = player_std
        else:
            std_dev = self.DEFAULT_STD_DEV.get(stat_type, 2.0)

        prob_over = 1.0 - norm.cdf(line, loc=expected_stat, scale=std_dev)
        return prob_over

    def calculate_ev(self, prob_model, odds_decimal):
        """
        Calcula el Valor Esperado (EV) de una apuesta.
        EV = (Prob * Odds) - 1
        """
        if odds_decimal <= 1.0 or prob_model <= 0:
            return -1.0
        
        ev = (prob_model * odds_decimal) - 1.0
        return ev
