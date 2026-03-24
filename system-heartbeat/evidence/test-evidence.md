# TEST EVIDENCE REPORT — Oráculo NBA
> Última actualización: 2026-03-23 | Cobertura total: **94%** | Tests: **79 passing, 0 failed**

---

## RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| **Total de tests** | 79 |
| **Pasando** | 79 ✅ |
| **Fallando** | 0 |
| **Cobertura global** | **94%** |
| **Archivos de test** | 11 |
| **Comando** | `uv run python -m pytest tests/ --cov=src --cov=main` |

### Cobertura por Módulo

| Módulo | Stmts | Miss | Cobertura |
|--------|-------|------|-----------|
| `main.py` | 34 | 2 | **94%** |
| `src/utils/email_service.py` | 42 | 0 | **100%** |
| `src/utils/report_generator.py` | 13 | 0 | **100%** |
| `src/utils/logger.py` | 12 | 0 | **100%** |
| `src/utils/bigquery_client.py` | 31 | 2 | **94%** |
| `src/data/eda_report.py` | 36 | 1 | **97%** |
| `src/data/feature_engineering.py` | 52 | 2 | **96%** |
| `src/models/evaluator.py` | 46 | 2 | **96%** |
| `src/models/stacking_trainer.py` | 51 | 2 | **96%** |
| `src/models/tuner.py` | 49 | 2 | **96%** |
| `src/models/trainer.py` | 64 | 4 | **94%** |
| `src/models/inference.py` | 101 | 13 | **87%** |
| `src/data/ingestion.py` | 61 | 7 | **89%** |
| **TOTAL** | **592** | **37** | **94%** |

---

## SPRINTS HISTÓRICOS

### [Sprint 1] Setup de Proyecto (HU1)
- **Scope**: Estructura de carpetas y archivos base.
- **Validation**:
  - Estructura de carpetas creada según plan.md: ✅
  - Git inicializado: ✅
  - `.gitignore` configurado para Python y Terraform: ✅
  - Dockerfile base listo: ✅
  - Requirements iniciales definidos: ✅

### [Sprint 1] Ingestión de Datos (HU2)
- **Scope**: Extracción desde nba_api y guardado en Parquet.
- **Command**: `env PYTHONPATH=. uv run python3 src/data/ingestion.py`
- **Output**:
```text
2026-03-22 21:48:55,958 - oracle-nba - INFO - Datos guardados exitosamente en data/raw/nba_games_raw.parquet
```
- **Validation**:
  - Extracción de temporadas 2021-22 a 2023-24: ✅
  - Almacenamiento en Parquet (eficiencia): ✅

### [Sprint 1] Infraestructura (HU3)
- **Scope**: Creación de archivos Terraform e integración en Python.
- **Validation**:
  - Definición de Bucket GCS con versionado: ✅
  - Script `ingestion.py` soporta `upload_to_gcs`: ✅
  - Uso de `python-dotenv` para manejar el nombre del bucket: ✅

### [Sprint 1] Análisis Exploratorio (HU4)
- **Scope**: Análisis de correlación y calidad de datos.
- **Output (Correlación)**:
  - PLUS_MINUS: 0.80 | FG_PCT: 0.46 | DREB: 0.37 | TOV: -0.11
- **Validation**:
  - Limpieza de datos (WL → Win/Loss): ✅
  - Reporte generado: `data/processed/eda_report.txt` ✅

### [Sprint 2] Entrenamiento de Modelos (HU1-2)
- **Results**: Logistic Regression 61.76% | XGBoost 61.47%
- **Validation**: Split temporal ✅ | Umbral 55% superado ✅ | Modelo guardado ✅

### [Sprint 2] Evaluación Financiera (HU3)
- **Results**: Win Rate 62.93% | Profit $12,964 | ROI 20.19%
- **Validation**: Estrategia unidad fija ✅ | Umbral de confianza ✅

