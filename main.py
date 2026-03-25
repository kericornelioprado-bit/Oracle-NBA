import traceback
import os
from flask import Flask, jsonify
from src.models.inference import NBAOracleInference
from src.utils.email_service import NBAEmailService
from src.utils.report_generator import NBAReportGenerator
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger

# Módulos de Jobs V2
from src.jobs import settle_bets, sunday_update

app = Flask(__name__)

@app.route("/", methods=["POST", "GET"])
def run_oracle():
    email_service = NBAEmailService()
    bq_client = NBABigQueryClient()
    
    try:
        logger.info("🏀 INICIANDO EJECUCIÓN DEL ORÁCULO NBA V2 (VÍA HTTP)...")
        
        # 1. Inferencia V2
        oracle = NBAOracleInference()
        ml_df, props_df = oracle.predict_today()
        
        # Combinar los dataframes para el generador de reportes (simplificación para el MVP)
        # O usar solo ml_df para compatibilidad con el reporte actual si props_df está vacío.
        predictions_df = ml_df 
        
        if predictions_df is not None and not predictions_df.empty:
            # 2. Persistencia en BigQuery (Moneyline histórico)
            bq_client.insert_predictions(predictions_df)

            # 3. Generación de Reporte y Envío de Email
            report_html = NBAReportGenerator.generate_html_report(predictions_df)
            email_service.send_prediction_report(report_html)

            logger.info("✅ EJECUCIÓN COMPLETADA EXITOSAMENTE.")
            return jsonify({"status": "success", "message": "Predicciones enviadas"}), 200
        else:
            msg = "No hay partidos NBA programados para hoy."
            logger.warning(f"⚠️ {msg}")
            email_service.send_email(
                subject="🏀 Oráculo NBA: Sin partidos hoy",
                body=msg,
                is_html=False
            )
            return jsonify({"status": "warning", "message": msg}), 200
            
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"❌ FALLO CRÍTICO EN LA EJECUCIÓN:\n{error_msg}")
        email_service.send_error_alert(error_msg)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/settle", methods=["POST", "GET"])
def settle():
    """Endpoint para el Cloud Scheduler de Liquidación (03:00 AM)"""
    try:
        settle_bets.main()
        return jsonify({"status": "success", "message": "Apuestas liquidadas."}), 200
    except Exception as e:
        logger.error(f"Error en endpoint settle: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/update_portfolio", methods=["POST", "GET"])
def update_portfolio():
    """Endpoint para el Cloud Scheduler del Domingo (23:59)"""
    try:
        sunday_update.main()
        return jsonify({"status": "success", "message": "Portafolio actualizado."}), 200
    except Exception as e:
        logger.error(f"Error en endpoint update_portfolio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Para ejecución local
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
