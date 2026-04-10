# Oracle Sports Betting Suite (formerly Oráculo NBA)

Sistema predictivo de **Value Betting** para deportes (actualmente **NBA** y en fase de expansión a **MLB**). Combina Modelos de Ensemble para predicción de resultados con un motor de Player Props impulsado por cuotas reales de mercado. 100% automatizado en Google Cloud.

## Arquitectura Monorepo (Fase 1 completada)

El sistema ha evolucionado a una estructura de Monorepo para soportar múltiples deportes compartiendo infraestructura core:
- `src/shared/`: Clientes API agnósticos (BigQuery, BallDontLie, Email, OddsAPI).
- `src/nba/`: (Migración en proceso) Lógica legacy de Oráculo NBA (Moneyline, Player Props, Game Script).
- `src/mlb/`: (En desarrollo - Diamante MLB) Modelo enfocado en Pitcher Strikeouts.

## Características Core (NBA V2)

- **Moneyline (Game Picks):** Stacking Ensemble (LR + XGBoost, 63.91% accuracy, 24.29% ROI en backtest).
- **Player Props:** Evalúa EV real contra cuotas de mercado (Pinnacle/The Odds API) para el "Top 20" de jugadores.
- **Automatización completa:** Cloud Scheduler -> Cloud Run -> BigQuery -> Gmail.
- **Kelly Fraccional:** Sizing de apuestas proporcional al edge calculado.

## Uso y CLI Unificado

El entry point `main.py` soporta ejecución híbrida (Server Flask o CLI Job) mediante flags:

```bash
# Servidor local
./ctl.sh start

# CLI para Jobs específicos
python main.py --sport nba --job predict
python main.py --sport nba --job settle
python main.py --sport mlb --job ingest  # (Próximamente)
python main.py --sport mlb --job predict # (Próximamente)
```

## Próximos Pasos (Diamante MLB V1)
- **Fase 2:** Ingesta de 4 años de game logs (Pitchers).
- **Fase 3:** Feature engineering y Stacking Classifier para Strikeouts (K's).
- **Fase 4:** Paper Trading (5 semanas).
