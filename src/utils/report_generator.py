import pandas as pd
from datetime import datetime

class NBAReportGenerator:
    # Mapeo oficial de IDs de la NBA a Nombres de Equipos
    TEAM_NAMES = {
        1610612737: "Atlanta Hawks",
        1610612738: "Boston Celtics",
        1610612739: "Cleveland Cavaliers",
        1610612740: "New Orleans Pelicans",
        1610612741: "Chicago Bulls",
        1610612742: "Dallas Mavericks",
        1610612743: "Denver Nuggets",
        1610612744: "Golden State Warriors",
        1610612745: "Houston Rockets",
        1610612746: "LA Clippers",
        1610612747: "Los Angeles Lakers",
        1610612748: "Miami Heat",
        1610612749: "Milwaukee Bucks",
        1610612750: "Minnesota Timberwolves",
        1610612751: "Brooklyn Nets",
        1610612752: "New York Knicks",
        1610612753: "Orlando Magic",
        1610612754: "Indiana Pacers",
        1610612755: "Philadelphia 76ers",
        1610612756: "Phoenix Suns",
        1610612757: "Portland Trail Blazers",
        1610612758: "Sacramento Kings",
        1610612759: "San Antonio Spurs",
        1610612760: "Oklahoma City Thunder",
        1610612761: "Toronto Raptors",
        1610612762: "Utah Jazz",
        1610612763: "Memphis Grizzlies",
        1610612764: "Washington Wizards",
        1610612765: "Detroit Pistons",
        1610612766: "Charlotte Hornets"
    }

    @staticmethod
    def generate_html_report(predictions_df):
        """Genera un reporte HTML visualmente atractivo con métricas de Value Betting."""
        if predictions_df is None or predictions_df.empty:
            return "<p>No hay partidos programados para hoy.</p>"
        
        html = f"""
        <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 14px; }}
                th, td {{ border: 1px solid #dddddd; text-align: center; padding: 10px; }}
                th {{ background-color: #0d1b2a; color: white; }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .recommendation-HOME {{ background-color: #d4edda; color: #155724; font-weight: bold; }}
                .recommendation-AWAY {{ background-color: #cce5ff; color: #004085; font-weight: bold; }}
                .recommendation-NO_BET {{ color: #6c757d; font-style: italic; }}
                .value-high {{ color: #28a745; font-weight: bold; }}
                .header-container {{ background: #1d3557; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            </style>
        </head>
        <body>
            <div class="header-container">
                <h1 style="margin:0;">🏀 Oráculo NBA v2: Value Betting Report</h1>
                <p style="margin:5px 0 0 0;">Fecha: {datetime.now().strftime('%d/%m/%Y')} | Banca Virtual de Paper Trading: $20,000 USD</p>
            </div>
            <table>
                <tr>
                    <th>Local</th>
                    <th>Visitante</th>
                    <th>Prob. Modelo</th>
                    <th>Mejor Cuota</th>
                    <th>Casa de Apuestas</th>
                    <th>Expected Value (EV)</th>
                    <th>Asignación Kelly</th>
                    <th>Inversión Sugerida</th>
                    <th>Recomendación</th>
                </tr>
        """

        for _, row in predictions_df.iterrows():
            rec = row['RECOMMENDATION']
            rec_class = f"recommendation-{rec.replace(' ', '_')}"
            
            home_name = NBAReportGenerator.TEAM_NAMES.get(int(row['HOME_ID']), str(row['HOME_ID']))
            away_name = NBAReportGenerator.TEAM_NAMES.get(int(row['AWAY_ID']), str(row['AWAY_ID']))
            
            # Formateo de valores
            prob_pct = f"{row['PROB_HOME_WIN']:.1%}" if rec == 'HOME' else f"{1-row['PROB_HOME_WIN']:.1%}"
            ev_pct = f"{row['EV']:.2%}"
            kelly_pct = f"{row['KELLY_PCT']:.2%}"
            units = f"${row['UNITS_SUGGESTED']:.2f}"
            odds = f"{row['ODDS']:.2f}" if row['ODDS'] > 0 else "N/A"
            
            html += f"""
                <tr>
                    <td>{home_name}</td>
                    <td>{away_name}</td>
                    <td>{prob_pct}</td>
                    <td><b>{odds}</b></td>
                    <td>{row['BOOKMAKER']}</td>
                    <td class="value-high">{ev_pct}</td>
                    <td>{kelly_pct}</td>
                    <td><mark>{units}</mark></td>
                    <td class="{rec_class}">{rec}</td>
                </tr>
            """

        html += """
            </table>
            <br>
            <div style="font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
                <p><b>Glosario:</b><br>
                - <b>EV:</b> Ventaja matemática sobre la casa de apuestas.<br>
                - <b>Kelly:</b> Gestión de banca fraccional (0.25) para maximizar crecimiento logarítmico.<br>
                - <b>Banca Virtual:</b> Simulación basada en un capital ficticio inicial de $20,000 USD para Paper Trading.</p>
                <p><i>Disclaimer: Este reporte es informativo. Las apuestas deportivas conllevan riesgo.</i></p>
            </div>
        </body>
        </html>
        """
        return html

    @staticmethod
    def generate_props_report(props_df, bankroll=20000):
        """Genera un reporte HTML de picks de Player Props."""
        if props_df is None or props_df.empty:
            return "<p>No hay picks de Player Props disponibles para hoy.</p>"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
                th, td {{ border: 1px solid #dddddd; text-align: center; padding: 10px; }}
                th {{ background-color: #0d1b2a; color: white; }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .value-high {{ color: #28a745; font-weight: bold; }}
                .header-container {{ background: #1d3557; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            </style>
        </head>
        <body>
            <div class="header-container">
                <h1 style="margin:0;">🏀 Oráculo NBA v2: Player Props Report</h1>
                <p style="margin:5px 0 0 0;">Fecha: {datetime.now().strftime('%d/%m/%Y')} | Banca Virtual: ${bankroll:,.0f} USD</p>
            </div>
            <table>
                <tr>
                    <th>Jugador</th>
                    <th>Mercado</th>
                    <th>Línea</th>
                    <th>Cuota</th>
                    <th>Casa</th>
                    <th>EV</th>
                    <th>Kelly %</th>
                    <th>Inversión</th>
                </tr>
        """

        for _, row in props_df.iterrows():
            ev_pct    = f"{row.get('ev', 0):.2%}"
            kelly_pct = f"{row.get('kelly_pct', 0):.2%}"
            bookmaker = row.get('bookmaker', 'N/A')
            odds      = row.get('odds_open', 'N/A')
            odds_str  = f"{odds:.2f}" if isinstance(odds, float) else str(odds)

            html += f"""
                <tr>
                    <td><b>{row['player_name']}</b></td>
                    <td>{row['market']}</td>
                    <td>{row['line']}</td>
                    <td>{odds_str}</td>
                    <td>{bookmaker}</td>
                    <td class="value-high">{ev_pct}</td>
                    <td>{kelly_pct}</td>
                    <td><mark>${row['stake_usd']:.2f}</mark></td>
                </tr>
            """

        html += """
            </table>
            <br>
            <div style="font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
                <p><b>Glosario:</b><br>
                - <b>EV:</b> Ventaja matemática sobre la casa de apuestas.<br>
                - <b>Kelly:</b> Gestión de banca fraccional (0.25) para maximizar crecimiento logarítmico.<br>
                - <b>Banca Virtual:</b> Simulación basada en un capital ficticio inicial de $20,000 USD para Paper Trading.</p>
                <p><i>Disclaimer: Este reporte es informativo. Las apuestas deportivas conllevan riesgo.</i></p>
            </div>
        </body>
        </html>
        """
        return html

