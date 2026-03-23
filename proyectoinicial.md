🏀 Proyecto: Oráculo NBA - Modelo Predictivo para Apuestas de Valor (Value Betting)
1. Resumen Ejecutivo y Objetivo
El objetivo de este proyecto es diseñar, entrenar y desplegar un modelo de machine learning capaz de predecir el resultado directo (ganador/perdedor) de los partidos de la NBA. A diferencia de un modelo estadístico tradicional, el éxito no se medirá únicamente por la precisión (Accuracy), sino por su capacidad para identificar ineficiencias en el mercado de apuestas deportivas (Expected Value positivo) y generar un Retorno de Inversión (ROI) rentable a largo plazo, superando el margen de las casas de apuestas (vig).
2. Alcance del Proyecto (Scope)
Universo: Baloncesto (NBA).
Mercado de Predicción: Moneyline (Ganador del partido, sin hándicaps).
Métrica de Éxito Comercial: Alcanzar un win rate de entre 55% y 60% en backtesting continuo, validado posteriormente con un mes de paper trading (simulación en tiempo real sin riesgo de capital).
Métrica de Optimización: Valor Esperado (EV) basado en cuotas de cierre.
3. Estrategia de Datos
La calidad del modelo dependerá enteramente de la granularidad y limpieza de los datos. Se dividirá la ingesta en dos dominios:
Estadísticas de la NBA: Extracción de datos históricos y en tiempo real utilizando la librería de Python nba_api (métricas tradicionales, avanzadas, play-by-play, días de descanso, etc.).
Cuotas Financieras (Odds):
Para Entrenamiento/Backtesting: Datasets históricos estáticos (archivos CSV/Kaggle) con cuotas de cierre de las últimas 5-10 temporadas.
Para Producción/Paper Trading: Integración con The-Odds-API para comparar las predicciones del modelo contra las líneas del mercado actual.
4. Arquitectura y Stack Tecnológico
Todo el ciclo de vida del proyecto está diseñado con estándares de ingeniería de software y MLOps, asegurando reproducibilidad y automatización total.
Control de Versiones: GitHub.
Entorno Local de Desarrollo: Estandarización del código a través de Docker. Los contenedores se ejecutarán localmente sobre Fedora, configurados con los drivers de CUDA para aprovechar la aceleración de la tarjeta gráfica NVIDIA durante las fases de entrenamiento pesado e iteración de hiperparámetros.
Lenguaje y ML: Python (Pandas, Scikit-Learn, XGBoost/LightGBM, PyTorch/TensorFlow para experimentación).
Tracking de Experimentos: MLflow integrado para registrar automáticamente cada corrida, métrica y versión del modelo.
Infraestructura en la Nube (GCP):
IaC: Terraform para aprovisionar y gestionar toda la infraestructura como código.
Almacenamiento (Data Lake): Google Cloud Storage para almacenar los datos crudos y procesados en formato Parquet.
Orquestación y Cómputo: Cloud Run (contenedores serverless para inferencia) disparados diariamente por Cloud Scheduler.
5. Plan de Ejecución (Sprints)
Sprint 1: Data Ingestion & EDA (Cimientos)
Configuración del repositorio en GitHub y estructuración del entorno Docker.
Desarrollo de scripts de extracción con nba_api.
Despliegue de la infraestructura de almacenamiento en GCP mediante Terraform.
Análisis Exploratorio de Datos (EDA) para limpiar ruido, evitar multicolinealidad y seleccionar features candidatas.
Sprint 2: Modelado, Backtesting y MLOps (El Motor)
Creación de un pipeline de entrenamiento modular para probar múltiples algoritmos (lineales, árboles, redes neuronales).
Implementación de validación cruzada temporal con ventanas móviles (rolling windows) y decaimiento del peso de los datos recientes.
Desarrollo de la función de evaluación financiera (Simulador de ROI y cálculo de EV).
Integración de MLflow para el registro automatizado de todos los experimentos.
Sprint 3: Despliegue y Paper Trading (Validación)
Empaquetado del modelo ganador.
Creación del pipeline de inferencia diaria en GCP (Cloud Run + Cloud Scheduler).
Inicio de la fase de un mes de predicciones en tiempo real capturando los resultados ("Paper Trading") para validar la rentabilidad antes de arriesgar capital.
