import argparse
import sys
import traceback
import os
from datetime import datetime
from flask import Flask, jsonify, request

# Importaciones NBA (Legacy / Estable)
from src.models.inference import NBAOracleInference
from src.utils.email_service import NBAEmailService
from src.utils.report_generator import NBAReportGenerator
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger
from src.jobs import settle_bets, sunday_update

# --- INICIALIZACIÓN APP FLASK ---
app = Flask(__name__)

# --- HANDLERS NBA (MANTENIDOS POR COMPATIBILIDAD) ---
@app.route("/", methods=["POST", "GET"])
def run_oracle_nba():
    """Endpoint original para NBA (Vía HTTP)"""
    return run_job(sport="nba", job="predict")

@app.route("/settle", methods=["POST", "GET"])
def settle_nba():
    """Endpoint original para Liquidación NBA (03:00 AM)"""
    return run_job(sport="nba", job="settle")

@app.route("/update_portfolio", methods=["POST", "GET"])
def update_portfolio_nba():
    """Endpoint original para Update NBA (Domingo)"""
    return run_job(sport="nba", job="update")

# --- NUEVOS HANDLERS MULTI-DEPORTE (VÍA HTTP) ---
@app.route("/<sport>/<job>", methods=["POST", "GET"])
def run_dynamic_job(sport, job):
    """
    Endpoint dinámico para nuevos deportes (MLB, etc.)
    Ej: /mlb/ingest, /mlb/predict
    """
    return run_job(sport, job)

# --- CORE DISPATCHER ---
def run_job(sport, job):
    """
    Lógica maestra para ejecutar el proceso correcto.
    Se puede llamar vía Flask (HTTP) o vía CLI.
    """
    logger.info(f"🚀 EJECUTANDO: [{sport.upper()}] JOB: [{job.upper()}] - {datetime.now()}")
    
    try:
        if sport == "nba":
            return _execute_nba_logic(job)
        elif sport == "mlb":
            return _execute_mlb_logic(job)
        else:
            msg = f"Deporte '{sport}' no soportado."
            logger.error(msg)
            return jsonify({"status": "error", "message": msg}), 400
            
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"❌ FALLO CRÍTICO EN {sport.upper()} - {job.upper()}:\n{error_msg}")
        # Alertas de error (NBA usa su service, MLB usará el shared)
        if sport == "nba":
            NBAEmailService().send_error_alert(error_msg)
        else:
            from src.shared.email_service import EmailService
            EmailService(sport=sport).send_error_alert(error_msg)
            
        return jsonify({"status": "error", "message": str(e)}), 500

def _execute_nba_logic(job):
    """Encapsula la lógica legacy de la NBA."""
    if job == "predict":
        oracle = NBAOracleInference()
        ml_df, props_df = oracle.predict_today()
        # ... (aquí iría el resto del código del main.py original que ya conocemos)
        # Por simplicidad y seguridad, llamaremos a una función interna que replique el comportamiento exacto
        return _run_nba_oracle_flow(oracle, ml_df, props_df)
    
    elif job == "settle":
        settle_bets.main()
        return jsonify({"status": "success", "message": "NBA Bets Settled"}), 200
        
    elif job == "update":
        sunday_update.main()
        return jsonify({"status": "success", "message": "NBA Portfolio Updated"}), 200
    
    return jsonify({"status": "error", "message": f"NBA Job {job} no implementado"}), 400

def _execute_mlb_logic(job):
    """
    Lógica para Diamante MLB (Fase 1: Placeholders).
    Soporta ingest y predict de forma granular.
    """
    # Importaciones MLB (Carga perezosa para evitar errores si no están listos)
    try:
        if job == "ingest":
            logger.info("⚾ Iniciando Ingesta MLB (Early Ingest)...")
            # TODO: Llamar a src.mlb.jobs.daily_ingestion
            return jsonify({"status": "success", "message": "MLB Ingest Completed (Mock)"}), 200
            
        elif job == "predict":
            logger.info("⚾ Iniciando Predicción MLB (Pre-juego/Lineups)...")
            # TODO: Llamar a src.mlb.jobs.predict_and_trade
            return jsonify({"status": "success", "message": "MLB Predictions Completed (Mock)"}), 200
            
        elif job == "settle":
            logger.info("⚾ Iniciando Liquidación MLB...")
            # TODO: Llamar a src.mlb.jobs.settle_bets
            return jsonify({"status": "success", "message": "MLB Bets Settled (Mock)"}), 200
            
        return jsonify({"status": "error", "message": f"MLB Job {job} no implementado"}), 400
    except ImportError as e:
        return jsonify({"status": "error", "message": f"Módulo MLB no listo: {e}"}), 501

def _run_nba_oracle_flow(oracle, ml_df, props_df):
    """Réplica exacta del flujo principal de NBA del main.py original."""
    email_service = NBAEmailService()
    bq_client = NBABigQueryClient()
    
    # Filtrar picks Moneyline
    if ml_df is not None and not ml_df.empty:
        ml_picks_df = ml_df[(ml_df['RECOMMENDATION'] != 'NO BET') & (ml_df['EV'] > 0.02)]
    else:
        ml_picks_df = ml_df
    
    if (ml_df is not None and not ml_df.empty) or (props_df is not None and not props_df.empty):
        if ml_df is not None:
            bq_client.insert_predictions(ml_df)

        props_section = ""
        if props_df is not None and not props_df.empty:
            props_section = NBAReportGenerator.generate_props_report(props_df, bankroll=int(oracle.bankroll), wrap_html=False)
        
        ml_section = ""
        if ml_picks_df is not None and not ml_picks_df.empty:
            ml_section = NBAReportGenerator.generate_html_report(ml_picks_df, wrap_html=False)
        
        if props_section or ml_section:
            report_html = f"<html><head>{NBAReportGenerator._get_css()}</head><body>{props_section}{ml_section}</body></html>"
            email_service.send_prediction_report(report_html)
            return jsonify({"status": "success", "message": "NBA Picks Sent"}), 200
    
    return jsonify({"status": "success", "message": "NBA Processed, no picks found"}), 200

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle Multi-Sport Entry Point")
    parser.add_argument("--sport", type=str, help="Deporte (nba|mlb)")
    parser.add_argument("--job", type=str, help="Job a ejecutar (predict|ingest|settle|update)")
    parser.add_argument("--server", action="store_true", help="Iniciar servidor Flask")
    
    args = parser.parse_args()
    
    if args.server or len(sys.argv) == 1:
        # Modo Servidor (Cloud Run Service)
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)
    else:
        # Modo CLI (Cloud Run Job o Local Debug)
        if args.sport and args.job:
            # Simulamos un contexto de request para reutilizar run_job
            with app.test_request_context():
                run_job(args.sport, args.job)
        else:
            parser.print_help()
