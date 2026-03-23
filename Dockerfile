# Usamos la imagen oficial de Python para máxima estabilidad y compatibilidad
FROM python:3.11-slim

# Metadatos
LABEL maintainer="Oracle NBA Team"
LABEL description="Environment for NBA Predictive Model development"

# Instalamos dependencias del sistema necesarias para XGBoost y GCS
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos requirements y los instalamos
# Usamos --upgrade para asegurar que las librerías de Google se vinculen correctamente
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos la estructura del proyecto
COPY . .

# Exponemos el puerto
EXPOSE 8080

# Usamos Gunicorn para el servidor HTTP
# Aumentamos el timeout a 600 segundos (10 min) para procesos pesados de la API NBA
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "600", "--workers", "1", "--threads", "4", "main:app"]
