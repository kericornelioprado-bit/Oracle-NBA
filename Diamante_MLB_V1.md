# Diamante MLB V1 — Plan Detallado
## Modelo de Predicción: Pitcher Strikeouts

**Módulo:** Diamante (MLB)  
**Versión:** V1 — Pitcher-Centric Strikeout Model  
**Duración:** 6 semanas de build + 5 semanas de paper trading  
**Dedicación:** ~10 hrs/semana (compartidas con NBA en las primeras semanas)  
**Presupuesto API:** $39.99/mes (BallDontLie GOAT tier para MLB) + The-Odds-API (ya pagándose)

---

## 1. Alcance de V1

**Prop objetivo:** Strikeouts de pitcher abridor (over/under K's por juego).

**Tesis del modelo:** El K rate de un pitcher abridor es la estadística más estable y predecible en baseball. Combinando el perfil del pitcher con las tendencias de ponche del equipo oponente y el contexto del juego, podemos identificar líneas de props con valor esperado positivo.

**Fuera de alcance para V1:**
- Props de bateador (hits, total bases) → V2
- Datos Statcast (exit velocity, barrel rate) → V2
- Múltiples casas de momios → se usa BallDontLie (player props) + The-Odds-API (odds de mercado, ya pagándose)

---

## 2. Arquitectura de Datos

### 2.1 Fuente: BallDontLie MLB (GOAT Tier — $39.99/mes)

| Endpoint | Uso | Frecuencia de Ingesta |
|---|---|---|
| `/mlb/v1/games` | Schedule, scores, status | Diaria (juegos del día + resultados) |
| `/mlb/v1/stats` | Box score por jugador por juego | Post-juego (batch nocturno) |
| `/mlb/v1/season_stats` | Promedios de temporada (K rate, ERA, WHIP) | Diaria (se actualiza con cada juego) |
| `/mlb/v1/player_splits` | Home/away, vs LHB/RHB | Semanal (cambia lento) |
| `/mlb/v1/player_vs_player` | Historial pitcher vs bateadores del lineup | Pre-juego (cuando se confirma lineup) |
| `/mlb/v1/lineups` | Lineup confirmado del día | Pre-juego (~2-4 hrs antes) |
| `/mlb/v1/betting_odds` | Moneyline, run line, totals | Pre-juego (para EV calculation) |
| `/mlb/v1/player_props` | Líneas de K's del pitcher (over/under) | Pre-juego (para comparar vs modelo) |
| `/mlb/v1/player_injuries` | IL status, day-to-day | Diaria |
| `/mlb/v1/players/active` | Roster activo | Semanal |

### 2.1b Fuente: The-Odds-API (ya pagándose)

| Uso | Detalle |
|---|---|
| Odds de mercado multi-sportsbook | Moneylines, spreads, totals de múltiples casas |
| Closing line reference | Para calcular CLV post-juego |
| Validación cruzada | Comparar odds de BallDontLie vs The-Odds-API para detectar discrepancias |

**Nota:** The-Odds-API es la fuente primaria de odds de mercado. BallDontLie `/betting_odds` y `/player_props` se usan como complemento. Si hay conflicto, The-Odds-API tiene prioridad por su cobertura multi-book.

### 2.2 BigQuery Schema

**Tabla: `mlb_pitcher_game_logs`** (una fila por pitcher por juego)

```
pitcher_id          INT64       -- BallDontLie player ID
game_id             INT64       -- BallDontLie game ID
game_date           DATE
season              INT64
opponent_team_id    INT64
home_away           STRING      -- 'home' | 'away'

-- Pitching stats del juego
strikeouts          INT64       -- TARGET VARIABLE
innings_pitched     FLOAT64
hits_allowed        INT64
runs_allowed        INT64
earned_runs         INT64
walks              INT64
pitches_thrown      INT64       -- si disponible
decision            STRING      -- W/L/ND

-- Contexto pre-juego (snapshot al momento de la predicción)
season_k_rate       FLOAT64     -- K/9 season avg al momento del juego
recent_k_rate       FLOAT64     -- K/9 últimos 3 starts
season_era          FLOAT64
season_whip         FLOAT64
days_rest           INT64       -- días desde último start
pitch_count_last    INT64       -- pitches en último start

-- Opponent features
opp_team_k_pct      FLOAT64    -- % ponche del equipo oponente (season)
opp_team_k_pct_7d   FLOAT64    -- % ponche últimos 7 días
opp_vs_hand_k_pct   FLOAT64    -- K% del oponente vs LHP o RHP

-- Game context
game_total_ou       FLOAT64    -- Over/under del juego
run_line_spread     FLOAT64    -- Run line (favorito/underdog)
prop_line_ks        FLOAT64    -- Línea de K's del prop (lo que vamos a batir)
prop_odds_over      INT64      -- Momios del over (american)
prop_odds_under     INT64      -- Momios del under (american)

-- Metadata
ingested_at         TIMESTAMP
predicted_ks        FLOAT64    -- Predicción del modelo (se llena post-predicción)
prediction_edge     FLOAT64    -- predicted - prop_line
bet_placed          BOOL       -- ¿Se colocó en paper trading?

```

**Tabla: `mlb_paper_trades`** (reutiliza estructura genérica del framework)

```
trade_id            STRING
sport               STRING      -- 'MLB'
market_type         STRING      -- 'pitcher_strikeouts'
player_id           INT64
game_id             INT64
game_date           DATE
prop_line           FLOAT64
bet_direction       STRING      -- 'over' | 'under'
odds_at_bet         INT64
model_prediction    FLOAT64
edge_at_bet         FLOAT64
kelly_fraction      FLOAT64
bet_size_units      FLOAT64
result              STRING      -- 'win' | 'loss' | 'push' | 'pending'
actual_value        FLOAT64     -- K's reales
pnl_units           FLOAT64
clv_at_close        FLOAT64     -- Closing line value
created_at          TIMESTAMP
settled_at          TIMESTAMP
```

---

## 3. Feature Engineering — Pitcher Strikeouts

### 3.1 Features del Pitcher (señal principal)

| Feature | Cálculo | Fuente | Rationale |
|---|---|---|---|
| `season_k9` | (K / IP) × 9, season to date | `season_stats` | Baseline de talento del pitcher |
| `recent_k9_3starts` | K/9 de los últimos 3 starts | `stats` (game logs) | Forma reciente, ajusta por slumps/hot streaks |
| `recent_k9_5starts` | K/9 de los últimos 5 starts | `stats` | Ventana más estable |
| `season_kpct` | K / batters faced, season | `season_stats` | Alternativa a K/9, normalizada por batters enfrentados |
| `days_rest` | Días desde el último start | `games` + `stats` | Fatiga vs frescura (sweet spot ~5 días) |
| `pitch_count_last` | Pitches lanzados en el start anterior | `stats` | Carga reciente del brazo |
| `avg_ip_per_start` | IP promedio por start, season | `season_stats` | Proxy de cuánto tiempo estará en el juego |
| `season_whip` | (BB + H) / IP | `season_stats` | Control general — pitchers con WHIP alto enfrentan más batters |
| `home_away_k_split` | K/9 en home vs away | `player_splits` | Algunos pitchers son significativamente mejores en casa |

### 3.2 Features del Oponente (segundo driver)

| Feature | Cálculo | Fuente | Rationale |
|---|---|---|---|
| `opp_team_kpct_season` | K% del equipo rival en la temporada | `stats` (agregado) | Qué tanto poncha este equipo |
| `opp_team_kpct_14d` | K% del equipo en últimos 14 días | `stats` (rolling) | Racha reciente del lineup oponente |
| `opp_vs_hand_kpct` | K% del equipo vs LHP o RHP | `player_splits` | Un equipo que poncha 28% vs LHP pero 22% vs RHP es muy diferente |
| `opp_lineup_kpct` | K% promedio de los bateadores en el lineup confirmado | `lineups` + `stats` | Más granular que el equipo: el lineup de hoy puede ser peor/mejor que el promedio |

### 3.3 Features de Contexto

| Feature | Cálculo | Fuente | Rationale |
|---|---|---|---|
| `game_total_ou` | Over/under del juego | `betting_odds` | Juegos con total alto implican más batters enfrentados = más oportunidades de K |
| `implied_team_total` | Total de carreras implícito del equipo oponente | `betting_odds` | Si el oponente tiene total implícito bajo, el pitcher domina → más K |
| `run_line` | Spread del juego | `betting_odds` | Game script: pitcher de equipo favorito puede ir más innings |
| `is_home` | 1 si pitcher es home, 0 si away | `games` | Factor simple pero significativo |
| `day_of_week` | Lun-Dom | `games` | Puede capturar efectos de scheduling |

### 3.4 Features de Matchup Histórico (si hay data suficiente)

| Feature | Cálculo | Fuente | Rationale |
|---|---|---|---|
| `pitcher_vs_team_k9` | K/9 histórico de este pitcher vs este equipo | `player_vs_player` | Algunos pitchers dominan ciertos equipos consistentemente |
| `pitcher_vs_team_games` | # de juegos históricos vs este equipo | `player_vs_player` | Sample size check: solo usar si N ≥ 3 |

---

## 4. Arquitectura del Modelo

### 4.1 Approach: Stacking Ensemble (misma arquitectura que Oráculo NBA)

```
Capa 1 — Base Models:
├── LightGBM (captura interacciones no lineales pitcher × oponente)
├── Ridge Regression (baseline lineal, regularizado)
└── Random Forest (robusto a outliers)

Capa 2 — Meta-Model:
└── Logistic Regression sobre predicciones de Capa 1
    → Output: Probabilidad de Over/Under X.5 K's
```

### 4.2 Target Variable

**Regresión:** Predecir K's exactos del pitcher.  
**Clasificación (para betting):** P(K > línea de prop) vs P(K ≤ línea de prop).

El modelo entrena como regresión y luego se convierte en clasificación comparando la predicción con la línea del prop para calcular probabilidad implícita y edge.

### 4.3 Training Data

- **Fuente:** Game logs históricos 2022-2025 (BallDontLie tiene data desde 2002, pero 2022+ es más relevante por cambios de reglas).
- **Split:** Train en 2022-2024, Validation en primera mitad 2025, Test en segunda mitad 2025.
- **Filtro:** Solo pitchers abridores con ≥ 5 starts en la muestra. Excluir juegos acortados por lluvia o bullpen games.
- **Muestra estimada:** ~4,500 starts de pitcher por temporada × 3 temporadas de training = ~13,500 observaciones.

### 4.4 Calibración para Betting

Una vez que el modelo produce P(Over), se compara con la probabilidad implícita del momio:

```
modelo_prob = P(Over K's) del modelo
implied_prob = convertir momio americano a probabilidad
edge = modelo_prob - implied_prob

Si edge > umbral (e.g., 3%) → generar señal de apuesta
Kelly fraction = edge / (odds - 1) para sizing
```

---

## 5. Sprint Plan — Semana a Semana

### Semana 2 (Abr 14-20) — Setup + Ingesta Histórica
**Horas:** 10 | **Prioridad:** Datos ante todo

- [ ] Activar BallDontLie GOAT tier para MLB ($39.99)
- [ ] Explorar endpoints: hacer llamadas manuales a `/stats`, `/season_stats`, `/player_splits` para entender la estructura de datos
- [ ] Crear tablas BigQuery: `mlb_pitcher_game_logs`, esqueleto de `mlb_paper_trades`
- [ ] Script de ingesta histórica: descargar game logs de pitchers 2022-2025 via `/stats`
- [ ] Validar data: comparar muestra de K's contra Baseball Reference para verificar accuracy
- [ ] **Entregable:** 13,000+ game logs de pitchers en BigQuery, listos para feature engineering

**Riesgo:** BallDontLie puede no tener granularidad suficiente en stats históricas. Si falta data, backup: usar pybaseball para llenar huecos históricos (gratis).

### Semana 3 (Abr 21-27) — Feature Engineering + Moneyline Model
**Horas:** 10

- [ ] Construir pipeline de feature engineering: calcular todos los features de la Sección 3 a partir de los game logs en BigQuery
- [ ] Calcular rolling features (recent_k9_3starts, opp_kpct_14d) con window functions en BigQuery
- [ ] Adaptar Game Script / Moneyline model para MLB run line (base del NBA Moneyline model)
- [ ] Exploration data analysis: distribución de K's, correlaciones feature-target, outlier analysis
- [ ] **Entregable:** Feature matrix completa en BigQuery. EDA notebook con insights iniciales.

### Semana 4 (Abr 28 – May 4) — Modelo V1 + Decisión NBA
**Horas:** 10 | **Nota:** Esta semana también evalúas NBA V1 (4 semanas de paper trading)

- [ ] **DECISIÓN NBA V1:** Evaluar resultados. Go/no-go.
- [ ] Entrenar Capa 1: LightGBM, Ridge, Random Forest en data 2022-2024
- [ ] Evaluar en validation set (primera mitad 2025): MAE, calibración de probabilidades
- [ ] Entrenar meta-model (Capa 2) con out-of-fold predictions de Capa 1
- [ ] Backtest en test set (segunda mitad 2025): simular paper trading retrospectivo
- [ ] **Entregable:** Modelo V1 entrenado. Métricas de backtest: accuracy, calibration plot, simulated ROI.

### Semana 5 (May 5-11) — Pipeline de Producción
**Horas:** 10

- [ ] Script de ingesta diaria: Cloud Run Job que cada mañana ingesta games, stats, lineups, odds, props del día
- [ ] Script de predicción: toma el lineup confirmado, genera features, corre el modelo, calcula edge vs prop line
- [ ] Integrar con Paper Trading framework: si edge > umbral → registrar apuesta simulada en BigQuery
- [ ] Integrar con sistema de alertas por email: notificación cuando hay señal de apuesta
- [ ] Testing end-to-end con datos del día actual
- [ ] **Entregable:** Pipeline completo corriendo en GCP. Predicciones generándose diariamente.

### Semana 6 (May 12-18) — Launch Paper Trading
**Horas:** 10

- [ ] **MLB V1 ENTRA EN PAPER TRADING** — comienza el reloj de 5 semanas
- [ ] Monitorear primer semana: verificar que las predicciones son razonables, que el pipeline no falla
- [ ] Fix bugs y edge cases (juegos pospuestos, doubleheaders, pitcher cambios de último minuto)
- [ ] Si hay tiempo: integrar The-Odds-API para complementar/validar odds de props de MLB contra BallDontLie
- [ ] **Entregable:** Paper trading activo. Dashboard de tracking en BigQuery.

### Semanas 7-10 (May 18 – Jun 14) — Paper Trading Activo + Monitoreo
**Horas:** ~3-4/semana en MLB (resto va a NFL prep)

- [ ] Monitoreo semanal: ROI, win rate, CLV, calibration drift
- [ ] Ajustes menores si se detectan problemas (no rediseño completo — eso es V2)
- [ ] Documentar observaciones para el paper de tesis
- [ ] **Semana 10: DECISIÓN MLB V1** — Evaluar 5 semanas de paper trading

---

## 6. Criterios Go/No-Go (Semana 10)

| Métrica | Umbral | Notas |
|---|---|---|
| **Muestra mínima** | ≥ 80 apuestas simuladas | Con ~15 juegos/día y selectividad, esto es alcanzable en 5 semanas |
| **ROI** | > 0% | Rentabilidad neta positiva |
| **CLV** | > 50% de apuestas con +CLV | ¿Estamos capturando líneas antes de que se muevan? |
| **Sharpe Ratio** | > 0.5 | Rendimiento ajustado por riesgo |
| **p-value** | < 0.10 | Significancia estadística del ROI |
| **Max Drawdown** | < 50% | Kill switch automático si se alcanza |
| **Calibración** | Brier Score < baseline | Las probabilidades del modelo son mejores que "moneda al aire" |

**Si NO-GO → V2 Plan:**
- Incorporar batter props (hits, total bases) con datos de pybaseball/Statcast
- Añadir features avanzados: exit velocity esperado del oponente, barrel rate, chase rate
- Pipeline de pybaseball se construye como fuente complementaria (gratis)
- 5 semanas adicionales de paper trading

**Si GO →**
- Continuar paper trading, documentar para tesis
- Considerar expandir a pitcher outs (innings pitched) como prop adicional dentro del mismo framework

---

## 7. Dependencias y Checklist Pre-Build

### Antes de empezar Semana 2:

- [ ] **Cuenta BallDontLie:** Verificar que el tier GOAT incluye todos los endpoints MLB necesarios
- [ ] **The-Odds-API:** Verificar que la suscripción actual cubre MLB player props (pitcher strikeouts)
- [ ] **Presupuesto:** Confirmar que al terminar NBA, los $40 liberados cubren los $39.99 de MLB
- [ ] **BigQuery:** Verificar que el dataset y permisos están listos para nuevas tablas
- [ ] **Cloud Run:** Verificar que el job scheduler puede manejar un segundo job (MLB) sin conflictos
- [ ] **Paper Trading Framework:** Confirmar que acepta `sport='MLB'` y `market_type='pitcher_strikeouts'` sin modificaciones
- [ ] **Email Alerts:** Verificar que el sistema de alertas es sport-agnostic

### Herramientas ya listas (reutilizables del NBA):

- ✅ Paper Trading Framework (genérico)
- ✅ EV Calculator
- ✅ Kelly Criterion sizing
- ✅ Alert system
- ✅ BigQuery pipeline patterns
- ✅ Cloud Run Job template
- ✅ The-Odds-API integration (ya pagándose, reutilizar adapter de NBA para MLB)

### Por construir desde cero:

- 🔨 BallDontLie MLB API adapter (nuevo, pero mismos patrones que NBA)
- 🔨 Feature engineering pipeline para pitchers
- 🔨 Modelo de strikeouts (arquitectura stacking se reutiliza, features son nuevos)
- 🔨 Moneyline/Run Line model para MLB (adaptar NBA game script engine)
- 🔨 Ingesta diaria de lineups + props (timing diferente a NBA)

---

## 8. Riesgos Específicos de MLB V1

| Riesgo | Prob | Impacto | Mitigación |
|---|---|---|---|
| BallDontLie no tiene pitch count por juego | Media | Medio | Usar IP como proxy de workload. Agregar pybaseball para pitch counts si es crítico. |
| Lineups se confirman tarde (~2hrs antes) | Alta | Bajo | Pipeline de predicción corre 2 veces: una preliminar con lineup proyectado, una final con lineup confirmado. |
| Pitchers scratched (cambio de último minuto) | Media | Medio | Monitorear `/games` por cambios de status. Cancelar señal si el pitcher cambia. |
| Doubleheaders (7 innings) | Baja | Medio | Filtrar o ajustar modelo — menos innings = menos K's por definición. Feature `is_doubleheader`. |
| Rain delays / postponements | Media | Bajo | El pipeline verifica game status antes de procesar. Graceful skip. |
| K line no disponible para todos los pitchers | Media | Medio | Solo generar señales donde hay prop line disponible. Trackear cobertura de líneas. |
| Muestra insuficiente en 5 semanas | Baja | Alto | Con selectividad moderada (~3-4 apuestas/día), 5 semanas dan ~100+ trades. Ajustar umbral de edge si la muestra va lenta. |

---

## 9. Calendario Visual

```
Semana:  2      3      4      5      6      7    8    9    10
         Abr14  Abr21  Abr28  May5   May12  May18...      Jun14
         ┌──────┬──────┬──────┬──────┬──────┬──────────────────┐
  DATA   │██████│      │      │      │      │                  │
         │Ingesta      │      │      │      │                  │
         │histórica    │      │      │      │                  │
         ├──────┼──────┤      │      │      │                  │
  FEAT   │      │██████│      │      │      │                  │
         │      │Feature Eng  │      │      │                  │
         │      │+ EDA │      │      │      │                  │
         ├──────┼──────┼──────┤      │      │                  │
  MODEL  │      │      │██████│      │      │                  │
         │      │      │Train+│      │      │                  │
         │      │      │Backtest     │      │                  │
         ├──────┼──────┼──────┼──────┤      │                  │
  PIPE   │      │      │      │██████│      │                  │
         │      │      │      │Pipeline      │                  │
         │      │      │      │producción    │                  │
         ├──────┼──────┼──────┼──────┼──────┼──────────────────┤
  PAPER  │      │      │      │      │██████│██████████████████│
  TRADE  │      │      │      │      │Launch│  5 semanas       │
         │      │      │      │      │      │  paper trading   │
         ├──────┼──────┼──────┼──────┼──────┼──────────────────┤
  NBA    │ V1 paper trading ──┤DECISIÓN     │                  │
         │ (sigue corriendo)  │V1    │      │                  │
         └──────┴──────┴──────┴──────┴──────┴──────────────────┘
                                                        ▲
                                                   DECISIÓN
                                                   MLB V1
```

---

## 10. Siguiente Paso Inmediato

**Esta semana (Semana 1, Abr 7-13):**
Mientras NBA V1 paper trading sigue corriendo, el tiempo de esta semana se dedica a:
1. Generalizar el Paper Trading Framework si quedan ajustes pendientes
2. Crear la cuenta BallDontLie MLB GOAT tier (o upgradear la existente)
3. Hacer 2-3 llamadas exploratorias a la API MLB para validar que los datos están como esperamos

**Semana 2 arranca el build formal de Diamante.**