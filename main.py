import traceback
import os
from flask import Flask, jsonify
from src.models.inference import NBAOracleInference
from src.utils.email_service import NBAEmailService
from src.utils.report_generator import NBAReportGenerator
from src.utils.bigquery_client import NBABigQueryClient
from src.utils.logger import logger

app = Flask(__name__)

@app.route("/", methods=["POST", "GET"])
def run_oracle():
    email_service = NBAEmailService()
    bq_client = NBABigQueryClient()
    
    try:
        logger.info("🏀 INICIANDO EJECUCIÓN DEL ORÁCULO NBA (VÍA HTTP)...")
        
        # 1. Inferencia
        oracle = NBAOracleInference()
        predictions_df = oracle.predict_today()
        
        if predictions_df is not None and not predictions_df.empty:
            # 2. Persistencia en BigQuery
            bq_client.insert_predictions(predictions_df)
            
            # 3. Generación de Reporte y Envío de Email
            report_html = NBAReportGenerator.generate_html_report(predictions_df)
            email_service.send_prediction_report(report_html)
            
            logger.info("✅ EJECUCIÓN COMPLETADA EXITOSAMENTE.")
            return jsonify({"status": "success", "message": "Predicciones enviadas"}), 200
        else:
            msg = "No se generaron predicciones hoy."
            logger.warning(f"⚠️ {msg}")
            return jsonify({"status": "warning", "message": msg}), 200
            
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"❌ FALLO CRÍTICO EN LA EJECUCIÓN:\n{error_msg}")
        email_service.send_error_alert(error_msg)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Para ejecución local
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
