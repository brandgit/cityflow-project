"""
Configuration centralisée pour le traitement des données CityFlow Analytics
Utilise des variables d'environnement pour la configuration AWS
"""

import os
from pathlib import Path

# Charger les variables d'environnement depuis le fichier .env si présent
try:
    from dotenv import load_dotenv
    # Charger .env depuis le répertoire racine du projet
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"✓ Fichier .env chargé depuis: {env_path}")
except ImportError:
    # python-dotenv non installé, continuer avec les variables d'environnement système
    pass

# Chemins de base (pour développement local, sinon depuis S3)
BASE_DIR = Path(__file__).parent.parent

# Variables d'environnement pour chemins de données
# En production (EC2), ces chemins pointent vers S3 ou EFS
# En local, utiliser les valeurs du fichier .env ou les chemins par défaut
DATA_DIR = os.getenv("DATA_DIR")
if not DATA_DIR:
    DATA_DIR = BASE_DIR / "bucket-cityflow-paris-s3-raw" / "cityflow-raw" / "raw"
else:
    DATA_DIR = Path(DATA_DIR)

# Chemins fichiers batch (depuis S3 ou local)
BATCH_DATA_PATH = os.getenv("BATCH_DATA_PATH")
if not BATCH_DATA_PATH:
    BATCH_DATA_PATH = Path(DATA_DIR) / "batch"
else:
    BATCH_DATA_PATH = Path(BATCH_DATA_PATH)

COMPTAGES_CSV = os.getenv("COMPTAGES_CSV")
if not COMPTAGES_CSV:
    COMPTAGES_CSV = Path(BATCH_DATA_PATH) / "comptages-routiers-permanents-2.csv"
else:
    COMPTAGES_CSV = Path(COMPTAGES_CSV)

CHANTIERS_CSV = os.getenv("CHANTIERS_CSV")
if not CHANTIERS_CSV:
    CHANTIERS_CSV = Path(BATCH_DATA_PATH) / "chantiers-perturbants-la-circulation.csv"
else:
    CHANTIERS_CSV = Path(CHANTIERS_CSV)

REFERENTIEL_CSV = os.getenv("REFERENTIEL_CSV")
if not REFERENTIEL_CSV:
    REFERENTIEL_CSV = Path(BATCH_DATA_PATH) / "referentiel-geographique-pour-les-donnees-trafic-issues-des-capteurs-permanents.csv"
else:
    REFERENTIEL_CSV = Path(REFERENTIEL_CSV)

# Chemins fichiers API (depuis S3 ou local)
API_DATA_PATH = os.getenv("API_DATA_PATH")
if not API_DATA_PATH:
    API_DATA_PATH = Path(DATA_DIR) / "api"
else:
    API_DATA_PATH = Path(API_DATA_PATH)
# Les chemins API sont dynamiques selon la date/heure
# En production, utiliser S3 avec partitionnement par date/heure
# Note: API_DATA_PATH reste un Path object pour faciliter les opérations

# Chemins spécifiques pour chaque type d'API (développement local)
# En production, ces chemins sont dynamiques selon dt=YYYY-MM-DD/hour=HH
# Par défaut, utiliser la date d'aujourd'hui (peut être surchargé via env)
from datetime import datetime
API_DATE = os.getenv("API_DATE", datetime.now().strftime("%Y-%m-%d"))
API_HOUR = os.getenv("API_HOUR", "02")

BIKES_JSON_PATH = API_DATA_PATH / "bikes" / f"dt={API_DATE}" / f"hour={API_HOUR}"
TRAFFIC_JSON_PATH = API_DATA_PATH / "traffic" / f"dt={API_DATE}" / f"hour={API_HOUR}"
WEATHER_JSON_PATH = API_DATA_PATH / "weather" / f"dt={API_DATE}" / f"hour={API_HOUR}"

