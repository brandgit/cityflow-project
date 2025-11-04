"""
Point d'entrée principal - Orchestration complète du traitement des données CityFlow Analytics
Exécuté dans AWS (Lambda/EC2) pour le preprocessing
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports configuration
from config import settings

# Imports processeurs
from processors import (
    BikesProcessor, TrafficProcessor, WeatherProcessor,
    ComptagesProcessor, ChantiersProcessor, ReferentielProcessor
)

# Imports utilitaires (depuis processors/utils/)
from processors.utils.file_utils import (
    load_json, find_json_files, load_and_combine_json_files, find_csv_files
)

# Import services base de données (MongoDB ou DynamoDB)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.database_factory import get_database_service, get_database_type
from utils.metrics_optimizer import should_optimize_for_mongodb, optimize_metrics_for_storage


def load_raw_data(config) -> Dict[str, Any]:
    """
    Charge les données brutes depuis fichiers locaux
    (Sur EC2, les fichiers doivent être uploadés manuellement dans data/)
    
    Args:
        config: Configuration
    
    Returns:
        Dict avec toutes les données brutes par type
    """
    print("📁 Chargement des données depuis fichiers locaux...")
    return load_raw_data_local(config)


def load_raw_data_local(config) -> Dict[str, Any]:
    """
    Charge les données depuis fichiers locaux
    
    Args:
        config: Configuration
    
    Returns:
        Dict avec toutes les données brutes par type
    """
    raw_data = {
        "bikes": None,
        "traffic": None,
        "weather": None,
        "comptages": None,
        "chantiers": None,
        "referentiel": None
    }
    
    # Charger données API (JSON)
    try:
        # Bikes - Charger TOUS les fichiers et les combiner
        bikes_files = find_json_files(str(config.BIKES_JSON_PATH))
        if bikes_files:
            print(f"📁 Trouvé {len(bikes_files)} fichier(s) bikes")
            if len(bikes_files) > 1:
                print(f"  → Combinaison de {len(bikes_files)} fichiers...")
                raw_data["bikes"] = load_and_combine_json_files(bikes_files)
            else:
                raw_data["bikes"] = load_json(bikes_files[0])
        
        # Traffic - Charger TOUS les fichiers et les combiner
        traffic_files = find_json_files(str(config.TRAFFIC_JSON_PATH))
        if traffic_files:
            print(f"📁 Trouvé {len(traffic_files)} fichier(s) traffic")
            if len(traffic_files) > 1:
                print(f"  → Combinaison de {len(traffic_files)} fichiers...")
                raw_data["traffic"] = load_and_combine_json_files(traffic_files)
            else:
                raw_data["traffic"] = load_json(traffic_files[0])
        
        # Weather - Charger TOUS les fichiers et les combiner
        weather_files = find_json_files(str(config.WEATHER_JSON_PATH))
        if weather_files:
            print(f"📁 Trouvé {len(weather_files)} fichier(s) weather")
            if len(weather_files) > 1:
                print(f"  → Combinaison de {len(weather_files)} fichiers...")
                raw_data["weather"] = load_and_combine_json_files(weather_files)
            else:
                raw_data["weather"] = load_json(weather_files[0])
    except Exception as e:
        print(f"Erreur chargement données API: {e}")
    
    # Charger données Batch (CSV)
    try:
        # Comptages - Chercher tous les fichiers CSV dans le répertoire
        comptages_dir = config.COMPTAGES_CSV.parent
        comptages_files = find_csv_files(str(comptages_dir), "comptages*.csv")
        if comptages_files:
            print(f"📁 Trouvé {len(comptages_files)} fichier(s) comptages")
            if len(comptages_files) > 1:
                print(f"  ⚠ Plusieurs fichiers trouvés, utilisation du premier: {comptages_files[0]}")
                print(f"  💡 Pour traiter plusieurs fichiers, utilisez le traitement par chunk")
            raw_data["comptages"] = comptages_files[0]  # Utiliser le premier pour compatibilité
        elif config.COMPTAGES_CSV.exists():
            raw_data["comptages"] = str(config.COMPTAGES_CSV)
        
        # Chantiers - Chercher tous les fichiers CSV
        chantiers_dir = config.CHANTIERS_CSV.parent
        chantiers_files = find_csv_files(str(chantiers_dir), "chantiers*.csv")
        if chantiers_files:
            print(f"📁 Trouvé {len(chantiers_files)} fichier(s) chantiers")
            if len(chantiers_files) > 1:
                print(f"  ⚠ Plusieurs fichiers trouvés, utilisation du premier: {chantiers_files[0]}")
            raw_data["chantiers"] = chantiers_files[0]
        elif config.CHANTIERS_CSV.exists():
            raw_data["chantiers"] = str(config.CHANTIERS_CSV)
        
        # Référentiel - Chercher tous les fichiers CSV
        referentiel_dir = config.REFERENTIEL_CSV.parent
        referentiel_files = find_csv_files(str(referentiel_dir), "referentiel*.csv")
        if referentiel_files:
            print(f"📁 Trouvé {len(referentiel_files)} fichier(s) référentiel")
            if len(referentiel_files) > 1:
                print(f"  ⚠ Plusieurs fichiers trouvés, utilisation du premier: {referentiel_files[0]}")
            raw_data["referentiel"] = referentiel_files[0]
        elif config.REFERENTIEL_CSV.exists():
            raw_data["referentiel"] = str(config.REFERENTIEL_CSV)
    except Exception as e:
        print(f"Erreur chargement données batch: {e}")
    
    return raw_data


def load_raw_data_from_s3(config) -> Dict[str, Any]:
    """
    Charge les données directement depuis S3
    
    Args:
        config: Configuration
    
    Returns:
        Dict avec données par type
    """
    import os
    import tempfile
    from utils.aws_services import S3Service
    
    raw_data = {}
    
    # Configuration S3 EN DUR (plus besoin de .env)
    bucket_name = "bucket-cityflow-paris-s3-raw"
    prefix = "cityflow-raw/raw"
    
    print(f"📦 S3 Bucket: {bucket_name}")
    print(f"📦 S3 Prefix: {prefix}")
    
    s3_service = S3Service(bucket_name)
    
    try:
        # Charger données API (JSON/JSONL)
        # Bikes
        bikes_files = s3_service.list_files_in_s3(f"{prefix}/api/bikes/", ".jsonl")
        if not bikes_files:
            bikes_files = s3_service.list_files_in_s3(f"{prefix}/api/bikes/", ".json")
        
        if bikes_files:
            print(f"📁 Trouvé {len(bikes_files)} fichier(s) bikes dans S3")
            bikes_data = []
            for file_key in bikes_files:
                data = s3_service.read_json_from_s3(file_key)
                if data:
                    bikes_data.append(data)
            
            # Combiner toutes les données
            if bikes_data:
                combined = {"data": []}
                for d in bikes_data:
                    if "data" in d:
                        if isinstance(d["data"], list):
                            combined["data"].extend(d["data"])
                        else:
                            combined["data"].append(d["data"])
                raw_data["bikes"] = combined
        
        # Traffic
        traffic_files = s3_service.list_files_in_s3(f"{prefix}/api/traffic/", ".jsonl")
        if not traffic_files:
            traffic_files = s3_service.list_files_in_s3(f"{prefix}/api/traffic/", ".json")
        
        if traffic_files:
            print(f"📁 Trouvé {len(traffic_files)} fichier(s) traffic dans S3")
            # Combiner tous les fichiers traffic
            all_disruptions = []
            for file_key in traffic_files:
                data = s3_service.read_json_from_s3(file_key)
                if data and "data" in data:
                    items = data["data"] if isinstance(data["data"], list) else [data["data"]]
                    for item in items:
                        if "disruptions" in item:
                            all_disruptions.extend(item["disruptions"])
            
            if all_disruptions:
                raw_data["traffic"] = {"disruptions": all_disruptions}
        
        # Weather
        weather_files = s3_service.list_files_in_s3(f"{prefix}/api/weather/", ".jsonl")
        if not weather_files:
            weather_files = s3_service.list_files_in_s3(f"{prefix}/api/weather/", ".json")
        
        if weather_files:
            print(f"📁 Trouvé {len(weather_files)} fichier(s) weather dans S3")
            data = s3_service.read_json_from_s3(weather_files[0])
            if data:
                raw_data["weather"] = data
        
        # Charger données BATCH (CSV) - Téléchargement temporaire pour traitement
        # Les CSV sont trop volumineux pour être chargés en mémoire, on les télécharge temporairement
        
        # Comptages
        comptages_files = s3_service.list_files_in_s3(f"{prefix}/batch/", ".csv")
        comptages_files = [f for f in comptages_files if "comptages" in f.lower()]
        if comptages_files:
            print(f"📁 Trouvé {len(comptages_files)} fichier(s) comptages dans S3 ({comptages_files[0]})")
            print(f"  → Téléchargement temporaire (fichier volumineux)...")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                content = s3_service.read_csv_from_s3(comptages_files[0])
                if content:
                    tmp.write(content)
                    tmp.flush()
                    raw_data["comptages"] = tmp.name
                    print(f"  ✅ Fichier temporaire: {tmp.name}")
        
        # Chantiers
        chantiers_files = s3_service.list_files_in_s3(f"{prefix}/batch/", ".csv")
        chantiers_files = [f for f in chantiers_files if "chantiers" in f.lower()]
        if chantiers_files:
            print(f"📁 Trouvé {len(chantiers_files)} fichier(s) chantiers dans S3")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                content = s3_service.read_csv_from_s3(chantiers_files[0])
                if content:
                    tmp.write(content)
                    tmp.flush()
                    raw_data["chantiers"] = tmp.name
        
        # Référentiel
        referentiel_files = s3_service.list_files_in_s3(f"{prefix}/batch/", ".csv")
        referentiel_files = [f for f in referentiel_files if "referentiel" in f.lower() or "geographique" in f.lower()]
        if referentiel_files:
            print(f"📁 Trouvé {len(referentiel_files)} fichier(s) référentiel dans S3")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
                content = s3_service.read_csv_from_s3(referentiel_files[0])
                if content:
                    tmp.write(content)
                    tmp.flush()
                    raw_data["referentiel"] = tmp.name
    
    except Exception as e:
        print(f"⚠ Erreur chargement depuis S3: {e}")
        import traceback
        traceback.print_exc()
    
    return raw_data


def initialize_processors(config) -> Dict[str, Any]:
    """
    Initialise tous les processeurs
    
    Args:
        config: Configuration
    
    Returns:
        Dict des processeurs par type
    """
    return {
        "bikes": BikesProcessor(config),
        "traffic": TrafficProcessor(config),
        "weather": WeatherProcessor(config),
        "comptages": ComptagesProcessor(config),
        "chantiers": ChantiersProcessor(config),
        "referentiel": ReferentielProcessor(config)
    }


def enrich_multi_source(results: Dict, referentiel_data: Optional[Dict] = None) -> Dict:
    """
    Enrichit les résultats avec jointures multi-sources
    
    Args:
        results: Résultats de traitement
        referentiel_data: Données référentiel pour enrichissement
    
    Returns:
        Résultats enrichis
    """
    # Enrichir comptages avec référentiel
    # (Simplifié - dans un vrai projet, utiliser referentiel_data pour enrichir)
    if referentiel_data and "comptages" in results:
        # TODO: Utiliser referentiel_data pour enrichir les métriques comptages
        # avec libelles et métadonnées géographiques
        pass
    
    # Enrichir avec chantiers (intersection géographique)
    # (Simplifié - nécessiterait calcul intersections géographiques)
    
    return results


def cleanup_processed_chunks(config, keep_chunks=False):
    """
    Nettoie les fichiers chunks temporaires après traitement
    
    Args:
        config: Configuration
        keep_chunks: Si True, garde les chunks (pour debug)
    """
    if keep_chunks:
        return
    
    import glob
    import os
    
    chunk_files = glob.glob(str(config.PROCESSED_DIR / "*_chunk_*.csv"))
    
    if chunk_files:
        deleted_count = 0
        for chunk_file in chunk_files:
            try:
                os.remove(chunk_file)
                deleted_count += 1
            except Exception as e:
                print(f"  ⚠ Erreur suppression {chunk_file}: {e}")
        
        if deleted_count > 0:
            print(f"  ✓ {deleted_count} fichiers chunks nettoyés")


def export_results(results: Dict, config, date: Optional[str] = None) -> None:
    """
    Exporte les métriques calculées vers la base de données (MongoDB ou DynamoDB)
    
    Args:
        results: Résultats de traitement
        config: Configuration
        date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
    """
    # Déterminer la date
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Remplir la date dans toutes les métriques
    for data_type, result in results.items():
        if result and result.get("indicators"):
            indicators = result.get("indicators", {})
            # Remplir date dans les métriques individuelles
            if "metrics" in indicators and isinstance(indicators["metrics"], list):
                for metric in indicators["metrics"]:
                    # Vérifier que metric est bien un dict
                    if isinstance(metric, dict) and "date" in metric and metric["date"] == "":
                        metric["date"] = date
            
            # Remplir date dans les top 10 tronçons
            if "top_10_troncons" in indicators:
                for troncon in indicators["top_10_troncons"]:
                    if "date" in troncon and troncon["date"] == "":
                        troncon["date"] = date
            
            # Remplir date dans les top 10 zones congestionnées
            if "top_10_zones_congestionnees" in indicators:
                for zone in indicators["top_10_zones_congestionnees"]:
                    if "date" in zone and zone["date"] == "":
                        zone["date"] = date
                    # S'assurer que zone_fallback est présent
                    if "zone_fallback" not in zone or not zone.get("zone_fallback"):
                        arr = zone.get("arrondissement", "Unknown")
                        if arr != "Unknown":
                            zone["zone_fallback"] = f"Arrondissement {arr}"
                        else:
                            zone["zone_fallback"] = "Unknown"
            
            # Remplir date dans les alertes de congestion
            if "alertes_congestion" in indicators:
                for alerte in indicators["alertes_congestion"]:
                    if "date" in alerte and alerte["date"] == "":
                        alerte["date"] = date
    
    # Obtenir le service de base de données (MongoDB ou DynamoDB selon config)
    try:
        db_service = get_database_service()
        db_type = get_database_type()
    except Exception as e:
        print(f"\n✗ Erreur initialisation base de données: {e}")
        print("💡 Les métriques seront sauvegardées en local uniquement")
        db_service = None
        db_type = "local"
    
    # Exporter métriques par type
    exported_count = 0
    for data_type, result in results.items():
        if result and result.get("success"):
            indicators = result.get("indicators", {})
            if indicators:
                # Vérifier si optimisation nécessaire pour MongoDB
                if db_service and should_optimize_for_mongodb(data_type, indicators):
                    # Créer version optimisée pour MongoDB (sans liste complète des tronçons)
                    optimized_indicators = optimize_metrics_for_storage(data_type, indicators)
                    print(f"  ⚠ Métriques {data_type} optimisées pour stockage (taille réduite)")
                    print(f"     → Version complète disponible en fichier local uniquement")
                    
                    # Sauvegarder version optimisée dans la base de données
                    success = db_service.save_metrics(
                        metrics=optimized_indicators,
                        data_type=data_type,
                        date=date
                    )
                    if success:
                        exported_count += 1
                        print(f"✓ Métriques {data_type} (summary) exportées vers {db_type.upper()}")
                    else:
                        print(f"✗ Erreur export métriques {data_type} vers {db_type.upper()}")
                else:
                    # Sauvegarder version complète dans la base de données
                    if db_service:
                        success = db_service.save_metrics(
                            metrics=indicators,
                            data_type=data_type,
                            date=date
                        )
                        if success:
                            exported_count += 1
                            print(f"✓ Métriques {data_type} exportées vers {db_type.upper()}")
                        else:
                            print(f"✗ Erreur export métriques {data_type} vers {db_type.upper()}")
                
                # Toujours sauvegarder version complète en local (backup + référence)
                if not os.getenv("AWS_EXECUTION_ENV"):
                    from processors.utils.file_utils import save_json
                    output_path = config.METRICS_DIR / f"{data_type}_metrics_{date}.json"
                    save_json(indicators, str(output_path))
                    print(f"  → Sauvegarde locale (backup complet): {output_path}")
    
    # Fermer connexion MongoDB si applicable
    if db_service and hasattr(db_service, 'close'):
        db_service.close()
    
    # Nettoyer chunks temporaires après export réussi
    cleanup_processed_chunks(config, keep_chunks=False)
    
    print(f"\n✓ {exported_count} types de métriques exportés vers {db_type.upper()}")
    print("\n💡 Pour générer le rapport quotidien (instance séparée), exécutez:")
    print(f"   python report_generator/main.py {date}")


def main(date: Optional[str] = None):
    """
    Point d'entrée principal
    
    Args:
        date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
    """
    # Déterminer la date de traitement
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Valider le format de date
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"⚠ Format de date invalide: {date}, utilisation de la date d'aujourd'hui")
            date = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("CityFlow Analytics - Traitement des Données")
    print(f"Date: {date}")
    print("=" * 60)
    
    try:
        # 1. Chargement configuration
        print("\n[1/6] Chargement configuration...")
        config = settings
        print("✓ Configuration chargée")
        
        # 2. Initialisation processeurs
        print("\n[2/6] Initialisation processeurs...")
        processors = initialize_processors(config)
        print(f"✓ {len(processors)} processeurs initialisés")
        
        # 3. Chargement données brutes
        print("\n[3/6] Chargement données brutes...")
        raw_data = load_raw_data(config)
        
        data_loaded = sum(1 for v in raw_data.values() if v is not None)
        print(f"✓ {data_loaded} sources de données chargées")
        
        # 4. Traitement par type de données
        print("\n[4/6] Traitement des données...")
        results = {}
        
        # Traiter référentiel en premier (pour enrichissement)
        if raw_data.get("referentiel"):
            print("  → Traitement référentiel géographique...")
            results["referentiel"] = processors["referentiel"].process(raw_data["referentiel"])
        
        # Traiter autres données
        for data_type, processor in processors.items():
            if data_type == "referentiel":
                continue  # Déjà traité
            
            data = raw_data.get(data_type)
            if data is None:
                print(f"  ⚠ Pas de données pour {data_type}")
                continue
            
            print(f"  → Traitement {data_type}...")
            
            try:
                # Cas spécial pour comptages (gros fichier)
                if data_type == "comptages" and isinstance(data, str):
                    result = processors[data_type].process_large_file(data)
                else:
                    result = processor.process(data)
                
                results[data_type] = result
                print(f"    ✓ {data_type} traité avec succès")
            except Exception as e:
                print(f"    ✗ Erreur traitement {data_type}: {e}")
                results[data_type] = {"success": False, "errors": [str(e)]}
        
        # 5. Enrichissement multi-sources
        print("\n[5/6] Enrichissement multi-sources...")
        referentiel_data = results.get("referentiel")
        results = enrich_multi_source(results, referentiel_data)
        print("✓ Enrichissement terminé")
        
        # 6. Export résultats (métriques uniquement)
        print("\n[6/6] Export des métriques...")
        export_results(results, config, date=date)
        print("✓ Export terminé")
        
        print("\n" + "=" * 60)
        print("Traitement terminé avec succès!")
        print("=" * 60)
        db_type = get_database_type()
        print(f"\n📊 Métriques exportées dans {db_type.upper()}")
        print("📋 Pour générer le rapport (instance séparée), exécutez:")
        print("   python report_generator/main.py")
        print("=" * 60)
        
        return results
    
    except Exception as e:
        print(f"\n✗ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()

