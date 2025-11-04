"""
Module de chargement des données pour le dashboard
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_metrics(metric_type: str, date: str, source: str) -> Optional[Dict[str, Any]]:
    """
    Charge les métriques depuis la source spécifiée
    
    Args:
        metric_type: Type de métrique (bikes, traffic, weather, comptages, chantiers, referentiel)
        date: Date au format YYYY-MM-DD
        source: Source de données (MongoDB Local, Fichiers JSON, API)
    
    Returns:
        Dict avec les métriques ou None
    """
    if source == "MongoDB Local":
        return load_from_mongodb(metric_type, date)
    elif source == "Fichiers JSON":
        return load_from_json(metric_type, date)
    elif source == "API":
        return load_from_api(metric_type, date)
    else:
        return None


def load_all_metrics(date: str, source: str) -> Dict[str, Any]:
    """
    Charge toutes les métriques pour une date donnée
    
    Args:
        date: Date au format YYYY-MM-DD
        source: Source de données
    
    Returns:
        Dict avec toutes les métriques
    """
    metrics = {}
    
    for metric_type in ["bikes", "traffic", "weather", "comptages", "chantiers", "referentiel"]:
        data = load_metrics(metric_type, date, source)
        if data:
            metrics[metric_type] = data
    
    return metrics


def load_report(date: str, source: str) -> Optional[Dict[str, Any]]:
    """
    Charge le rapport quotidien
    
    Args:
        date: Date au format YYYY-MM-DD
        source: Source de données
    
    Returns:
        Dict avec le rapport ou None
    """
    if source == "MongoDB Local":
        return load_report_from_mongodb(date)
    elif source == "Fichiers JSON":
        return load_report_from_json(date)
    elif source == "API":
        return load_report_from_api(date)
    else:
        return None


def load_from_json(metric_type: str, date: str) -> Optional[Dict[str, Any]]:
    """Charge depuis fichiers JSON locaux"""
    try:
        # Construire le chemin du fichier
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / "output" / "metrics" / f"{metric_type}_metrics_{date}.json"
        
        if not file_path.exists():
            print(f"❌ Fichier non trouvé: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Les fichiers JSON contiennent directement les indicators
        # Pas besoin de transformation supplémentaire
        print(f"✅ Chargé {metric_type} depuis JSON: {list(data.keys())[:5]}")
        return data
    except Exception as e:
        print(f"❌ Erreur lors du chargement de {metric_type}: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_from_mongodb(metric_type: str, date: str) -> Optional[Dict[str, Any]]:
    """Charge depuis MongoDB"""
    try:
        from utils.mongodb_service import MongoDBService
        
        db_service = MongoDBService()
        data = db_service.load_metrics(metric_type, date)
        db_service.close()
        
        return data
    except Exception as e:
        print(f"Erreur MongoDB pour {metric_type}: {e}")
        # Fallback vers fichiers JSON
        return load_from_json(metric_type, date)


def load_from_api(metric_type: str, date: str) -> Optional[Dict[str, Any]]:
    """Charge depuis l'API"""
    try:
        import requests
        
        api_port = os.getenv("API_PORT", "5001")
        response = requests.get(f"http://localhost:{api_port}/metrics/{metric_type}/{date}")
        
        if response.status_code == 200:
            return response.json().get("data")
        else:
            return None
    except Exception as e:
        print(f"Erreur API pour {metric_type}: {e}")
        # Fallback vers fichiers JSON
        return load_from_json(metric_type, date)


def load_report_from_json(date: str) -> Optional[Dict[str, Any]]:
    """Charge le rapport depuis fichiers JSON"""
    try:
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / "output" / "reports" / f"daily_report_{date}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        print(f"Erreur lors du chargement du rapport: {e}")
        return None


def load_report_from_mongodb(date: str) -> Optional[Dict[str, Any]]:
    """Charge le rapport depuis MongoDB"""
    try:
        from utils.mongodb_service import MongoDBService
        
        db_service = MongoDBService()
        data = db_service.load_report(date)
        db_service.close()
        
        return data
    except Exception as e:
        print(f"Erreur MongoDB pour le rapport: {e}")
        return load_report_from_json(date)


def load_report_from_api(date: str) -> Optional[Dict[str, Any]]:
    """Charge le rapport depuis l'API"""
    try:
        import requests
        
        api_port = os.getenv("API_PORT", "5001")
        response = requests.get(f"http://localhost:{api_port}/report/{date}")
        
        if response.status_code == 200:
            return response.json().get("data")
        else:
            return None
    except Exception as e:
        print(f"Erreur API pour le rapport: {e}")
        return load_report_from_json(date)

