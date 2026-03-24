# Architecture: Oráculo NBA v2 - Automated Prediction System

## 1. Diseño de Componentes (Microservicio)
El sistema opera como un microservicio ligero basado en Flask, diseñado para ejecutarse de forma efímera en Google Cloud Run.

### Módulos Python:
1.  **`main.py`**: Servidor Flask que expone un endpoint `/` (GET/POST). Actúa como el orquestador principal del flujo diario.
2.  **`src/models/inference.py`**: 
    - Lógica de predicción con Stacking Ensemble.
    - Mitigación de bloqueos de API: Reintentos con backoff y cabeceras de navegador reales.
    - Carga de features vía `config/model_features.json` para evitar dependencias locales.
3.  **`src/utils/bigquery_client.py`**: Cliente para la persistencia de predicciones y metadatos en BigQuery.
4.  **`src/utils/report_generator.py`**: Generador de HTML dinámico con mapeo de IDs a nombres oficiales de la NBA.
5.  **`src/utils/email_service.py`**: Envío de reportes y alertas vía Gmail SMTP.

## 2. Esquema de Datos (BigQuery)
**Dataset:** `oracle_nba_ds` | **Tabla:** `predictions`
Persistencia histórica para análisis de ROI y comparación de versiones de modelos.

## 3. Infraestructura GCP (Golden Path)
- **Cloud Run**: Ejecución serverless (escala a cero).
- **Cloud Scheduler**: Disparador cron (`0 14 * * *` UTC).
- **Artifact Registry**: Repositorio de imágenes Docker basado en `python:3.11-slim`.
- **Secret Manager/ENV**: Configuración de credenciales de Gmail y GCP.

## 4. Pipeline de CI/CD (GitHub Actions)
- **Quality Gate**: Ejecución de `pytest` en cada push a `main`. Cobertura actual: 94%.
- **Auto-Deploy**: Construcción de imagen y despliegue automático a Cloud Run tras pasar los tests.

## 5. Estrategia de Resiliencia
- **NBA API Retries:** Manejo de fallos de red mediante pausas de 1.5s y reintentos automáticos.
- **Global Error Handling:** Captura de excepciones en `main.py` con envío automático de alerta técnica vía email.
