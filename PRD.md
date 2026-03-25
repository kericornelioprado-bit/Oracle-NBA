# PRD — Oráculo NBA V2: Motor de Proyección de Player Props

**Estado:** Definido / Listo para Arquitectura
**Capital de Simulación:** $20,000 MXN (Ficticios)
**Filosofía:** *"Si requiere intervención humana, no es un sistema; es una hoja de cálculo con pasos extra."*
**Versión:** 2.0 — Corregido con mecanismos de defensa, diagnóstico y presupuesto de API.

---

## 1. Visión del Producto

Migrar de un modelo de predicción de resultados (Moneyline) a un sistema de arbitraje de valor en Player
Props. El "Edge" no es predecir la estadística final por sí sola, sino predecir el **Game Script** (Contexto
del Juego) para proyectar minutos de juego antes de que las casas de apuestas ajusten sus líneas.

---

## 2. El Portafolio de 20 Jugadores (Estructura de Capital)

El sistema gestionará un portafolio dinámico dividido en tres niveles de riesgo y asignación de capital:

| Tier | Perfil | Jugadores | % Capital | Lógica de Selección |
|------|--------|-----------|-----------|---------------------|
| Tier 1: Núcleo | 6tos Hombres | 10 | 50% | Sensibilidad al margen (minute_swing: blowout vs close) |
| Tier 2: Volatilidad | Injury Heirs | 7 | 35% | Beneficiarios directos de bajas (next man up) |
| Tier 3: Señuelos | Superestrellas | 3 | 15% | Triggers tácticos (assists/props secundarios solamente) |

### 2.1 Criterios Cuantitativos de Selección Automática

**Tier 1 — Núcleo:**

| Criterio | Umbral |
|----------|--------|
| Minutos promedio | 18-25 min/juego |
| minute_swing (min en blowout − min en partido cerrado) | > +5.0 |
| Juegos jugados en temporada | > 30 |
| Rol | Suplente consistente (no fluctúa entre titular/banco) |
| Std de minutos | > 5 min (alta varianza = sensible al contexto) |

**Tier 2 — Volatilidad:**

| Criterio | Umbral |
|----------|--------|
| Minutos promedio | 10-20 min/juego |
| Minutos cuando titular de su posición está OUT | > 140% de su promedio |
| Juegos jugados en temporada | > 20 |
| Existe titular claro por delante en la rotación | Sí (injury heir identificable) |

**Tier 3 — Superestrellas Condicionales:**

| Criterio | Umbral |
|----------|--------|
| Usage rate | Top 15 de la liga |
| Varianza en assists por matchup táctico | Std > 2.0 |
| Mercado objetivo | Solo assists, turnovers, o props secundarios. NUNCA puntos. |
| Frecuencia máxima de apuesta | 1-2 veces por semana |

### 2.2 Criterios de Exclusión Automática (Aplican a Todos los Tiers)

| Criterio | Razón |
|----------|-------|
| Jugador lesionado (OUT > 7 días) | Sin actividad, sin datos recientes |
| Jugador con < 20 juegos en la temporada | Datos insuficientes |
| Jugador traspasado en los últimos 14 días | Rol incierto en equipo nuevo |
| Equipo en bottom 3 del standings | Rotaciones caóticas por tanking |

---

## 3. El Motor de Proyección de Minutos (El "Cerebro")

Este es el componente nuevo que actúa como puente entre el Moneyline y los Props.

### 3.1 Inputs Automáticos

| Input | Fuente | Frecuencia |
|-------|--------|------------|
| Game Script (margen esperado) | Modelo Moneyline | Diario, 16:30 CST |
| Injury Report (OUT/GTD/Probable) | nba_api o scraping | Diario, 16:30 CST |
| Schedule (B2B, días descanso, localía) | nba_api | Diario |
| Roster y rotación actual | nba_api | Semanal (domingo) |

### 3.2 Heurísticas de Decisión (Fase 1 — MVP)

