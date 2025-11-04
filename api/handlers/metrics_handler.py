"""
Handler pour les endpoints de métriques
Gère MongoDB (local) et DynamoDB (AWS) automatiquement
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.database_factory import get_database_service, get_database_type


def get_metrics(metric_type: str, date: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les métriques d'un type spécifique pour une date
    
    Args:
        metric_type: Type de métrique (bikes, traffic, weather, etc.)
        date: Date au format YYYY-MM-DD
    
    Returns:
        Métriques ou None si non trouvées
    """
    try:
        # Obtenir le service de base de données (MongoDB ou DynamoDB selon config)
        db_service = get_database_service()
        
        # Charger les métriques
        metrics = db_service.load_metrics(
            data_type=metric_type,
            date=date
        )
        
        # Fermer la connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return metrics
    
    except Exception as e:
        print(f"Erreur get_metrics({metric_type}, {date}): {e}")
        raise


def get_all_metrics(date: str) -> Dict[str, Any]:
    """
    Récupère toutes les métriques pour une date
    
    Args:
        date: Date au format YYYY-MM-DD
    
    Returns:
        Dict avec toutes les métriques par type
    """
    metric_types = ["bikes", "traffic", "weather", "comptages", "chantiers", "referentiel"]
    
    all_metrics = {}
    
    try:
        db_service = get_database_service()
        
        for metric_type in metric_types:
            try:
                metrics = db_service.load_metrics(
                    data_type=metric_type,
                    date=date
                )
                
                if metrics:
                    all_metrics[metric_type] = metrics
            except Exception as e:
                print(f"Erreur chargement {metric_type}: {e}")
                all_metrics[metric_type] = None
        
        # Fermer la connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return all_metrics
    
    except Exception as e:
        print(f"Erreur get_all_metrics({date}): {e}")
        raise


def query_metrics_range(metric_type: str, 
                       start_date: str, 
                       end_date: str) -> List[Dict[str, Any]]:
    """
    Récupère les métriques sur une plage de dates
    
    Args:
        metric_type: Type de métrique
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
    
    Returns:
        Liste des métriques
    """
    try:
        db_service = get_database_service()
        
        metrics_list = db_service.query_metrics_by_date_range(
            data_type=metric_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # Fermer la connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return metrics_list
    
    except Exception as e:
        print(f"Erreur query_metrics_range({metric_type}, {start_date}, {end_date}): {e}")
        raise

