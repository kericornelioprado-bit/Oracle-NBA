# PRD: Oráculo NBA v2 - Advanced Ensemble & Automation

## Visión del Producto
Desarrollar un sistema de predicción de apuestas de valor para la NBA que utilice técnicas de Ensemble y Optimización Bayesiana para maximizar el ROI, evolucionado hacia un servicio 100% autónomo, resiliente y con entrega diaria de valor vía email.

## Historias de Usuario (Completadas)

### Sprint 1: Cimientos y Extracción
- **HU1: Setup del Entorno:** Configuración de `uv`, Docker y estructura modular.
- **HU2: Extracción NBA API:** Pipeline de ingesta histórica.
- **HU3: Infraestructura GCP:** Bucket GCS configurado vía Terraform.
- **HU4: EDA:** Identificación de features clave (Plus/Minus, Rolling Stats).

### Sprint 2: Inteligencia y Modelado
- **HU1: Multi-Modelo:** Pipeline para LR, XGBoost y LightGBM.
- **HU2: Validación Temporal:** Implementación de ventanas móviles [3, 5, 10, 20] sin data leakage.
- **HU3: ROI Sim:** Backtesting financiero con ROI del 24.29%.
- **HU4: Optuna & MLflow:** Optimización bayesiana y tracking de experimentos.

### Sprint 2.5: Advanced Stacking
- **HU1: Meta-Modelo:** Implementación de `StackingClassifier` (LR + XGBoost).

### Sprint 3: Automatización y Despliegue (Estado: FINALIZADO)
- **HU4: CI/CD Pipeline:** GitHub Actions implementado con Quality Gate (Tests obligatorios).
- **HU5: Email Delivery:** Reporte HTML diario con nombres de equipos reales y recomendaciones (HOME/AWAY/SKIP).
- **HU6: Persistencia Histórica:** Integración con BigQuery para auditoría de ROI a largo plazo.
- **HU7: Resiliencia de Red:** Parche de conectividad para NBA API con reintentos y backoff.

## Requisitos No Funcionales
- **Escalabilidad:** Despliegue en Cloud Run (Serverless).
- **Seguridad:** Gestión de secretos mediante GitHub Secrets.
- **Observabilidad:** Logs centralizados en GCP Logging.
- **Calidad:** Cobertura de tests del 94%.
