# PRD: Oráculo NBA v2 - Advanced Ensemble & Value Betting

## Visión del Producto
Evolucionar el sistema de predicción hacia una plataforma de inversión cuantitativa que no solo prediga resultados, sino que identifique ineficiencias del mercado (Value Betting) y gestione el capital mediante algoritmos de asignación de riesgo (Kelly Criterion), operando de forma 100% autónoma en la nube.

## Historias de Usuario

### Sprint 1: Cimientos y Extracción (Completado)
- **HU1: Setup del Entorno:** Configuración de `uv`, Docker y estructura modular.
- **HU2: Extracción NBA API:** Pipeline de ingesta histórica.

### Sprint 2: Inteligencia y Modelado (Completado)
- **HU1: Multi-Modelo:** Pipeline para LR, XGBoost y LightGBM.
- **HU2: Advanced Stacking:** Implementación de `StackingClassifier` (LR + XGBoost).

### Sprint 3: Automatización y Despliegue (Completado)
- **HU1: CI/CD Pipeline:** GitHub Actions con Quality Gate.
- **HU2: Persistencia Histórica:** Integración con BigQuery para auditoría de ROI.

### Sprint 4: Value Betting & Capital Management (MVP v2 - EN CURSO)
- **HU1: Integración de Cuotas Reales:** Conexión con *The Odds API* para obtener cuotas en tiempo real de casas de apuestas seleccionadas (Pinnacle, Bet365, etc.).
- **HU2: Motor de Valor Esperado (EV):** Cálculo dinámico de EV comparando la probabilidad del modelo contra la cuota del mercado. Filtro estricto de seguridad: **EV > 2%**.
- **HU3: Gestión de Riesgo (Kelly):** Implementación del Criterio de Kelly Fraccional (Quarter-Kelly) para determinar el tamaño óptimo de la apuesta.
- **HU4: UX de Inversión:** Reporte diario que incluye columnas de Cuota, Probabilidad, EV%, Kelly% y Unidades Sugeridas (basadas en banca virtual de $1,000 USD).
- **HU5: Orquestación "Ventana Dorada":** Programación de la ejecución a las **16:30 CST** para capturar el cierre de reportes de lesiones y maximizar la ventaja informativa.

## Requisitos No Funcionales
- **Arquitectura Stateless:** Ejecución en Cloud Run sin dependencia de estado persistente entre días para el bankroll.
- **Line Shopping Inteligente:** Comparación de cuotas entre 3-5 bookmakers configurables vía variables de entorno.
- **Resiliencia:** Manejo de límites de cuota de la API y fallos de conectividad.
- **Observabilidad:** Registro detallado en BigQuery de las cuotas encontradas vs. probabilidades del modelo para análisis de cierre de línea (Closing Line Value).

