# Estructura Monorepo — Fase 1
## Oracle_NBA → Sports Betting Suite

**Principio:** NBA en producción no se toca. MLB se construye al lado.

---

## Estructura objetivo (Fase 1)

```
Oracle_NBA/                          # Nombre del repo no cambia aún
├── .claude/
├── .github/
├── config/
│   ├── nba/                         # Mover configs NBA aquí
│   │   └── ...
│   └── mlb/                         # NUEVO: configs MLB
│       ├── features.yaml            # Definición de features para pitcher K model
│       ├── model_params.yaml        # Hiperparámetros del stacking ensemble
│       └── props_markets.yaml       # Mercados de props a monitorear
├── data/                            # Sin cambios
├── docs/
│   ├── ARCHITECTURE.md              # Ya existe (mover aquí o dejar en raíz)
│   ├── PRD.md                       # Ya existe
│   └── mlb/                         # NUEVO
│       └── DIAMANTE_V1_PLAN.md      # El plan que armamos hoy
├── infra/
│   ├── nba/                         # Cloud Run job config para NBA (ya existente, reorganizar)
│   └── mlb/                         # NUEVO: Cloud Run job config para MLB
│       ├── cloud_run_job.yaml
│       └── scheduler.yaml
├── models/                          # Modelos serializados (.pkl, .joblib)
│   ├── nba/
│   └── mlb/                         # NUEVO
├── notebooks/
│   ├── nba/
│   └── mlb/                         # NUEVO
│       └── 01_eda_pitchers.ipynb    # Exploración inicial de data MLB
├── scripts/
│   ├── nba/
│   └── mlb/                         # NUEVO
│       ├── backfill_historical.py   # One-time: cargar game logs 2022-2025
│       └── test_bdl_mlb.py          # Exploración de endpoints MLB
├── src/
│   │
│   ├── __init__.py
│   │
│   ├── data/                        # ⚠️ SIN CAMBIOS — NBA sigue usando esto
│   │   ├── __init__.py
│   │   ├── eda_report.py
│   │   ├── feature_engineering.py
│   │   ├── ingestion.py
│   │   └── player_ingestion.py
│   │
│   ├── jobs/                        # ⚠️ SIN CAMBIOS — NBA sigue usando esto
│   │   ├── settle_bets.py
│   │   └── sunday_update.py
│   │
│   ├── models/                      # ⚠️ SIN CAMBIOS — NBA sigue usando esto
│   │   ├── __init__.py
│   │   ├── evaluator.py
│   │   ├── inference.py
│   │   ├── minutes_projector.py
│   │   ├── props_model.py
│   │   ├── stacking_trainer.py
│   │   ├── trainer.py
│   │   └── tuner.py
│   │
│   ├── utils/                       # ⚠️ SIN CAMBIOS — NBA sigue importando de aquí
│   │   ├── __init__.py
│   │   ├── bdl_client.py
│   │   ├── bigquery_client.py
│   │   ├── email_service.py
│   │   ├── logger.py
│   │   ├── odds_api.py
│   │   └── report_generator.py
│   │
│   ├── shared/                      # 🆕 NUEVO — Capa compartida para multi-deporte
│   │   ├── __init__.py
│   │   ├── bigquery_client.py       # Copia de utils/ (o import re-export)
│   │   ├── email_service.py         # Copia de utils/
│   │   ├── logger.py                # Copia de utils/
│   │   ├── odds_api.py              # Copia de utils/ (The-Odds-API)
│   │   ├── report_generator.py      # Copia de utils/
│   │   ├── bdl_client.py            # EXTENDIDO: parametrizado por deporte
│   │   ├── paper_trading.py         # Extraído de jobs/settle_bets.py (lógica genérica)
│   │   ├── ev_calculator.py         # Cálculo de Expected Value (genérico)
│   │   └── kelly.py                 # Kelly Criterion sizing (genérico)
│   │
│   └── mlb/                         # 🆕 NUEVO — Módulo Diamante
│       ├── __init__.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── ingestion.py         # Ingesta de BallDontLie MLB endpoints
│       │   ├── feature_engineering.py # Features de pitcher K model
│       │   └── lineup_tracker.py    # Monitoreo de lineups confirmados
│       ├── models/
│       │   ├── __init__.py
│       │   ├── strikeout_model.py   # Modelo de predicción de K's
│       │   ├── run_line_model.py    # Game Script engine adaptado a MLB
│       │   └── inference.py         # Pipeline de predicción diaria
│       └── jobs/
│           ├── __init__.py
│           ├── daily_ingestion.py   # Cloud Run Job: ingesta diaria
│           ├── predict_and_trade.py # Cloud Run Job: predicción + paper trade
│           └── settle_bets.py       # Llama a shared.paper_trading
│
├── tests/
│   ├── nba/                         # Tests existentes (reorganizar)
│   ├── mlb/                         # NUEVO
│   │   ├── test_ingestion.py
│   │   ├── test_features.py
│   │   └── test_strikeout_model.py
│   └── shared/                      # NUEVO
│       ├── test_bdl_client.py
│       └── test_paper_trading.py
│
├── system-heartbeat/                # Sin cambios
├── .env                             # Agregar vars MLB (BDL_MLB_API_KEY, etc.)
├── .env.example                     # Actualizar con vars MLB
├── .gitignore
├── CLAUDE.md                        # Actualizar con contexto MLB
├── ctl.sh                           # Agregar comandos MLB (ctl.sh mlb:ingest, mlb:predict)
├── Dockerfile                       # Agregar --build-arg SPORT=nba|mlb
├── main.py                          # Agregar --sport flag (python main.py --sport mlb)
├── README.md                        # Actualizar
└── requirements.txt                 # Agregar deps MLB si hay nuevas
```

