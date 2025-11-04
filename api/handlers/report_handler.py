"""
Handler pour les endpoints de rapports quotidiens
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.database_factory import get_database_service


def get_report(date: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le rapport quotidien pour une date
    
    Args:
        date: Date au format YYYY-MM-DD
    
    Returns:
        Rapport ou None si non trouvé
    """
    try:
        # Obtenir le service de base de données (MongoDB ou DynamoDB selon config)
        db_service = get_database_service()
        
        # Charger le rapport
        report = db_service.load_report(date)
        
        # Fermer la connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return report
    
    except Exception as e:
        print(f"Erreur get_report({date}): {e}")
        raise


def get_latest_report() -> Optional[Dict[str, Any]]:
    """
    Récupère le dernier rapport disponible
    
    Returns:
        Dernier rapport ou None
    """
    from datetime import datetime, timedelta
    
    # Essayer les 7 derniers jours
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        report = get_report(date)
        if report:
            return report
    
    return None

