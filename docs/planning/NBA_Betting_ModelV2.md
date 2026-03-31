# NBA Betting Model V2 — Plan Corregido y Definitivo

---

## 1. Deuda Técnica Pendiente (Resolver PRIMERO)

Antes de construir nada nuevo, hay que estabilizar lo que ya está en producción.

### 1.1 Bug: Equipos Duplicados en el Reporte
- Algunos juegos aparecen duplicados en el correo de predicciones (detectado en la V1)
- Revisar el pipeline de extracción de datos: probablemente se están jalando duplicados desde nba_api o The-Odds-API
- Verificar: ¿es un problema de deduplicación en la query, o es que la API devuelve el mismo juego con IDs diferentes?
- Prioridad: Alta — si el reporte tiene datos duplicados, las apuestas podrían duplicarse

### 1.2 Cron Job Fallido (V2 no envió correo hoy 24 de marzo)
- El Cloud Scheduler debió despertar al contenedor de Cloud Run a las 16:30 CST y no lo hizo (o lo hizo y falló silenciosamente)
- Revisar:
  - ¿El job de Cloud Scheduler se ejecutó? (logs en GCP Console → Cloud Scheduler → historial)
  - ¿Cloud Run recibió la invocación? (logs en Cloud Run → Logs)
  - ¿El contenedor arrancó y falló? (error de dependencia, timeout, OOM?)
  - ¿El correo se generó pero no se envió? (verificar credenciales de SMTP o servicio de correo)
- Prioridad: Crítica — sin el cron job, todo el sistema de producción está muerto

---

## 2. La Arquitectura Real del Sistema V2

### La Cadena de Valor (El Insight de Keri)

```
PASO 1: Modelo Moneyline (ya existe)
  ↓
  Output: Probabilidad de victoria → Game Script predicho
  ej: "Denver 82% de ganar → probable paliza de +15"
  
PASO 2: Motor de Proyección de Minutos
  ↓
  Input: Game Script + roster + injury report
  Output: Minutos proyectados por jugador
  ej: "Si paliza → Naz Reid jugará ~28 min (vs su promedio de 20)"
  
PASO 3: Modelo de Player Props
  ↓
  Input: Minutos proyectados + features del jugador + matchup
  Output: Stat esperada (rebounds, assists, etc.)
  ej: "Naz Reid → E[REB] = 9.8 (vs su promedio de 6.5)"
  
PASO 4: Motor de EV + Kelly (ya existe, se adapta)
  ↓
  Input: Stat esperada vs. línea de la casa
  Output: ¿Apostar? ¿Cuánto?
  ej: "Over 6.5 REB a -110 → EV = +22% → Kelly = 4.1% de banca"
```

Esto es fundamentalmente diferente a lo que yo proponía. No es "predice rebounds directo." Es "predice el contexto del juego → proyecta minutos → proyecta stats." La capa de Game Script es lo que le da edge a tu modelo sobre las casas, que ajustan líneas de role players basándose en promedios, no en predicciones de cómo se desarrollará el partido.

---

## 3. El Portafolio de 20 Jugadores

### 3.1 Estructura del Portafolio

| Tier | Nombre | Jugadores | % del Capital | Lógica de Selección |
|---|---|---|---|---|
| Tier 1 | Núcleo: 6tos Hombres y Rotación Clave | 10 | 50% | Minutos entre 18-25, alta varianza de minutos según game script |
| Tier 2 | Activos de Volatilidad: Novatos y Especialistas | 7 | 35% | Beneficiarios directos de lesiones y cambios de rotación |
| Tier 3 | Señuelos: Superestrellas Condicionales | 3 | 15% | Solo en líneas secundarias (assists, turnovers) con trigger táctico |

### 3.2 Criterios de Selección por Tier

**Tier 1 — Núcleo (10 jugadores)**

| Criterio | Umbral | Razón |
|---|---|---|
| Minutos promedio | 18-25 min/juego | Suficientes para generar stats, no titulares inamovibles |
| Varianza de minutos | Std > 5 min | Alta sensibilidad al game script |
| Correlación minutos-margen | Alta (positiva o negativa) | Sus minutos cambian según si el equipo va ganando/perdiendo |
| Juegos jugados | > 30 en la temporada | Datos suficientes para modelar |
| Consistencia de rol | Siempre del banco, no fluctúa entre titular/suplente | Rol predecible |

Perfil tipo: Naz Reid, Malik Monk, Bobby Portis, Cam Johnson (en rol de banco), Jalen Duren, etc.

El edge: Las Vegas pone sus líneas basándose en promedios de temporada. Si tu modelo de Moneyline predice una paliza (margen > +15), estos jugadores jugarán 25-30 minutos en vez de 18. La casa no ajusta la línea del suplente anticipando garbage time; tú sí.

