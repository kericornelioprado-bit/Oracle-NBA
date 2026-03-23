# PRD: Oráculo NBA v2 - Advanced Ensemble & Automation

## Visión del Producto
Desarrollar un sistema de predicción de apuestas de valor para la NBA que utilice técnicas de Ensemble y Optimización Bayesiana para maximizar el ROI, ahora evolucionando hacia un servicio automatizado, confiable y con entrega directa de valor al usuario mediante reportes diarios.

## Historias de Usuario (Fase de Experimentación Avanzada - Completada)

### Historia 1: Optimización de Hiperparámetros (Tuning Inteligente)
*   **Estado:** Completado. ROI incrementado al 22.2% con Optuna.

### Historia 2: Ensamble por Stacking (Voto de Expertos)
*   **Estado:** Completado. Meta-modelo LR + XGBoost implementado (Accuracy 62.9%).

### Historia 3: Ingeniería de Ventanas Dinámicas (Contexto Histórico)
*   **Estado:** Completado. ROI Final 24.29% con ventanas [3, 5, 10, 20].

## Historias de Usuario (Fase de Automatización y Despliegue - En Progreso)

### Historia 4: Pipeline de CI/CD (Guardián de Calidad)
**Como Desarrollador,** quiero un flujo de GitHub Actions que valide el código antes de cualquier despliegue.
*   **Criterios de Aceptación:**
    - El workflow se dispara con cada `push` a la rama `main`.
    - Ejecución obligatoria de `pytest`. Si un solo test falla, el despliegue se cancela. **La calidad no es negociable.**
    - Construcción automática de la imagen Docker y subida a Google Artifact Registry.
    - Despliegue automático a Google Cloud Run solo si los tests pasan al 100%.

### Historia 5: Automatización de Predicciones Diarias (Email Delivery)
**Como Usuario,** quiero recibir las predicciones en mi Gmail personal cada día sin intervención manual.
*   **Criterios de Aceptación:**
    - Configuración de Cloud Scheduler para ejecutar el contenedor diariamente.
    - El sistema debe extraer la cartelera del día, generar predicciones y enviar un reporte formateado al correo Gmail personal.
    - Uso de Gmail via SMTP con App Passwords para el envío.

### Historia 6: Notificaciones de Fallo y Resiliencia
**Como Usuario,** quiero ser notificado inmediatamente vía correo si el sistema falla (ej. timeout de la API).
*   **Criterios de Aceptación:**
    - Implementación de manejo de errores global en el punto de entrada de producción.
    - Envío de alerta de error detallada al correo personal en caso de fallo crítico.

## Requisitos No Funcionales
*   **MLflow:** Cada experimento de tuning debe quedar registrado (Local/GCS).
*   **Seguridad de Credenciales:** Las llaves de GCP y contraseñas de Gmail deben residir en GitHub Secrets y Secret Manager.
*   **Reproducibilidad:** Cada corrida de Optuna debe tener una semilla fija.
*   **Observabilidad:** Logs centralizados en Google Cloud Logging.
