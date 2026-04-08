# Diagramas de Arquitectura — Oráculo NBA

> Generado por `/technical-writer` | 2026-03-23

---

## 1. Flujo de Datos Principal (End-to-End)

```mermaid
flowchart TD
    SCHED["☁️ Cloud Scheduler\n0 14 * * * UTC"]
    CR["☁️ Cloud Run\noracle-nba-service"]
    FLASK["🐍 Flask /\nmain.py"]

    subgraph ML["Moneyline (Game Picks)"]
        BDL_G["BallDontLie API\npartidos de hoy"]
        FE["NBAFeatureEngineer\nRolling [3,5,10,20] + rest days"]
        MODEL["Stacking Model\nLR + XGBoost\n63.91% accuracy"]
    end

    subgraph PROPS["Player Props"]
        ODDS["The Odds API v4\nget_all_player_props_today()\n~100 jugadores con cuotas"]
        BDL_P["BallDontLie API\nlogs últimos 30 días"]
        FEAT_P["PlayerStatsIngestion\nL10 rolling + std (shift-1)"]
        PROJ["MinutesProjector\ngame script adjustment"]
        EV["PlayerPropsModel\nP(Over) normal → EV\nKelly fraccional"]
    end

    BQ_ML["☁️ BigQuery\noracle_nba_ds.predictions"]
    BQ_PROPS["☁️ BigQuery\noracle_nba_ds.prop_bets"]
    RPT["NBAReportGenerator\nHTML con picks ML + props"]
    EMAIL["📧 Gmail SMTP :587"]

    SCHED -->|"POST OIDC"| CR
    CR --> FLASK
    FLASK --> BDL_G --> FE --> MODEL
    FLASK --> ODDS
    ODDS -->|"real_odds_map"| EV
    BDL_P --> FEAT_P --> PROJ --> EV
    MODEL -->|"picks ML"| BQ_ML
    EV -->|"EV > 5% → pick"| BQ_PROPS
    BQ_ML --> RPT
    BQ_PROPS --> RPT
    RPT --> EMAIL

    style SCHED fill:#4285F4,color:#fff
    style CR fill:#4285F4,color:#fff
    style BQ_ML fill:#4285F4,color:#fff
    style BQ_PROPS fill:#4285F4,color:#fff
    style MODEL fill:#FF6D00,color:#fff
    style EV fill:#FF6D00,color:#fff
    style EMAIL fill:#34A853,color:#fff
    style ODDS fill:#7B1FA2,color:#fff
```

---

## 2. Pipeline de ML (Entrenamiento)

```mermaid
flowchart LR
    RAW["📦 data/raw/\nnba_games_raw.parquet\n(2021-22 → 2023-24)"]
    ING["NBADataIngestor\ningestion.py"]
    FE["NBAFeatureEngineer\nfeature_engineering.py"]
    PROC["📦 data/processed/\nnba_games_features.parquet"]
    TUNE["NBAHyperTuner\nOptuna (20 trials)\nlog_loss minimize"]
    STACK["NBAStackingTrainer\nLR + XGBoost\ncv=5"]
    MLFLOW["📊 MLflow\nExperiments + Metrics"]
    ARTIFACT["📦 models/\nnba_best_model_stacking.joblib\nnba_best_model_tuned.joblib"]

    RAW --> ING
    ING -->|"fetch_season_games()"| FE
    FE -->|"rolling windows\nrest days\n80/20 temporal split"| PROC
    PROC --> TUNE
    TUNE -->|"best XGB params"| STACK
    STACK -->|"StackingClassifier fit"| ARTIFACT
    TUNE --> MLFLOW
    STACK --> MLFLOW

    style MLFLOW fill:#0194E2,color:#fff
    style ARTIFACT fill:#FF6D00,color:#fff
```

---

## 3. Arquitectura de Módulos Python

