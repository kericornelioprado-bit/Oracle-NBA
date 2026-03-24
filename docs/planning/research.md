# Research Report: Oráculo NBA v2

## 1. Arquitectura Actual (Descubierta)
El proyecto es una aplicación de ciencia de datos modular en Python para la predicción de partidos de la NBA y apuestas de valor.

### Módulos Principales:
- **`src/data/ingestion.py`**: Utiliza `nba_api` para extraer datos históricos de temporadas de la NBA y los almacena en formato Parquet (`data/raw/`). Soporta carga a Google Cloud Storage.
- **`src/data/feature_engineering.py`**: Calcula medias móviles (`ROLL_`) para ventanas de [3, 5, 10, 20] partidos y días de descanso (`DAYS_REST`). Transforma el dataset de 2 filas por juego a 1 fila con prefijos `HOME_` y `AWAY_`.
- **`src/models/trainer.py`**: Entrenamiento de modelos base (XGBoost, etc.) con validación temporal.
- **`src/models/tuner.py`**: Optimización de hiperparámetros usando Optuna para maximizar el ROI.
- **`src/models/stacking_trainer.py`**: Implementa un `StackingClassifier` combinando Regresión Logística y XGBoost (con meta-modelo LR). Registra métricas (Accuracy, ROI, Win Rate) en MLflow.
- **`src/models/inference.py`**: Script para predicciones diarias. Obtiene la cartelera de hoy, calcula features dinámicamente y emite recomendaciones (`HOME`, `AWAY`, `SKIP`) basadas en umbrales de probabilidad.

## 2. Flujo de Datos y Stack Tecnológico
- **Lenguaje**: Python 3.11+.
- **Gestión de Entorno**: `uv` (mencionado en el plan), `requirements.txt`.
- **Persistencia**: Archivos Parquet locales y GCS.
- **Modelado**: Scikit-learn, XGBoost, LightGBM, Optuna.
- **MLOps**: MLflow (tracking local en `mlflow.db` y `mlruns/`).
- **Infraestructura**: Terraform (solo GCS configurado en `infra/main.tf`).
- **Contenedores**: Docker (Base Fedora).

## 3. Puntos Ciegos y Deuda Técnica
- **Infraestructura Incompleta**: El plan menciona Cloud Run y Cloud Scheduler, pero no hay código de Terraform ni scripts de despliegue para estos componentes.
- **Lógica de Recomendación Hardcodeada**: Los umbrales de probabilidad (`0.524` y `0.476`) en `inference.py` están fijos y no se derivan de un análisis dinámico de cuotas.
- **Ausencia de CI/CD**: No se han encontrado workflows de automatización para tests o despliegue.
- **Gestión de Secretos**: No hay una estrategia clara para el manejo de credenciales de GCP en producción (fuera de `.env.example`).
- **Validación de Datos en Inferencia**: El script de inferencia tiene correcciones "ad-hoc" para nulos en las medias móviles (imputación manual por cascada).
- **Consistencia de Features**: La inferencia re-implementa parte de la lógica de ingeniería de características en lugar de importar una función puramente compartida, lo que podría generar sesgo de entrenamiento-servicio (training-serving skew).