```
minutos_proyectados = minutos_avg_L10

REGLA 1 — Game Script:
  IF predicted_margin > +15 (BLOWOUT_WIN):
      minutos_proyectados *= 1.25    # Garbage time boost
  ELIF predicted_margin < -15 (BLOWOUT_LOSS):
      minutos_proyectados *= 1.15    # Equipo rinde la toalla
  ELIF ABS(predicted_margin) < 8 (COMPETITIVE):
      minutos_proyectados *= 0.95    # Titulares absorben todo
  ELSE (LEAN):
      sin ajuste

REGLA 2 — Lesiones:
  IF starter_misma_posicion == OUT:
      minutos_proyectados += starter_avg_minutes * 0.60
  ELIF starter_misma_posicion == QUESTIONABLE:
      SKIP → No apostar en este jugador hoy (incertidumbre)

REGLA 3 — Fatiga:
  IF is_back_to_back:
      minutos_proyectados *= 0.95

REGLA 4 — Cap:
  minutos_proyectados = MIN(minutos_proyectados, 38)
```

### 3.3 Validación del Motor de Minutos

| Métrica | Target | Cómo se mide |
|---------|--------|--------------|
| MAE de minutos proyectados vs reales | < 4.0 minutos | Walk-forward sobre datos históricos |
| Accuracy de clasificación de Game Script | > 65% | % de blowouts correctamente identificados |

Si el MAE supera 4.0 en producción, el sistema levanta un flag en el reporte semanal.

---

## 4. Mercados Activos y Priorización

Basado en la oferta confirmada de la casa de apuestas:

### Fase 1 — Mercados Primarios (Sprint 3)

| Mercado | API Market Key | Razón |
|---------|---------------|-------|
| Total de Rebotes (O/U) | `player_rebounds` | Alta correlación con minutos, modelable |
| Total de Asistencias (O/U) | `player_assists` | Sensible a matchup táctico |
| Total P+R+A | combo | Casas suman promedios sin ajustar correlación |

### Fase 2 — Mercados Secundarios (Post Sprint 4)

| Mercado | Razón |
|---------|-------|
| Rebotes + Asistencias (R+A) | Menos líquido, potencialmente más ineficiente |
| Puntos + Rebotes (P+R) | Segundo combo más popular |
| Total de Robos (O/U) | Alta varianza, nicho |
| Total de Bloqueos (O/U) | Alta varianza, nicho |

### Fase 3 — Descartados o Diferidos

| Mercado | Razón |
|---------|-------|
| Puntos del jugador (O/U) | Mercado más eficiente, casas lo modelan con precisión |
| Primer Anotador | Modelo completamente diferente (probabilístico, no regresión) |
| Tiros de 3 Puntos | Extremadamente volátil, difícil de predecir |

---

## 5. Gestión Financiera y Auto-Protección del Bankroll

### 5.1 Parámetros Iniciales

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Bankroll inicial | $20,000 MXN | Capital ficticio de prueba |
| Duración mínima de simulación | 30 días | ~100-200 picks para significancia estadística |
| Método de sizing | Kelly Fraccional (1/4 = 0.25) | Conservador, protege contra varianza |
| Filtro de EV mínimo | > 3% | Solo apuestas con margen de seguridad |

### 5.2 Límites Duros (Hard Caps)

| Límite | Valor | Razón |
|--------|-------|-------|
| Apuesta máxima individual | 5% del bankroll actual | Ninguna apuesta compromete más del 5% |
| Apuesta mínima | $50 MXN | Debajo de esto, el edge se erosiona con la granularidad |
| Máximo apuestas por día | 5 | Priorizar por EV descendente |
| Exposición máxima diaria | 20% del bankroll | Nunca más del 20% en riesgo simultáneo |
| Stop loss diario | -8% del bankroll | Si pierde > $1,600 en un día, no apuesta más ese día |

### 5.3 Protección de Drawdown