```mermaid
graph TB
    subgraph "main.py — Orquestador Flask"
        EP["POST/GET /"]
    end

    subgraph "src/models/"
        INF["inference.py\nNBAOracleInference"]
        TRAIN["trainer.py\nNBAModelTrainer"]
        STACK["stacking_trainer.py\nNBAStackingTrainer"]
        EVAL["evaluator.py\nNBAProfitSim"]
        TUNE["tuner.py\nNBAHyperTuner"]
    end

    subgraph "src/data/"
        ING["ingestion.py\nNBADataIngestor"]
        FENG["feature_engineering.py\nNBAFeatureEngineer"]
        EDA["eda_report.py\nrun_eda()"]
    end

    subgraph "src/utils/"
        BQ["bigquery_client.py\nNBABigQueryClient"]
        MAIL["email_service.py\nNBAEmailService"]
        RPT["report_generator.py\nNBAReportGenerator"]
        LOG["logger.py\nsetup_logger()"]
    end

    EP --> INF
    EP --> BQ
    EP --> RPT
    EP --> MAIL
    INF --> FENG
    STACK --> TRAIN
    STACK --> EVAL
    TUNE --> TRAIN
    TUNE --> EVAL
    TRAIN --> EVAL
    ING --> FENG

    style EP fill:#34A853,color:#fff
    style INF fill:#FF6D00,color:#fff
```

---

## 4. Pipeline de CI/CD (GitHub Actions)

```mermaid
flowchart LR
    PUSH["git push\nbranch: main"]

    subgraph "Job: test"
        PY["Setup Python 3.11"]
        INST["uv pip install\nrequirements.txt"]
        TEST["pytest tests/\n--cov=src"]
    end

    subgraph "Job: deploy (needs: test)"
        AUTH["Google Auth\nGCP_SA_KEY secret"]
        BUILD["docker build\n:github.sha tag"]
        PUSH_IMG["docker push\nArtifact Registry"]
        DEPLOY["gcloud run deploy\noracle-nba-service\nus-central1"]
    end

    PUSH --> PY --> INST --> TEST
    TEST -->|"✅ pass"| AUTH
    TEST -->|"❌ fail → BLOCKED"| PUSH
    AUTH --> BUILD --> PUSH_IMG --> DEPLOY

    style TEST fill:#34A853,color:#fff
    style DEPLOY fill:#4285F4,color:#fff
```

---

## 5. Infraestructura GCP (Terraform)

```mermaid
graph TB
    subgraph "GCP Project: oracle-nba"
        subgraph "Compute"
            CR["Cloud Run v2\noracle-nba-service\n1 vCPU / 512Mi\nscale 0→1"]
        end
        subgraph "Orchestration"
            CS["Cloud Scheduler\n0 14 * * * UTC\nPOST → Cloud Run"]
        end
        subgraph "Storage"
            GCS["Cloud Storage\noracle-nba-nba-data-lake\nversioning enabled"]
            BQ_DS["BigQuery Dataset\noracle_nba_ds"]
            BQ_TBL["BigQuery Table\npredictions\n9 campos"]
        end
        subgraph "IAM"
            SA["Service Account\noracle-nba-service-sa\nroles/bigquery.dataEditor\nroles/storage.objectAdmin"]
        end
        subgraph "CI/CD"
            AR["Artifact Registry\noracle-nba-repo\noracle-nba:sha"]
        end
    end

    CS -->|"OIDC token"| CR
    CR --> GCS
    CR --> BQ_DS
    BQ_DS --> BQ_TBL
    SA -.->|"attached to"| CR
    AR -->|"image"| CR

    style CR fill:#4285F4,color:#fff
    style CS fill:#4285F4,color:#fff
    style GCS fill:#4285F4,color:#fff
    style BQ_DS fill:#4285F4,color:#fff
    style SA fill:#FBBC05,color:#000
    style AR fill:#4285F4,color:#fff
```

---

## 6. Lógica de Recomendación de Apuesta

```mermaid
flowchart TD
    PROBA["prob_home_win\n(Stacking output)"]
    D1{prob > 0.524?}
    D2{prob < 0.476?}
    HOME["RECOMMENDATION: HOME\nApuesta al local"]
    AWAY["RECOMMENDATION: AWAY\nApuesta al visitante"]
    SKIP["RECOMMENDATION: SKIP\nNo apostar\n(zona break-even)"]

    PROBA --> D1
    D1 -->|"Sí"| HOME
    D1 -->|"No"| D2
    D2 -->|"Sí"| AWAY
    D2 -->|"No"| SKIP

    style HOME fill:#34A853,color:#fff
    style AWAY fill:#4285F4,color:#fff
    style SKIP fill:#9E9E9E,color:#fff
```

> **Justificación de umbrales:** Con odds 1.91 (-110 americano), el break-even es 1/1.91 = 52.36%. Se usa ±2.4% como margen de seguridad → [47.6%, 52.4%].