**Tier 2 — Volatilidad (7 jugadores)**

| Criterio | Umbral | Razón |
|---|---|---|
| Tipo de jugador | Novatos, especialistas 3&D, pívots suplentes | Alta sensibilidad a lesiones del titular |
| Minutos promedio | 10-20 min/juego | Bajo baseline = mayor upside si titular se lesiona |
| "Injury heir" | Siguiente en la rotación si el titular cae | Hereda minutos y oportunidades |
| Tiempo de reacción de la casa | Lento (>4h post noticia de lesión) | Tu ventana de 16:30 captura noticias de última hora |

El edge: Si el pívot titular se reporta OUT a las 15:00 CST, la casa tarda horas en ajustar los rebounds del backup de "6.5" a "10.5". Tu sistema, que corre a las 16:30, ya incorpora la lesión. Tienes una ventana de ~90 minutos donde la línea del backup está subestimada.

**Tier 3 — Superestrellas Condicionales (3 jugadores)**

| Criterio | Umbral | Razón |
|---|---|---|
| Tipo de jugador | Estrella que es la ÚNICA opción ofensiva de su equipo | Alta dependencia táctica |
| Mercado objetivo | NO puntos. Solo assists, turnovers, o líneas secundarias | Puntos de estrellas = mercado eficiente |
| Trigger de apuesta | Solo cuando hay correlación táctica específica | ej: rival usa zona → más assists |
| Frecuencia de apuesta | Máximo 1-2 veces por semana | Ultra selectivo |

El edge: Las casas modelan los puntos de LeBron con precisión, pero sus assists contra una defensa en zona que fuerza pases extra no están tan bien calibrados. Solo disparas cuando tu modelo detecta el matchup táctico correcto.

### 3.3 Selección Dinámica, No Estática

El portafolio de 20 es una LISTA DE SEGUIMIENTO, no una lista fija de apuestas diarias. Cada día, el sistema:

1. Revisa qué jugadores del portafolio tienen juego hoy
2. Corre el modelo de Moneyline → genera Game Script
3. Proyecta minutos para cada jugador del portafolio según Game Script
4. Predice stats → compara vs. líneas → calcula EV
5. Solo recomienda los que pasan el filtro EV > umbral

En una noche típica, de 20 jugadores quizá 8-10 juegan, y de esos quizá 2-4 tienen EV positivo suficiente para apostar.

---

## 4. Mercados Disponibles y Priorización

Basado en lo que tu casa de apuestas ofrece:

### Fase 1 — Mercados Primarios (empezar aquí)

| Mercado | Market Key | Por qué primero |
|---|---|---|
| Total de Rebotes (O/U) | `player_rebounds` | Alta correlación con minutos, modelable |
| Total de Asistencias (O/U) | `player_assists` | Sensible a matchup táctico, menos eficiente |
| Total de Puntos + Asistencias + Rebotes | P+R+A combo | Casas suman promedios sin ajustar correlación |

### Fase 2 — Mercados Secundarios (agregar después)

| Mercado | Market Key | Por qué después |
|---|---|---|
| Rebotes y Asistencias (R+A) | combo | Menos líquido pero potencialmente más ineficiente |
| Puntos y Rebotes (P+R) | combo | Segundo combo más popular |
| Total de Robos (O/U) | `player_steals` | Alta varianza, difícil de modelar, pero potencialmente rentable |
| Total de Bloqueos (O/U) | `player_blocks` | Igual que steals: alta varianza, nichos |

### Fase 3 — Mercados Avanzados (si Fase 1 y 2 funcionan)

| Mercado | Por qué último |
|---|---|
| Puntos y Asistencias (P+A) | Requiere buen modelo de puntos, que evitamos en Fase 1 |
| Tiros de 3 Puntos Anotados | Extremadamente volátil, difícil de predecir |
| Primer Anotador de Puntos | Mercado de probabilidad baja, requiere modelo diferente |
| Tiros de Campo / Tiros Libres | Mercados de nicho, poco líquidos |

---

## 5. Features Específicas para el Motor de Proyección de Minutos

Este es el componente NUEVO que no existe en tu sistema actual y es el puente entre Moneyline y Props.

### Input
- Game Script predicho (output del modelo Moneyline: margen esperado)
- Roster del equipo (quién está disponible)
- Injury report del día (quién está OUT/QUESTIONABLE/PROBABLE)
- Historial de minutos del jugador en diferentes contextos

### Features del Modelo de Minutos