### [Sprint 2.5] Advanced Tuning — Optuna (HU1)
- **Results**: Best LogLoss 0.6400 | ROI 22.22% | Win Rate 63.99%
- **Validation**: MLflow Tuning ✅ | `models/nba_best_model_tuned.joblib` ✅

### [Sprint 2.5] Stacking Ensemble (HU2)
- **Results**: Accuracy 62.89% | ROI 21.27% | Win Rate 63.49%
- **Validation**: LR + XGBoost Tuned ✅ | `models/nba_best_model_stacking.joblib` ✅

### [Sprint 2.5] Ventanas Dinámicas [3,5,10,20] (HU3)
- **Results**: Accuracy 63.91% | ROI 24.29% | Win Rate 65.07%
- **Validation**: Ventanas integradas ✅ | Tracking MLflow ✅

### [Sprint 3] Inferencia Diaria (HU1)
- **Command**: `env PYTHONPATH=. uv run python3 src/models/inference.py`
- **Output**:
```text
=== CARTELERA DE APUESTAS DEL DÍA (ORÁCULO NBA) ===
      HOME_ID     AWAY_ID  PROB_HOME_WIN RECOMMENDATION
0  1610612743  1610612757       0.537534           HOME
```
- **Validation**: Scoreboard en tiempo real ✅ | Imputación nulos ✅ | Predicciones Stacking ✅

---

## SUITE COMPLETA DE TESTS AUTOMATIZADOS (Sprint 3 — Cobertura 94%)

> Comando: `uv run python -m pytest tests/ --cov=src --cov=main -q`

---

### `tests/test_email_service.py` — NBAEmailService (2 tests)

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_send_email_success` | Mock SMTP completo: verifica starttls, login y sendmail con credenciales correctas | ✅ |
| `test_send_email_no_creds` | Retorna False cuando GMAIL_USER o GMAIL_APP_PASSWORD están vacíos | ✅ |

---

### `tests/test_feature_engineering.py` — NBAFeatureEngineer básico (2 tests)

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_rolling_averages` | Valida que shift(1) + rolling(3) produce NaN en primeras filas y promedio correcto en fila 4 | ✅ |
| `test_rest_days_calculation` | Verifica diferencia de días entre partidos y valor de relleno ≥7 para el primer registro | ✅ |

---

### `tests/test_model_training.py` — NBAModelTrainer + NBAHyperTuner (2 tests)

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_trainer_split_logic` | Split temporal 80/20 produce 4 train + 1 test sobre 5 registros | ✅ |
| `test_tuner_initialization` | Tuner inicializa con data_path correcto y trainer interno sincronizado | ✅ |

---

### `tests/test_ingestion_evaluator.py` — NBADataIngestor + NBAProfitSim básico (3 tests)

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_ingestor_save_parquet` | Guarda DataFrame en Parquet y verifica existencia y contenido del archivo | ✅ |
| `test_profit_calculator_math` | Valida matemáticamente ganancia (+100) y pérdida (-100) con odds 2.0 | ✅ |
| `test_ingestor_api_error_handling` | Retorna None sin propagar excepción cuando la NBA API falla con timeout | ✅ |

---

### `tests/test_inference_pipeline.py` — NBAOracleInference básico (2 tests)

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_model_loading` | Verifica que el modelo de producción existe en disco y expone `predict_proba` | ✅ |
| `test_inference_logic_robustness` | Lógica de cascada NaN: ROLL_PTS_20 hereda 110.0 desde ROLL_PTS_3 sin quedar nulo | ✅ |

---

### `tests/test_bigquery_client.py` — NBABigQueryClient (7 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_init_without_gcp_project_id` | Sin GCP_PROJECT_ID el cliente interno queda en None | ✅ |
| `test_insert_predictions_no_client` | Retorna False y loguea warning cuando client es None | ✅ |
| `test_insert_predictions_success` | Retorna True e invoca insert_rows_json cuando BQ no reporta errores | ✅ |
| `test_insert_predictions_bq_errors` | Retorna False cuando BQ retorna lista de errores no vacía | ✅ |
| `test_insert_predictions_exception` | Retorna False ante excepción inesperada de BQ (ej. conexión caída) | ✅ |
| `test_insert_predictions_row_structure` | Verifica que cada fila insertada contiene los 9 campos del schema | ✅ |
| `test_insert_predictions_custom_version` | model_version y experiment_id personalizados se propagan correctamente a BQ | ✅ |

