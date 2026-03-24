# Oráculo NBA 🏀

Sistema predictivo de **Value Betting** para la NBA basado en Stacking Ensembles. 100% automatizado en Google Cloud.

## Características Principales
- **🤖 Inteligencia Artificial:** Ensemble de Regresión Logística y XGBoost optimizado con Optuna.
- **📈 ROI Comprobado:** 24.29% de retorno en backtesting histórico.
- **🚀 Automatización:** Ejecución diaria programada en Cloud Run.
- **📧 Reportes:** Entrega de predicciones diarias en HTML directamente a tu Gmail.
- **📊 Persistencia:** Histórico de predicciones en BigQuery para auditoría.

## Estructura del Proyecto
- `src/`: Lógica modular (Ingesta, Modelos, Utils).
- `infra/`: Código de Terraform para GCP.
- `config/`: Configuraciones estáticas del modelo.
- `tests/`: Suite completa de pruebas unitarias e integración (94% cobertura).
- `.github/workflows/`: Pipeline de CI/CD.

## Control Local
Usa el script maestro para gestionar el servicio localmente:
```bash
./ctl.sh start    # Inicia el microservicio Flask
./ctl.sh status   # Verifica el estado
./ctl.sh stop     # Detiene el proceso
```

## Despliegue en GCP
1. Configura tus secretos en **GitHub Secrets** (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GCP_PROJECT_ID`, `GCP_SA_KEY`).
2. Realiza un `push` a la rama `main`.
3. GitHub Actions validará el código y desplegará automáticamente en Cloud Run.

---
*Desarrollado con enfoque en Calidad, Resiliencia y ROI.*