# Chemins output (local uniquement pour développement)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "output")))
METRICS_DIR = OUTPUT_DIR / "metrics"
REPORTS_DIR = OUTPUT_DIR / "reports"
PROCESSED_DIR = OUTPUT_DIR / "processed"

# Création des répertoires output si nécessaire (uniquement en local)
if not os.getenv("AWS_EXECUTION_ENV"):  # Pas dans Lambda
    for directory in [OUTPUT_DIR, METRICS_DIR, REPORTS_DIR, PROCESSED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# Paramètres traitement
CHUNK_SIZE = 10000  # Lignes par chunk pour traitement Lambda
EC2_CHUNK_SIZE = 100000  # Lignes pour traitement EC2
MAX_FILE_SIZE_MB = 500  # Taille max pour traitement Lambda (au-delà → EC2)

# Seuils validation
TAUX_OCCUPATION_SEUIL_CONGESTION = 80  # % pour alerte congestion
TAUX_OCCUPATION_SEUIL_CRITIQUE = 90  # % pour alerte critique
DUREE_ALERTE_CONGESTION_MINUTES = 120  # Durée minimale pour alerte
CAPTEUR_DEFAILLANT_HEURES = 6  # Heures sans données pour considérer défaillant
VARIATION_ANOMALIE_POURCENT = 300  # Variation > 300% pour détecter anomalie

# Paramètres calcul temps perdu
VITESSE_REFERENCE_NORMALE = 50  # km/h pour routes normales
VITESSE_REFERENCE_URBAINE = 30  # km/h pour zones urbaines
TAUX_OCCUPATION_VITESSE = {
    "faible": (0, 30, 1.0),  # (min, max, coefficient)
    "moyen": (30, 50, 0.8),
    "eleve": (50, 70, 0.6),
    "critique": (70, 100, 0.4)  # vitesse = 20 km/h si > 70%
}

# Arrondissements Paris
ARRONDISSEMENTS_PARIS = [f"750{i:02d}" for i in range(1, 21)]

# Catégories impacts chantiers
IMPACT_CHANTIERS = {
    "BARRAGE_TOTAL": 100,
    "IMPASSE": 80,
    "RESTREINTE": 50,
    "SENS_UNIQUE": 30
}

# Niveaux sévérité disruptions RATP
SEVERITE_RATP = {
    "CRITIQUE": 50,  # priority >= 50
    "ELEVEE": 30,    # priority >= 30
    "MOYENNE": 15,   # priority >= 15
    "FAIBLE": 0      # priority < 15
}

# Configuration météo
CONDITIONS_METEO = {
    "PLUVIEUX": {"precip": 5},  # mm
    "VENTEUX": {"windspeed": 30},  # km/h
    "FROID": {"temp": 10},  # °C
    "CHAUD": {"temp": 25}   # °C
}

# Configuration logs
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration AWS - Variables d'environnement

# DynamoDB Tables
DYNAMODB_METRICS_TABLE = os.getenv("DYNAMODB_METRICS_TABLE", "cityflow-metrics")
DYNAMODB_REPORTS_TABLE = os.getenv("DYNAMODB_REPORTS_TABLE", "cityflow-daily-reports")

# S3 Buckets
S3_REPORTS_BUCKET = os.getenv("S3_REPORTS_BUCKET", "cityflow-reports")
S3_REPORTS_PREFIX = os.getenv("S3_REPORTS_PREFIX", "reports")

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")

# Configuration DynamoDB (ancien format, conservé pour compatibilité)
DYNAMODB_TABLES = {
    "traffic_metrics": DYNAMODB_METRICS_TABLE,
    "traffic_global": DYNAMODB_METRICS_TABLE,
    "bikes_metrics": DYNAMODB_METRICS_TABLE,
    "weather_metrics": DYNAMODB_METRICS_TABLE,
    "daily_report": DYNAMODB_REPORTS_TABLE,
    "chantiers": DYNAMODB_METRICS_TABLE,
    "referentiel": DYNAMODB_METRICS_TABLE
}