---

### `tests/test_report_generator.py` — NBAReportGenerator (8 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_generate_html_none_input` | Retorna mensaje "No hay partidos" cuando se pasa None | ✅ |
| `test_generate_html_empty_dataframe` | Retorna mensaje "No hay partidos" con DataFrame vacío | ✅ |
| `test_generate_html_valid_data` | Genera `<html>` con `<table>` y probabilidades formateadas como porcentaje | ✅ |
| `test_generate_html_contains_recommendations` | HOME y AWAY aparecen en el HTML generado | ✅ |
| `test_generate_html_recommendation_css_classes` | Clases CSS `recommendation-HOME` y `recommendation-AWAY` presentes | ✅ |
| `test_generate_html_skip_recommendation` | Clase `recommendation-SKIP` generada para partidos sin recomendación clara | ✅ |
| `test_generate_html_contains_team_ids` | Los IDs de equipos son visibles en la tabla HTML | ✅ |
| `test_generate_html_single_game` | HTML válido con un solo partido y probabilidad correctamente formateada | ✅ |

---

### `tests/test_eda_report.py` — run_eda() (5 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_run_eda_file_not_found` | Ruta inexistente retorna None sin lanzar excepción | ✅ |
| `test_run_eda_generates_report` | Con parquet válido crea el archivo `eda_report.txt` en disco | ✅ |
| `test_run_eda_computes_correlation` | El reporte escrito contiene secciones "REPORTE EDA" y "Correlación" | ✅ |
| `test_run_eda_no_nulls_report` | Sin nulos escribe "No se encontraron valores nulos" en el reporte | ✅ |
| `test_run_eda_with_nulls_report` | Con un campo nulo el reporte incluye la sección de calidad de datos | ✅ |

---

### `tests/test_evaluator_extended.py` — NBAProfitSim completo (6 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_profit_sim_init_mocked` | `__init__` carga modelo y DataFrame correctamente con mocks de joblib y pandas | ✅ |
| `test_run_simulation_returns_dataframe` | `run_simulation` retorna DataFrame con columnas PROFIT, CUM_PROFIT, BET_PLACED, PRED_PROBA | ✅ |
| `test_run_simulation_bet_placed_logic` | BET_PLACED == 0 para probabilidades dentro del rango neutro [0.476, 0.524] | ✅ |
| `test_run_simulation_profit_calculation_home_win` | Ganancia = unit × (odds-1) = 91.0 cuando local gana con prob > 0.524 | ✅ |
| `test_run_simulation_profit_calculation_away_win` | Ganancia = 91.0 cuando visitante gana con prob < 0.476 | ✅ |
| `test_run_simulation_roi_zero_bets` | ROI = 0 y PROFIT.sum() = 0 cuando todas las probabilidades están en zona SKIP | ✅ |

---

### `tests/test_feature_engineering_extended.py` — NBAFeatureEngineer completo (7 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_structure_for_modeling_shape` | 2 partidos (4 filas raw) → 2 filas estructuradas (1 fila por partido) | ✅ |
| `test_structure_for_modeling_columns` | Dataset estructurado contiene columnas `HOME_*`, `AWAY_*` y `TARGET` | ✅ |
| `test_structure_for_modeling_target_encoding` | TARGET = 1 cuando local ganó (WL='W'), TARGET = 0 cuando perdió | ✅ |
| `test_load_data_mocked` | `load_data` lee parquet y convierte GAME_DATE a dtype datetime64 | ✅ |
| `test_run_pipeline_full` | Pipeline completo `run()` genera parquet de salida con columna TARGET | ✅ |
| `test_rest_days_clipped_at_10` | Diferencia de 19 días entre partidos queda capped en 10 (upper clip) | ✅ |
| `test_rolling_features_no_data_leakage` | shift(1) garantiza que la fila i no incluye sus propios datos en el rolling | ✅ |

