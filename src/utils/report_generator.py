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
        """Genera un reporte HTML visualmente atractivo con nombres de equipos."""
        if predictions_df is None or predictions_df.empty:
            return "<p>No hay partidos programados para hoy.</p>"
        
        html = f"""
        <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }}
                th, td {{ border: 1px solid #dddddd; text-align: left; padding: 12px; }}
                th {{ background-color: #0d1b2a; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .recommendation-HOME {{ color: green; font-weight: bold; }}
                .recommendation-AWAY {{ color: blue; font-weight: bold; }}
                .recommendation-SKIP {{ color: gray; }}
            </style>
        </head>
        <body>
            <h2>🏀 Cartelera de Apuestas del Día - {datetime.now().strftime('%Y-%m-%d')}</h2>
            <table>
                <tr>
                    <th>Local</th>
                    <th>Visitante</th>
                    <th>Prob. Victoria Local</th>
                    <th>Recomendación</th>
                </tr>
        """

        for _, row in predictions_df.iterrows():
            rec_class = f"recommendation-{row['RECOMMENDATION']}"
            
            # Obtener nombres (si el ID no existe por alguna razón, se muestra el ID)
            home_name = NBAReportGenerator.TEAM_NAMES.get(int(row['HOME_ID']), str(row['HOME_ID']))
            away_name = NBAReportGenerator.TEAM_NAMES.get(int(row['AWAY_ID']), str(row['AWAY_ID']))
            
            html += f"""
                <tr>
                    <td>{home_name}</td>
                    <td>{away_name}</td>
                    <td>{row['PROB_HOME_WIN']:.2%}</td>
                    <td class="{rec_class}">{row['RECOMMENDATION']}</td>
                </tr>
            """

        html += """
            </table>
            <br>
            <p><i>Este es un sistema automatizado (Oráculo NBA v2). Juega con responsabilidad.</i></p>
        </body>
        </html>
        """
        return html

