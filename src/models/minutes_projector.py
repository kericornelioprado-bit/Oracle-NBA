from src.utils.logger import logger

class MinutesProjector:
    """Motor heurístico para proyectar los minutos que jugará un jugador basándose en el Game Script."""
    
    def __init__(self):
        # Parámetros heurísticos según PRD V2
        self.BLOWOUT_MARGIN_THRESHOLD = 15.0
        self.BENCH_BLOWOUT_BOOST = 1.25
        self.STARTER_BLOWOUT_PENALTY = 0.85
        self.INJURY_HEIR_FRACTION = 0.60
        self.STARTER_MIN_THRESHOLD = 28.0 # Minutos promedio para considerar a alguien titular

    def project_minutes(self, player_stats, game_script_margin, is_starter_out=False, starter_avg_min=0.0):
        """
        Proyecta los minutos de un jugador.
        
        Args:
            player_stats (dict): Diccionario con 'L10_MIN' y otros promedios del jugador.
            game_script_margin (float): Margen esperado del partido (positivo = blowout local).
            is_starter_out (bool): True si el titular de su posición está lesionado.
            starter_avg_min (float): Minutos promedio del titular lesionado a redistribuir.
            
        Returns:
            float: Minutos proyectados (o -1 si hay incertidumbre "SKIP").
        """
        base_min = player_stats.get('L10_MIN', 0.0)
        
        if base_min == 0:
            return 0.0
            
        projected_min = base_min
        is_bench = base_min < self.STARTER_MIN_THRESHOLD
        
        # 1. Ajuste por Game Script (Blowout)
        if abs(game_script_margin) >= self.BLOWOUT_MARGIN_THRESHOLD:
            if is_bench:
                projected_min *= self.BENCH_BLOWOUT_BOOST
                logger.debug(f"Blowout detectado: boost de banca aplicado (x{self.BENCH_BLOWOUT_BOOST})")
            else:
                projected_min *= self.STARTER_BLOWOUT_PENALTY
                logger.debug(f"Blowout detectado: penalización titular aplicada (x{self.STARTER_BLOWOUT_PENALTY})")
                
        # 2. Ajuste por Injury Heir (Lesiones)
        if is_starter_out and is_bench and starter_avg_min > 0:
            added_min = starter_avg_min * self.INJURY_HEIR_FRACTION
            projected_min += added_min
            logger.debug(f"Titular OUT detectado: {added_min:.1f} minutos redistribuidos al suplente.")
            
        # Limitar minutos máximos a 48 (un partido NBA sin prórroga)
        return min(projected_min, 48.0)
        
    def should_skip_game(self, injury_report_status):
        """
        Aplica el 'Uncertainty Skip' (Regla de Oro).
        Si un jugador clave es Questionable/GTD, se omite el partido completo.
        """
        uncertain_statuses = ['Questionable', 'GTD', 'Doubtful']
        if injury_report_status in uncertain_statuses:
            logger.warning(f"Incertidumbre detectada ({injury_report_status}). Ejecutando SKIP AUTOMÁTICO.")
            return True
        return False