---

### `tests/test_ingestion_extended.py` — NBADataIngestor completo (8 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_upload_to_gcs_skipped_when_no_bucket` | Sin GCS_BUCKET_NAME no se instancia storage.Client | ✅ |
| `test_upload_to_gcs_success` | Con bucket configurado llama a `blob.upload_from_filename` con la ruta correcta | ✅ |
| `test_upload_to_gcs_error_handling` | Excepción de GCS es capturada sin propagarse al llamador | ✅ |
| `test_run_ingestion_with_successful_seasons` | Combina datos de 2 temporadas y llama a `save_to_parquet` exactamente una vez | ✅ |
| `test_run_ingestion_all_seasons_fail` | Retorna None cuando todas las temporadas fallan en fetch | ✅ |
| `test_run_ingestion_partial_failure` | Retorna datos parciales cuando solo una temporada falla | ✅ |
| `test_run_ingestion_default_seasons` | Sin argumentos usa temporadas ['2021-22', '2022-23', '2023-24'] por defecto | ✅ |
| `test_save_to_parquet_calls_upload` | `save_to_parquet` invoca `upload_to_gcs` tras guardar localmente | ✅ |

---

### `tests/test_inference_extended.py` — NBAOracleInference completo (9 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_oracle_init_file_not_found` | Lanza `FileNotFoundError` si el modelo no existe en disco | ✅ |
| `test_oracle_init_loads_model` | Carga modelo con joblib y crea instancia de NBAFeatureEngineer | ✅ |
| `test_get_today_games_returns_dataframe` | Retorna DataFrame con GAME_ID, HOME_TEAM_ID, VISITOR_TEAM_ID | ✅ |
| `test_get_today_games_no_games` | Retorna None cuando el scoreboard viene vacío | ✅ |
| `test_fetch_recent_history` | Concatena y deduplica historial por GAME_ID para múltiples equipos | ✅ |
| `test_predict_today_no_games` | Retorna None temprano cuando get_today_games() retorna None | ✅ |
| `test_predict_today_with_games` | Retorna DataFrame con RECOMMENDATION y PROB_HOME_WIN para partidos del día | ✅ |
| `test_predict_today_recommendation_home` | prob > 0.524 genera recomendación 'HOME' | ✅ |
| `test_predict_today_recommendation_away` | prob < 0.476 genera recomendación 'AWAY' | ✅ |

---

### `tests/test_stacking_trainer.py` — NBAStackingTrainer (4 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_stacking_trainer_init` | Inicializa con data_path y best_xgb_params hardcodeados de Optuna | ✅ |
| `test_build_stacking_model` | Retorna StackingClassifier con estimadores 'lr' y 'xgb' | ✅ |
| `test_train_and_evaluate_mocked` | Llama a model.fit, loguea métricas en MLflow y retorna el modelo entrenado | ✅ |
| `test_stacking_trainer_uses_correct_data_path` | NBAModelTrainer interno usa la misma ruta de datos que el stacker | ✅ |

---