| Feature | Fuente | Descripción |
|---|---|---|
| minutes_avg_L10 | nba_api | Minutos promedio últimos 10 juegos |
| minutes_when_blowout_win | nba_api | Minutos promedio cuando su equipo gana por >15 |
| minutes_when_blowout_loss | nba_api | Minutos cuando su equipo pierde por >15 |
| minutes_when_close | nba_api | Minutos en partidos decididos por <8 puntos |
| predicted_margin | Modelo Moneyline | Margen esperado del partido |
| starter_OUT_same_position | Injury report | ¿Falta el titular de su posición? (boolean) |
| starter_OUT_minutes | nba_api | Minutos promedio del titular ausente (para redistribuir) |
| is_home | Schedule | Local o visitante |
| is_b2b | Schedule | Back-to-back |
| rest_days | Schedule | Días desde último juego |

### Output
- Minutos proyectados para el jugador en este juego específico

### Approach Recomendado

Dos opciones:

**Opción A: Reglas heurísticas (rápido, interpretable)**
```
minutos_proyectados = minutos_base_L10

IF predicted_margin > +15:
    minutos_proyectados *= 1.25  # Garbage time boost para bench
IF predicted_margin < -15:
    minutos_proyectados *= 1.15  # Equipo rinde la toalla, bench entra
IF starter_OUT_same_position:
    minutos_proyectados += starter_OUT_minutes * 0.6  # Hereda ~60% de los minutos
IF is_b2b:
    minutos_proyectados *= 0.95  # Leve reducción por fatiga
```

**Opción B: Modelo de regresión (más preciso, más complejo)**
- XGBoost con las features anteriores
- Target: minutos reales jugados
- Ventaja: captura interacciones no lineales
- Desventaja: más datos necesarios, más complejidad

**Recomendación: Empieza con Opción A (heurísticas) para el MVP. Si funciona conceptualmente y genera EV positivo en backtesting, migra a Opción B para optimizar.**

---

## 6. Flujo Operativo Diario (V2 Completa)

```
16:30 CST — Cloud Scheduler despierta el contenedor

FASE 1: Recolección (5 minutos)
├── Descargar schedule del día (qué equipos juegan)
├── Descargar injury report actualizado
├── Descargar cuotas de Moneyline (The-Odds-API)
└── Descargar cuotas de Player Props (The-Odds-API, por evento)

FASE 2: Game Script (2 minutos)
├── Correr modelo Moneyline para cada juego
├── Generar: P(Home Win), margen esperado, clasificación (paliza/cerrado/coin flip)
└── Filtrar: ¿qué jugadores del portafolio de 20 juegan hoy?

FASE 3: Proyección de Minutos (2 minutos)
├── Para cada jugador del portafolio que juega hoy:
│   ├── Calcular minutos proyectados según Game Script
│   ├── Ajustar por lesiones (¿titular de su posición está OUT?)
│   └── Ajustar por B2B, descanso, home/away
└── Output: minutos_proyectados por jugador

FASE 4: Predicción de Stats (3 minutos)
├── Para cada jugador con minutos proyectados:
│   ├── Calcular features (rendimiento reciente, matchup defensivo, pace)
│   ├── Correr modelo de regresión → E[REB], E[AST], E[PTS+REB+AST]
│   └── Calcular P(Over línea) usando distribución histórica del jugador
└── Output: stat esperada + probabilidad de over/under por mercado

FASE 5: Motor de Decisión (1 minuto)
├── Para cada predicción:
│   ├── Comparar P(Over) vs. probabilidad implícita de la cuota
│   ├── Calcular EV
│   ├── Si EV > umbral → calcular Kelly stake
│   └── Line shopping: ¿hay mejor cuota en otra casa?
└── Output: lista de apuestas recomendadas

FASE 6: Reporte (1 minuto)
├── Generar correo con:
│   ├── Sección 1: Game Scripts del día (contexto)
│   ├── Sección 2: Player Props Picks (la carne)
│   │   ├── Por cada pick: jugador, prop, línea, EV, Kelly, razón
│   │   └── Clasificado por Tier (Núcleo / Volatilidad / Señuelo)
│   └── Sección 3: Moneyline picks (referencia, baja prioridad)
└── Enviar correo

TOTAL: ~14 minutos de ejecución
Margen hasta tip-off: ~76 minutos para colocar apuestas
```

---

## 7. Timeline de Ejecución Revisado

### Sprint 0: Estabilización (Esta semana)
- [ ] Diagnosticar y arreglar el cron job que no disparó hoy
- [ ] Arreglar el bug de equipos duplicados en el reporte
- [ ] Confirmar que la V2 de Moneyline funciona y envía correos correctamente
- [ ] Verificar que The-Odds-API devuelve player props para NBA (probar endpoint manualmente)

### Sprint 1: Datos de Jugadores (Semanas 1-2)
- [ ] Pipeline de extracción de stats individuales con nba_api
- [ ] Features de rendimiento por jugador (rolling windows para REB, AST, PTS)
- [ ] Features de contexto (minutes_when_blowout, minutes_when_close, etc.)
- [ ] Features de matchup defensivo (DvP, def_rating oponente)
- [ ] Dataset: un registro por (jugador, juego) con features + stat real + minutos reales

