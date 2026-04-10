import traceback
import os
from datetime import datetime
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
        
        # Filtrar solo predicciones de Moneyline que tengan valor (EV > 2% y no sea NO BET)
        if ml_df is not None and not ml_df.empty:
            ml_picks_df = ml_df[(ml_df['RECOMMENDATION'] != 'NO BET') & (ml_df['EV'] > 0.02)]
        else:
            ml_picks_df = ml_df
        
        if (ml_df is not None and not ml_df.empty) or (props_df is not None and not props_df.empty):
            # 2. Persistencia en BigQuery (Moneyline histórico completo, no solo picks)
            if ml_df is not None:
                bq_client.insert_predictions(ml_df)

            # 3. Generación de Reporte y Envío de Email
            props_section = ""
            if props_df is not None and not props_df.empty:
                props_section = NBAReportGenerator.generate_props_report(props_df, bankroll=int(oracle.bankroll), wrap_html=False)
            
            ml_section = ""
            if ml_picks_df is not None and not ml_picks_df.empty:
                ml_section = NBAReportGenerator.generate_html_report(ml_picks_df, wrap_html=False)
            
            if props_section or ml_section:
                # Layout Maestro
                report_html = f"""
                <html>
                <head>{NBAReportGenerator._get_css()}</head>
                <body>
                    <div class="header-container">
                        <h1 style="margin:0;">🏀 Oráculo NBA v2: Picks del Día</h1>
                        <p style="margin:5px 0 0 0;">Fecha: {datetime.now().strftime('%d/%m/%Y')} | Banca Virtual: ${int(oracle.bankroll):,} USD</p>
                    </div>
                    {props_section}
                    {ml_section}
                    <div style="font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px; margin-top: 20px;">
                        <p><b>Glosario:</b><br>
                        - <b>EV:</b> Ventaja matemática sobre la casa de apuestas.<br>
                        - <b>Kelly:</b> Gestión de banca fraccional (0.25) para maximizar crecimiento logarítmico.<br>
                        - <b>Banca Virtual:</b> Simulación basada en un capital ficticio inicial de $20,000 USD para Paper Trading.</p>
                        <p><i>Disclaimer: Este reporte es informativo. Las apuestas deportivas conllevan riesgo.</i></p>
                    </div>
                </body>
                </html>
                """
                email_service.send_prediction_report(report_html)
                logger.info("✅ EJECUCIÓN COMPLETADA EXITOSAMENTE CON PICKS ENVIADOS.")
            else:
                msg = "No se encontraron oportunidades con Valor Esperado (EV) positivo hoy."
                logger.info(f"ℹ️ {msg}")
                email_service.send_email(
                    subject="🏀 Oráculo NBA: Sin picks de valor hoy",
                    body=msg,
                    is_html=False
                )
            
            return jsonify({"status": "success", "message": "Proceso terminado"}), 200
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
