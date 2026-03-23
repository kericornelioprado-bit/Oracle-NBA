Sprint 1: Data Ingestion & EDA
Objetivo del Sprint: Tener un pipeline automatizado (o semi-automatizado) que extraiga datos históricos de la NBA, los almacene de forma segura en la nube y nos permita identificar las variables estadísticamente significativas para el modelo.
Historia de Usuario 1: Configuración del Entorno y Repositorio
"Como Data Scientist, quiero configurar mi entorno de desarrollo local y de control de versiones para mantener el código organizado y reproducible."
Criterios de Aceptación:
Repositorio inicializado en Git y alojado en GitHub.
Estructura de carpetas definida (ej. data/, notebooks/, src/, infra/).
Entorno virtual de Python creado con un archivo requirements.txt inicial (pandas, numpy, scikit-learn, requests).
Dockerfile base creado para estandarizar el entorno de ejecución, asegurando que el código corra igual en tu equipo local que en la nube.
Historia de Usuario 2: Extracción de Datos Históricos (API)
"Como Ingeniero de Datos, quiero conectar un script de Python a una API de la NBA para descargar el historial de partidos y estadísticas de las últimas 3-5 temporadas."
Criterios de Aceptación:
API seleccionada y credenciales (API keys) configuradas como variables de entorno (nunca en el código duro).
Script en Python desarrollado para iterar sobre temporadas pasadas y extraer resultados de partidos (Moneyline) y estadísticas de equipo.
Manejo de errores implementado (ej. reintentos si la API falla o límite de peticiones alcanzado).
Historia de Usuario 3: Almacenamiento Raw en la Nube
"Como Arquitecto de Datos, quiero aprovisionar los recursos necesarios en GCP para almacenar los datos crudos extraídos de la API."
Criterios de Aceptación:
Código de infraestructura escrito en Terraform (main.tf, variables.tf) para desplegar un bucket en Google Cloud Storage o un dataset en BigQuery.
El script de extracción de Python (Historia 2) modificado para escribir el archivo final (CSV o Parquet) directamente en este almacenamiento en GCP.
Historia de Usuario 4: Análisis Exploratorio y Selección de Variables (EDA)
"Como Data Scientist, quiero analizar los datos históricos para limpiar el ruido y seleccionar las variables con mayor poder predictivo."
Criterios de Aceptación:
Limpieza de datos completada (manejo de valores nulos, estandarización de nombres de equipos).
Análisis de correlación ejecutado para evitar multicolinealidad (ej. si Offensive Rating y Puntos por Partido dicen lo mismo, descartar una).
Lista final de features candidatas documentada (ej. Win streak actual, Pace, días de descanso, porcentaje de tiros de campo).
Sprint 2: Modelado, Backtesting y MLOps
Objetivo del Sprint: Desarrollar un pipeline automatizado de entrenamiento que evalúe múltiples algoritmos utilizando validación temporal, optimizando para rentabilidad financiera (EV) y registrando todos los experimentos automáticamente.
Historia de Usuario 1: Pipeline de Entrenamiento Multi-Modelo
"Como Data Scientist, quiero un pipeline modular que me permita entrenar y comparar distintos algoritmos rápidamente."
Criterios de Aceptación:
Código estructurado para instanciar dinámicamente al menos tres tipos de modelos (ej. Regresión Logística, XGBoost, Red Neuronal simple).
Función de búsqueda de hiperparámetros automatizada (ej. GridSearch o RandomSearch) implementada para cada modelo.
Historia de Usuario 2: Validación Temporal y Ponderación de Datos
"Como Ingeniero de Machine Learning, quiero que el modelo respete la cronología de los eventos y pondere la información reciente para evitar fuga de datos (data leakage) y adaptarse a cambios en los equipos."
Criterios de Aceptación:
Implementación de TimeSeriesSplit para la evaluación cruzada.
Creación de features de ventana móvil (ej. promedio de puntos de los últimos 5, 10 y 15 partidos).
Mecanismo de decaimiento (decay) temporal aplicado a las observaciones del dataset de entrenamiento.
Historia de Usuario 3: Evaluación Basada en Valor Esperado (EV) y Cuotas
"Como Analista Cuantitativo, quiero evaluar el rendimiento de los modelos no solo por su accuracy, sino por su retorno de inversión simulado contra cuotas históricas."
Criterios de Aceptación:
Integración de un dataset de cuotas (odds) históricas de cierre de casas de apuestas.
Función de métrica personalizada escrita en Python que calcule el ROI simulado y el EV de las predicciones en el conjunto de prueba.
Generación de una curva de capital (equity curve) simulada para visualizar el rendimiento financiero del modelo a lo largo de la temporada de prueba.
Historia de Usuario 4: Tracking de Experimentos Automatizado
"Como MLOps Engineer, quiero registrar automáticamente cada corrida de entrenamiento para comparar versiones sin depender de notas manuales."
Criterios de Aceptación:
Herramienta de tracking (como MLflow o Weights & Biases) integrada en el script de entrenamiento.
Registro automático de hiperparámetros, métricas clásicas (LogLoss, Brier Score), métricas de negocio (ROI, EV), y versionado del archivo del modelo resultante.