| Situación | Condición | Acción Automática |
|-----------|-----------|-------------------|
| Operación normal | Bankroll entre $18,000 y $24,000 | Kelly 1/4 estándar |
| Drawdown leve | Bankroll entre $16,000 y $18,000 (-10% a -20%) | Reducir a Kelly 1/8 (más conservador) |
| Drawdown severo | Bankroll < $16,000 (-20%) | PAUSAR apuestas 3 días. Solo observar y registrar picks fantasma. |
| Recuperación post-pausa | Bankroll sube 2 días consecutivos | Reanudar con Kelly 1/8 por 7 días, luego volver a 1/4 |
| Bankroll en crecimiento | Bankroll > $22,000 (+10%) | Kelly 1/4 normal; stakes suben proporcionalmente al bankroll |

### 5.4 Criterios de Éxito/Fracaso (Post 30 Días)

| Resultado | Señal | Acción |
|-----------|-------|--------|
| ROI > +3% Y CLV > +1.5% Y hit rate > 53% | 🟢 Luz verde | Pasar a dinero real con bankroll conservador |
| ROI entre 0% y +3% Y CLV positivo | 🟡 Luz amarilla | Extender simulación 2 semanas más |
| ROI < 0% PERO CLV > +1.5% | 🟡 Luz amarilla | El modelo tiene edge pero varianza no cooperó. Extender. |
| ROI < 0% Y CLV < 0% | 🔴 Luz roja | El modelo no tiene edge. Regresar a Sprint 3. |
| ROI < -15% | 🔴 Rojo crítico | Algo fundamentalmente mal. Revisar lógica completa. |

---

## 6. Flujo Operativo Diario (16 Minutos)

Ejecución One-Shot a las **16:30 CST:**

```
FASE 0: RESOLUCIÓN DEL DÍA ANTERIOR (2 min)
├── Descargar box scores de los juegos de ayer
├── Para cada apuesta de ayer:
│   ├── Obtener stat real del jugador
│   ├── Determinar: WIN / LOSS
│   ├── Calcular P&L de la apuesta
│   ├── Registrar cuota de cierre (para CLV)
│   └── Calcular CLV = (cuota_ejecución - cuota_cierre) / cuota_cierre
├── Actualizar bankroll
├── Actualizar métricas acumuladas (ROI, hit rate, racha, CLV promedio)
├── Verificar reglas de protección:
│   ├── ¿Drawdown severo? → PAUSAR
│   └── ¿En modo Kelly 1/8? → Verificar si puede volver a 1/4
└── Persistir en betting_history.json

FASE 1: RECOLECCIÓN (3 min)
├── Cargar portfolio.json (los 20 jugadores de la semana)
├── Descargar schedule: ¿quiénes de los 20 juegan hoy?
├── Descargar injury report actualizado
├── Descargar cuotas de Moneyline (The-Odds-API: 1 request)
└── Descargar cuotas de Player Props para juegos relevantes
    (The-Odds-API: 1 request por juego con jugadores del portafolio)

FASE 2: GAME SCRIPT (2 min)
├── Correr modelo Moneyline para cada juego del día
├── Clasificar cada juego:
│   ├── BLOWOUT_HOME: margen predicho > +12
│   ├── BLOWOUT_AWAY: margen predicho < -12
│   ├── COMPETITIVE: margen entre -8 y +8
│   └── LEAN: margen entre 8-12 en cualquier dirección
└── Output: game_scripts del día

FASE 3: PROYECCIÓN DE MINUTOS (2 min)
├── Para cada jugador del portafolio que juega hoy:
│   ├── Aplicar heurísticas de la Sección 3.2
│   └── Si starter de su posición es QUESTIONABLE → SKIP jugador
└── Output: minutos_proyectados por jugador

FASE 4: PREDICCIÓN DE STATS (3 min)
├── Para cada jugador con minutos proyectados:
│   ├── Calcular features (stat_per_minute, DvP, pace, home/away)
│   ├── stat_esperada = modelo.predict(features) o heurística
│   ├── Calcular P(Over línea):
│   │   mean = stat_esperada
│   │   std = desviación histórica del jugador
│   │   P(Over) = 1 - norm.cdf(línea, mean, std)
│   └── Repetir para: REB, AST, P+R+A, P+R, R+A
└── Output: predicciones con P(Over/Under) por mercado

FASE 5: MOTOR DE DECISIÓN (2 min)
├── Para cada predicción:
│   ├── Calcular EV = (P_modelo × payout_neto) - (1 - P_modelo)
│   ├── Filtrar: EV > 3%
│   ├── Calcular Kelly: stake = bankroll × kelly_fraction × 0.25
│   ├── Aplicar caps (mín $50, máx 5% bankroll)
│   └── Verificar stop loss diario y exposición total
├── Si exposición total > 20% del bankroll:
│   └── Recortar apuestas más débiles proporcionalmente
└── Output: lista_apuestas_del_dia (máximo 5)

FASE 6: REPORTE Y ENVÍO (2 min)
├── Generar correo con estructura de la Sección 7
└── Enviar correo

TOTAL: ~16 minutos
MARGEN HASTA TIP-OFF: ~74 minutos para colocar apuestas
```