### `tests/test_trainer_extended.py` — NBAModelTrainer + NBAHyperTuner completo (6 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_prepare_data_feature_columns` | Identifica columnas ROLL_* y DAYS_REST; excluye TARGET y GAME_DATE | ✅ |
| `test_prepare_data_temporal_order` | Split 80/20 sobre 30 registros produce 24 train + 6 test en orden cronológico | ✅ |
| `test_save_temp_model` | Invoca joblib.dump exactamente una vez para persistir el modelo temporal | ✅ |
| `test_train_and_evaluate_mocked` | Ejecuta mlflow.start_run exactamente 2 veces (uno por modelo: LR y XGBoost) | ✅ |
| `test_tuner_objective_returns_float` | `objective(trial)` retorna float ≥ 0 (log_loss sobre datos reales) | ✅ |
| `test_run_tuning_mocked` | `run_tuning` ejecuta `study.optimize`, loguea parámetros en MLflow y retorna best_params | ✅ |

---

### `tests/test_flask_app.py` — Flask endpoint + NBAEmailService avanzado (8 tests) 🆕

| Test | Descripción | Estado |
|------|-------------|--------|
| `test_run_oracle_success` | GET / retorna 200 + status "success", invoca BQ y email con predicciones | ✅ |
| `test_run_oracle_no_predictions` | predict_today() retorna None → 200 + status "warning" | ✅ |
| `test_run_oracle_empty_predictions` | predict_today() retorna DataFrame vacío → 200 + status "warning" | ✅ |
| `test_run_oracle_exception` | Excepción interna → 500 + status "error" + send_error_alert() invocado | ✅ |
| `test_run_oracle_post_method` | Endpoint acepta método POST además de GET | ✅ |
| `test_email_service_send_prediction_report` | Subject contiene "NBA" e is_html=True al llamar a send_email | ✅ |
| `test_email_service_send_error_alert` | Subject contiene "ALERT"/"Fallo" e is_html=False (texto plano) | ✅ |
| `test_email_service_smtp_exception` | Retorna False cuando smtplib.SMTP lanza excepción de conexión | ✅ |

---

## EVOLUCIÓN DE COBERTURA

| Sprint | Tests | Cobertura | Incremento |
|--------|-------|-----------|------------|
| Sprint 1 (estructura) | 0 | 0% | — |
| Sprint 2 (modelos base) | 5 | 11% | +11% |
| Sprint 2.5 (tuning + stacking) | 11 | 32% | +21% |
| Sprint 3.1 (suite unitaria inicial) | 11 | 33% | +1% |
| **Sprint 3.2 (cobertura 94%)** | **79** | **94%** | **+61%** |

---

## ARCHIVOS DE TEST

| Archivo | Tests | Módulo Cubierto | Nuevo |
|---------|-------|----------------|-------|
| `test_email_service.py` | 2 | `utils/email_service.py` | — |
| `test_feature_engineering.py` | 2 | `data/feature_engineering.py` | — |
| `test_model_training.py` | 2 | `models/trainer.py`, `models/tuner.py` | — |
| `test_ingestion_evaluator.py` | 3 | `data/ingestion.py`, `models/evaluator.py` | — |
| `test_inference_pipeline.py` | 2 | `models/inference.py` | — |
| `test_bigquery_client.py` | 7 | `utils/bigquery_client.py` | 🆕 |
| `test_report_generator.py` | 8 | `utils/report_generator.py` | 🆕 |
| `test_eda_report.py` | 5 | `data/eda_report.py` | 🆕 |
| `test_evaluator_extended.py` | 6 | `models/evaluator.py` | 🆕 |
| `test_feature_engineering_extended.py` | 7 | `data/feature_engineering.py` | 🆕 |
| `test_ingestion_extended.py` | 8 | `data/ingestion.py` | 🆕 |
| `test_inference_extended.py` | 9 | `models/inference.py` | 🆕 |
| `test_stacking_trainer.py` | 4 | `models/stacking_trainer.py` | 🆕 |
| `test_trainer_extended.py` | 6 | `models/trainer.py`, `models/tuner.py` | 🆕 |
| `test_flask_app.py` | 8 | `main.py`, `utils/email_service.py` | 🆕 |
| **TOTAL** | **79** | — | — |