### Sprint 2: Motor de Proyección de Minutos (Semana 3)
- [ ] Implementar heurísticas de proyección de minutos basadas en Game Script
- [ ] Integrar injury report como input (manual o scraping)
- [ ] Validar: ¿los minutos proyectados se acercan a los reales en datos históricos?
- [ ] Métrica: MAE de minutos proyectados vs reales < 4 minutos

### Sprint 3: Modelo de Props (Semanas 4-5)
- [ ] Ridge Regression baseline para REB y AST
- [ ] XGBoost regresión con minutos proyectados como feature clave
- [ ] Walk-forward validation (entrenar con temporada N, validar con N+1)
- [ ] Implementar conversión: stat predicha → P(Over/Under) → EV
- [ ] Backtesting con líneas históricas simuladas
- [ ] Métricas: MAE < baseline, ROI simulado > 0%

### Sprint 4: Integración y Paper Trading (Semanas 6-9)
- [ ] Conectar props de The-Odds-API al pipeline
- [ ] Integrar motor de EV + Kelly existente con formato de props
- [ ] Generar correo V2 con sección de Player Props
- [ ] Correr paper trading mínimo 4 semanas
- [ ] Registrar CLV (Closing Line Value) como métrica principal
- [ ] Criterio de paso: CLV positivo en >55% de picks + ROI paper > 0%

### Sprint 5: Producción (Semana 10+)
- [ ] Integrar en Cloud Run actual
- [ ] Banca dedicada para props (separada de Moneyline)
- [ ] Monitoreo de rendimiento semanal
- [ ] Selección inicial del portafolio de 20 jugadores basada en datos

---

## 8. Selección del Portafolio Inicial de 20 Jugadores

La selección final debe ser data-driven, pero como punto de partida para investigación, estos son los criterios de query:

```sql
-- Pseudoquery para identificar candidatos de Tier 1
SELECT player_name, team,
       AVG(minutes) as avg_min,
       STDDEV(minutes) as std_min,
       AVG(CASE WHEN margin > 15 THEN minutes END) as min_in_blowout,
       AVG(CASE WHEN ABS(margin) < 8 THEN minutes END) as min_in_close,
       (min_in_blowout - min_in_close) as minute_swing
FROM player_game_logs
WHERE season = '2024-25'
  AND is_starter = FALSE
  AND games_played > 30
  AND AVG(minutes) BETWEEN 18 AND 25
GROUP BY player_name, team
ORDER BY minute_swing DESC
LIMIT 15
```

Los jugadores con mayor "minute_swing" (diferencia entre minutos en blowouts vs. partidos cerrados) son tus mejores candidatos para Tier 1.

Para Tier 2, la query busca:
```sql
-- Candidatos de Tier 2: "Injury Heirs"
SELECT backup.player_name, backup.team, backup.position,
       starter.player_name as starter_ahead,
       starter.avg_minutes as starter_minutes,
       backup.avg_minutes as backup_avg_min,
       -- Buscar juegos donde el titular no jugó
       AVG(CASE WHEN starter_played = FALSE THEN backup.minutes END) as min_without_starter
FROM player_game_logs backup
JOIN starters starter ON backup.team = starter.team AND backup.position = starter.position
WHERE backup.avg_minutes BETWEEN 10 AND 20
  AND min_without_starter > backup_avg_min * 1.4  -- Al menos 40% más minutos sin titular
GROUP BY backup.player_name
ORDER BY (min_without_starter - backup_avg_min) DESC
LIMIT 10
```

---

## 9. Riesgos Actualizados

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Cron job inestable | Media | Crítico — sin ejecución, sin picks | Diagnosticar ahora. Agregar alertas de fallo al Telegram. |
| The-Odds-API no tiene props suficientes para role players | Media | Alto — sin líneas, no hay apuestas | Verificar esta semana qué jugadores tienen props disponibles |
| Modelo de minutos impreciso | Alta | Alto — minutos son EL predictor más importante | Empezar con heurísticas simples, validar MAE < 4 min |
| Proyección de minutos en blowout depende del modelo ML | Media | Medio — error en blowout prediction se propaga | Usar 1/4 Kelly para limitar exposure en predicciones de blowout |
| Insuficientes datos históricos de props para backtesting | Alta | Alto — no puedes validar ROI sin líneas históricas | Usar promedios de temporada como proxy de líneas |
| Temporada NBA termina en abril (playoffs cambian rotaciones) | Certeza | Medio — playoffs = rotaciones diferentes | Fase de paper trading cubre final de temporada regular. Ajustar modelo para playoffs como V3. |