---

## 7. Estructura del Correo Diario

El correo es la herramienta de **diagnóstico**, no solo de notificación. Contiene 4 secciones obligatorias:

### Sección 1: Balance General

```
Bankroll inicial:      $20,000.00
Bankroll actual:       $XX,XXX.XX
P&L total:             +/- $X,XXX.XX (+/-X.X%)
Día de simulación:     N de 30
Apuestas totales:      N
Record:                XW - XL (XX.X%)
ROI acumulado:         +/-X.X%
CLV promedio:          +/-X.X%
Racha actual:          XW / XL
Estado del sistema:    ACTIVO / PAUSA (drawdown) / KELLY REDUCIDO
```

### Sección 2: Resultados del Día Anterior

Para cada apuesta de ayer:

```
✅/❌ | [Jugador] [OVER/UNDER] [línea] [stat]
   Predicción: E[STAT] = X.X | Real: X
   Cuota ejecución: -XXX | Cuota cierre: -XXX | CLV: +/-X.X%
   Stake: $XXX | P&L: +/- $XXX
   Contexto: [Game Script acertado/fallado] + [razón del resultado]

P&L del día anterior: +/- $XXX
```

### Sección 3: Picks de Hoy

Para cada apuesta recomendada:

```
PICK N | Tier X ([nombre del tier])
  Jugador:        [Nombre] ([Equipo])
  Prop:           [OVER/UNDER] [X.X] [Stat]
  Predicción:     E[STAT] = X.X | P(Over/Under) = XX.X%
  Cuota:          -XXX ([Casa])
  Implied prob:   XX.X%
  EV:             +X.X%
  Stake:          $XXX (X.X% del bankroll)
  Game Script:    [BLOWOUT/COMPETITIVE/LEAN] — margen predicho: +/-XX
  Min proyectados: XX (vs avg XX)
  Razón:          [Explicación en 1-2 líneas del por qué de esta apuesta]
```

### Sección 3b: Razones de NO Apuesta (Auditoría)

```
NO PICK | [Jugador] ([Equipo]): [Razón]
  ej: "Malik Monk (SAC): Game Script COMPETITIVE. Minutos normales. Sin edge."
  ej: "Aaron Gordon (DEN): DvP del rival top 5 en REB. Matchup desfavorable."
  ej: "Jalen Williams (OKC): Starter Chet Holmgren QUESTIONABLE → SKIP automático."
```

### Sección 4: Resumen de Exposición

```
Apuestas hoy:           N
Capital en riesgo:      $X,XXX (X.X% del bankroll)
Capital no apostado:    $XX,XXX (XX.X% del bankroll)
Stop loss restante:     $X,XXX antes de pausar el día
```

---

## 8. Correo Semanal (Domingos) y The Sunday Update

### 8.1 Actualización Automática del Portafolio

Cada domingo a las **23:59 CST**, el sistema ejecuta:

