# PRD: Oráculo NBA v2 - Advanced Ensemble Edition

## Visión del Producto
Desarrollar un sistema de predicción de apuestas de valor para la NBA que utilice técnicas de Ensemble y Optimización Bayesiana para maximizar el ROI y minimizar la varianza de las predicciones.

## Historias de Usuario (Fase de Experimentación Avanzada)

### Historia 1: Optimización de Hiperparámetros (Tuning Inteligente)
**Como Data Scientist,** quiero utilizar **Optuna** para encontrar la mejor combinación de parámetros para el modelo XGBoost, con el fin de superar el 21.8% de ROI actual.
*   **Criterio de Aceptación:** Superar el Accuracy del modelo base en al menos un 1% o reducir el LogLoss en un conjunto de validación.

### Historia 2: Ensamble por Stacking (Voto de Expertos)
**Como Data Scientist,** quiero implementar un meta-modelo que combine las predicciones de un modelo lineal (Logistic Regression) y un modelo de árboles (LightGBM).
*   **Criterio de Aceptación:** El modelo final de Stacking debe tener un ROI superior a la media de los modelos individuales.

### Historia 3: Ingeniería de Ventanas Dinámicas (Contexto Histórico)
**Como Data Scientist,** quiero añadir ventanas de 3 y 20 partidos para capturar rachas cortas y consistencia a largo plazo.
*   **Criterio de Aceptación:** El análisis de importancia de características debe mostrar que las nuevas ventanas aportan valor predictivo (SHAP values).

## Requisitos No Funcionales
*   **MLflow:** Cada experimento de tuning debe quedar registrado.
*   **Reproducibilidad:** Cada corrida de Optuna debe tener una semilla fija.
