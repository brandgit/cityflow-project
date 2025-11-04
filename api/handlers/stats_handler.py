"""
Handler pour les statistiques globales
"""

import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.database_factory import get_database_service, get_database_type


def get_stats() -> Dict[str, Any]:
    """
    Récupère les statistiques globales de l'API
    
    Returns:
        Dict avec statistiques
    """
    try:
        db_type = get_database_type()
        db_service = get_database_service()
        
        # Statistiques basiques
        stats = {
            "api_version": "1.0.0",
            "database_type": db_type,
            "environment": "AWS" if db_type == "dynamodb" else "Local",
            "timestamp": datetime.now().isoformat(),
            "metric_types_available": [
                "bikes",
                "traffic",
                "weather",
                "comptages",
                "chantiers",
                "referentiel"
            ]
        }
        
        # Si MongoDB, ajouter statistiques de la BDD
        if hasattr(db_service, 'client'):
            try:
                # Compter les documents dans chaque collection
                stats["database_stats"] = {
                    "metrics_count": db_service.metrics_collection.count_documents({}),
                    "reports_count": db_service.reports_collection.count_documents({})
                }
            except Exception as e:
                print(f"Erreur stats MongoDB: {e}")
        
        # Fermer connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return stats
    
    except Exception as e:
        print(f"Erreur get_stats(): {e}")
        raise