1. **Re-escanear la liga completa:**
   - Descargar game logs de todos los jugadores (últimas 4 semanas).
   - Recalcular minute_swing, injury_heir_score, y volatilidad de stats.

2. **Seleccionar portafolio automáticamente:**
   - Aplicar criterios cuantitativos de la Sección 2.1.
   - Aplicar exclusiones de la Sección 2.2.
   - Guardar en `portfolio.json`.

3. **Re-evaluar modelo (con condiciones):**
   - Calcular MAE de predicciones de la última semana.
   - **Solo reentrenar si:** MAE semanal > MAE histórico × 1.15 (15% de degradación).
   - Si no hay degradación, el modelo se mantiene intacto.
   - **Nunca reentrenar por reentrenar.** El overfitting es peor que un modelo ligeramente subóptimo.

### 8.2 Contenido del Correo Semanal

```
PERFORMANCE DE LA SEMANA:
  Apuestas: N | Record: XW-XL | P&L: +/-$X,XXX | ROI: +/-X.X%
  CLV promedio: +/-X.X%

ANÁLISIS POR TIER:
  Tier 1: N apuestas | XW-XL | +/-$X,XXX | ROI +/-X.X%
  Tier 2: N apuestas | XW-XL | +/-$X,XXX | ROI +/-X.X%
  Tier 3: N apuestas | XW-XL | +/-$X,XXX | ROI +/-X.X%

ANÁLISIS POR MERCADO:
  Rebounds O/U:    N apuestas | XW-XL | +/-$X,XXX
  Assists O/U:     N apuestas | XW-XL | +/-$X,XXX
  Combos (P+R+A):  N apuestas | XW-XL | +/-$X,XXX

ACTUALIZACIÓN DE PORTAFOLIO:
  Jugadores que SALEN: [nombre] — [razón]
  Jugadores que ENTRAN: [nombre] — [razón y métricas]
  Portafolio semana siguiente: [lista de 20]

DIAGNÓSTICO DEL MODELO:
  MAE de minutos: X.X (target < 4.0) [✅/⚠️]
  MAE de stats: X.X [✅/⚠️]
  Game Script accuracy: XX% [✅/⚠️]
  Calibración: Cuando dice 70% → real XX% [✅/⚠️]
  ¿Reentrenamiento necesario? [SÍ: razón / NO]
  Flags: [Observaciones automáticas sobre patrones detectados]
```

---

## 9. Presupuesto de API (The-Odds-API — Tier Gratuito: 500 req/mes)

### 9.1 Consumo Estimado Diario

| Consulta | Requests | Notas |
|----------|----------|-------|
| Moneyline (todos los juegos del día) | 1 | Endpoint `/odds` con markets=h2h |
| Player Props (por juego con jugadores del portafolio) | ~5-8 | Solo juegos donde al menos 1 de los 20 juega. Endpoint `/events/{id}/odds` |
| **Total diario estimado** | **~6-9** | |

### 9.2 Consumo Estimado Mensual

| Concepto | Requests |
|----------|----------|
| Diario: ~8 requests × 30 días | ~240 |
| Buffer para retries y debugging | ~50 |
| **Total mensual estimado** | **~290** |
| **Margen disponible** | **~210 requests** |

### 9.3 Estrategias de Optimización

| Estrategia | Ahorro |
|------------|--------|
| Solo consultar props de juegos donde juegan los 20 del portafolio (no todos los juegos) | ~40% de requests |
| Cachear cuotas de Moneyline (no re-consultar si ya las tienes del día) | 1-2 req/día |
| No consultar props de jugadores en SKIP (starter Questionable) | Variable |
| En días sin juegos de jugadores del portafolio: 0 requests de props | ~5-8 req ahorrados |

### 9.4 Contingencia

Si a mitad de mes el consumo supera las proyecciones:
- Priorizar solo Tier 1 (los 10 del núcleo) y reducir consultas de Tier 2 y 3.
- Último recurso: upgrade a plan básico (~$15 USD/mes = ~300 MXN).

---

## 10. Datos a Persistir (Dataset de Auditoría)

