#!/bin/bash
# ==============================================================================
# Script de Control Maestro (Golden Path) - Oráculo NBA v2
# ==============================================================================

APP_NAME="oracle-nba"
PORT="8080"
PID_FILE=".${APP_NAME}.pid"
LOG_FILE="${APP_NAME}_local.log"

# Colores para legibilidad
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  [${APP_NAME}] ya está corriendo (PID: $PID).${NC}"
            return 0
        fi
        rm "$PID_FILE"
    fi

    echo -e "${GREEN}🚀 Iniciando [${APP_NAME}] con uv...${NC}"
    
    # Comando de arranque: Inferencia diaria + Reporte
    # Usamos export PYTHONPATH=. para que reconozca el módulo 'src'
    export PYTHONPATH=.
    export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-sqlite:///data/mlflow/mlflow.db}"
    nohup uv run python3 main.py > "$LOG_FILE" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    
    sleep 2
    if ps -p $NEW_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ [${APP_NAME}] iniciado (PID: $NEW_PID).${NC}"
        echo -e "📄 Logs en: tail -f $LOG_FILE"
    else
        echo -e "${RED}❌ Error al iniciar. Revisa: cat $LOG_FILE${NC}"
        rm "$PID_FILE"
        exit 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo -e "${YELLOW}🛑 Deteniendo [${APP_NAME}] (PID: $PID)...${NC}"
        kill -15 $PID
        sleep 2
        [ -f "$PID_FILE" ] && rm "$PID_FILE"
        echo -e "${GREEN}✅ Detenido.${NC}"
    else
        echo -e "${YELLOW}⚠️  No está corriendo.${NC}"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        echo -e "${GREEN}🟢 ACTIVO (PID: $(cat "$PID_FILE"))${NC}"
    else
        echo -e "${RED}🔴 DETENIDO${NC}"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    restart) stop; sleep 1; start ;;
    *) echo "Uso: $0 {start|stop|status|restart}"; exit 1 ;;
esac
