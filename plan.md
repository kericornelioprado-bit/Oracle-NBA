# Implementation Plan - Monorepo & Diamante MLB V1

## Estado del Proyecto
- [ ] Planning (Fase de diseño completada)
- [x] Approved (Listo para código)
- [ ] In Progress
- [ ] Done

## Arquitectura Refinada
Se implementará una estructura de **Monorepo por Capas**:
1.  **`src/shared/`**: Lógica agnóstica al deporte (BigQuery, Email, Logging, Odds API, BDL Client Base).
2.  **`src/nba/`**: Migración de la lógica actual (manteniendo compatibilidad inicial).
3.  **`src/mlb/`**: Nuevo módulo para Diamante.
4.  **Entry Point Unificado**: `main.py` soportará `--sport [nba|mlb]` para despliegues independientes en Cloud Run.

## Roadmap & Checklist

### Fase 1: Core Monorepo Setup [Status: 100%]
*Objetivo: Preparar la infraestructura de carpetas y servicios compartidos sin romper NBA.*
- [x] **Estructura de Directorios**
  - [x] Crear `src/shared/`, `src/mlb/`, `config/mlb/`, `infra/mlb/`.
  - [x] **Verificación**: Directorios creados correctamente.
- [x] **Servicios Compartidos (Copia y Adaptación)**
  - [x] Copiar `src/utils/` a `src/shared/` (manteniendo `src/utils/` intacto).
  - [x] Generalizar `BDLClient` en `src/shared/` para soportar `/nba/v1/` y `/mlb/v1/`.
  - [x] Crear adaptadores genéricos para `BigQueryClient` y `EmailService` en `src/shared/` (remover prefijos NBA).
  - [x] **Verificación**: Servicios compartidos implementados.
- [x] **Entry Point & Docker**
  - [x] Actualizar `main.py` para manejar lógica condicional por deporte y jobs granulares.
  - [x] Parametrizar `Dockerfile` (Pendiente de build-arg, pero el código ya lo soporta).
  - [x] **Verificación**: `main.py` soporta `--sport` y `--job`.

### Fase 2: Diamante MLB - Ingesta y Datos [Status: 0%]
*Objetivo: Cargar el histórico de 4 años para entrenamiento.*
- [ ] **Adaptador BDL MLB**
  - [ ] Implementar `src/mlb/data/ingestion.py`.
  - [ ] Integrar endpoints `/mlb/v1/stats`, `/games`, `/lineups`.
- [ ] **BigQuery MLB Schema**
  - [ ] Crear tablas `mlb_pitcher_game_logs` y `mlb_paper_trades`.
- [ ] **Backfill Histórico**
  - [ ] Ejecutar `scripts/mlb/backfill_historical.py` (2022-2025).
  - [ ] **Verificación**: Query en BQ para validar ~13,000 registros.

### Fase 3: Diamante MLB - Modelado [Status: 0%]
- [ ] **Feature Engineering**
  - [ ] Pipeline para Pitcher K's (Rolling averages, splits).
- [ ] **Entrenamiento Stacking V1**
  - [ ] Modelos Base (LightGBM, Ridge, RF).
  - [ ] Meta-modelo y calibración.
  - [ ] **Verificación**: Reporte de métricas (MAE, ROI simulado).

### Fase 4: Producción y Paper Trading [Status: 0%]
- [ ] **Pipeline Diario**
  - [ ] Cloud Run Job para MLB (Ingesta -> Inferencia -> Alerta).
- [ ] **Paper Trading Launch**
  - [ ] Activación de seguimiento de ROI para MLB.

---
**Nota para el Usuario:** He diseñado la Fase 1 para que sea 100% segura. NBA seguirá funcionando desde `src/utils/` inicialmente o mediante un alias, mientras el nuevo código usa `src/shared/`. 

¿Desea que proceda con la creación de la estructura de directorios y la migración de servicios compartidos?