Cada apuesta registrada en `betting_history.json` (o base de datos) incluye:

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| fecha | date | 2026-03-25 |
| jugador | string | Naz Reid |
| tier | int | 1 |
| equipo | string | MIN |
| rival | string | LAL |
| mercado | string | player_rebounds |
| direccion | string | OVER |
| linea | float | 7.5 |
| cuota_ejecucion | int | -115 |
| P_modelo | float | 0.742 |
| stat_esperada | float | 9.2 |
| EV | float | 0.197 |
| stake | float | 400.00 |
| game_script | string | BLOWOUT_HOME |
| predicted_margin | float | +14.2 |
| min_proyectados | float | 27.0 |
| min_reales | float | 29.0 |
| stat_real | float | 11.0 |
| resultado | string | WIN |
| pnl | float | +348.00 |
| bankroll_post | float | 20348.00 |
| cuota_cierre | int | -130 |
| CLV | float | +0.013 |
| razon_apuesta | string | "Blowout MIN proyectado. DvP LAL #27 en REB." |

Este dataset es el activo más valioso de la simulación. Después de 30 días permite análisis de qué tier rinde, qué mercado tiene más edge, si el Game Script agrega valor real, y si el modelo tiene edge estadísticamente significativo.

---

## 11. Deuda Técnica Pendiente (Sprint 0)

### 11.1 Bug: Equipos Duplicados en el Reporte

- **Síntoma:** Algunos juegos aparecen duplicados en el correo de predicciones (detectado en V1).
- **Diagnóstico requerido:**
  - ¿La duplicación viene de nba_api (el mismo juego con IDs diferentes)?
  - ¿Viene de The-Odds-API (el mismo evento listado dos veces)?
  - ¿Es un problema de deduplicación en el pipeline de transformación?
- **Fix:** Agregar deduplicación por `(home_team, away_team, date)` como llave única.
- **Prioridad:** Alta.

### 11.2 Cron Job Fallido (V2 no envió correo el 24 de marzo)

- **Síntoma:** El sistema debió enviar correo a las 16:30 CST y no lo hizo.
- **Diagnóstico requerido (checklist):**
  1. ¿El job de Cloud Scheduler se ejecutó? → GCP Console → Cloud Scheduler → Historial.
  2. ¿Cloud Run recibió la invocación? → Cloud Run → Logs.
  3. ¿El contenedor arrancó y falló? → Buscar errores de dependencia, timeout, OOM.
  4. ¿El correo se generó pero no se envió? → Verificar credenciales SMTP / servicio de correo.
  5. ¿Hay un error en la V2 del código que no existía en V1? → Diff entre versiones.
- **Fix:** Depende del diagnóstico. Agregar notificación de fallo a Telegram como failsafe.
- **Prioridad:** Crítica — sin cron job, el sistema está muerto.

---

## 12. Timeline de Ejecución (Sprints)

| Sprint | Nombre | Entregable Principal | Dependencia |
|--------|--------|---------------------|-------------|
| Sprint 0 | Estabilización V1 | Cron job funcionando + bug duplicados resuelto | Ninguna |
| Sprint 1 | Pipeline de Stats Individuales | Dataset (jugador, juego) con features + stat real | Sprint 0 |
| Sprint 2 | Motor de Proyección de Minutos | Heurísticas implementadas, MAE < 4.0 en backtest | Sprint 1 |
| Sprint 3 | Modelado de Props + EV | Modelo de regresión + conversión a P(Over) + backtesting | Sprint 2 |
| Sprint 4 | Paper Trading | 30 días de simulación autónoma con $20,000 ficticios | Sprint 3 |
| Sprint 5 | Evaluación y Decisión | Aplicar criterios de Sección 5.4. Go / No-Go para dinero real. | Sprint 4 |
| Sprint 6 | Producción | Integración total en GCP + banca real dedicada | Sprint 5 (solo si 🟢) |

---

*Documento vivo. Actualizar después de cada Sprint con resultados y ajustes.*