---

## ¿Qué va en shared/ exactamente?

### Copias directas de utils/ (misma lógica, nueva ubicación):
| Archivo | Razón |
|---|---|
| `bigquery_client.py` | Operaciones BQ son idénticas para cualquier deporte |
| `email_service.py` | Alertas por email son genéricas |
| `logger.py` | Logging es universal |
| `odds_api.py` | The-Odds-API ya soporta MLB, mismo client |
| `report_generator.py` | Generación de reportes es genérica |

### Extendido / parametrizado:
| Archivo | Cambio |
|---|---|
| `bdl_client.py` | Agregar `sport` param: `BDLClient(sport='mlb')` que cambia el base path de `/nba/v1/` a `/mlb/v1/` |

### Extraído de código existente:
| Archivo | Fuente | Qué se extrae |
|---|---|---|
| `paper_trading.py` | `jobs/settle_bets.py` | Lógica genérica de settlement, tracking, métricas. El job de NBA sigue llamando su versión; MLB llama a shared. |
| `ev_calculator.py` | Probablemente ya existe inline en algún archivo | Cálculo de EV: `model_prob - implied_prob` |
| `kelly.py` | Probablemente ya existe inline | Kelly Criterion: `edge / (odds - 1)` |

---

## Estrategia de imports en Fase 1

```python
# MLB importa de shared (código nuevo)
from src.shared.bigquery_client import BigQueryClient
from src.shared.bdl_client import BDLClient
from src.shared.odds_api import OddsAPI
from src.shared.paper_trading import PaperTrader

# NBA sigue importando de utils (código existente, NO SE TOCA)
from src.utils.bigquery_client import BigQueryClient
from src.utils.bdl_client import BDLClient
```

---

## Fase 2 (cuando MLB paper trading esté estable)

1. Crear `src/nba/` con subcarpetas `data/`, `models/`, `jobs/`
2. Mover `src/data/*` → `src/nba/data/`
3. Mover `src/models/*` → `src/nba/models/`
4. Mover `src/jobs/*` → `src/nba/jobs/`
5. Actualizar imports de NBA: `from src.utils.X` → `from src.shared.X`
6. Eliminar `src/utils/` (ya redundante)
7. Resultado: `src/` tiene solo 3 carpetas: `shared/`, `nba/`, `mlb/`

---

## Entry points

### main.py (actualizado)
```python
# Idea: un solo entry point con flag de deporte
# python main.py --sport nba --job predict
# python main.py --sport mlb --job daily_ingestion
# python main.py --sport mlb --job predict_and_trade

import argparse

if args.sport == 'nba':
    # importar y ejecutar job de NBA (lógica existente)
elif args.sport == 'mlb':
    from src.mlb.jobs import daily_ingestion, predict_and_trade, settle_bets
    # ejecutar job correspondiente
```

### Dockerfile (actualizado)
```dockerfile
# Build arg para deporte — permite Cloud Run Jobs separados
ARG SPORT=nba
ENV SPORT=${SPORT}
# ... el resto igual, CMD cambia según SPORT
```

### Cloud Scheduler
```
NBA Job: cron → Cloud Run Job (SPORT=nba) — ya existente
MLB Job: cron → Cloud Run Job (SPORT=mlb) — NUEVO, schedule diferente
```

---

## Checklist de implementación (Semana 2, primeras 2-3 horas)

- [ ] Crear carpeta `src/shared/`
- [ ] Copiar archivos compartibles de `src/utils/` a `src/shared/`
- [ ] Extender `bdl_client.py` en shared/ para soportar `sport='mlb'`
- [ ] Crear carpeta `src/mlb/` con subcarpetas `data/`, `models/`, `jobs/`
- [ ] Crear `config/mlb/` con configs iniciales
- [ ] Crear `scripts/mlb/test_bdl_mlb.py` para explorar endpoints
- [ ] Actualizar `.env` con variables MLB
- [ ] Verificar que NBA sigue funcionando exactamente igual (smoke test)
- [ ] Commit: "feat: monorepo structure for multi-sport support"