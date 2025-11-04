"""
Utilitaires pour optimiser les métriques avant stockage
Permet de créer des versions "summary" pour éviter les limites MongoDB (16 MB)
"""

from typing import Dict, Any
import json


def create_comptages_summary(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée une version summary des métriques comptages pour MongoDB
    Exclut la liste complète des tronçons (trop volumineuse)
    Garde uniquement les agrégations et top 10
    
    Args:
        indicators: Indicateurs complets des comptages
    
    Returns:
        Dict avec seulement les métriques agrégées (fits dans MongoDB)
    """
    # Extraire seulement les métriques importantes
    summary = {
        # Métriques globales (essentielles)
        "global_metrics": indicators.get("global_metrics", {}),
        
        # Top 10 (petit, essentiel pour les rapports)
        "top_10_troncons": indicators.get("top_10_troncons", [])[:10],
        "top_10_zones_congestionnees": indicators.get("top_10_zones_congestionnees", [])[:10],
        
        # Alertes (limitées à 20)
        "alertes_congestion": indicators.get("alertes_congestion", [])[:20],
        
        # Métadonnées
        "total_troncons": len(indicators.get("metrics", [])),
        "note": "Liste complète des tronçons disponible dans fichier local uniquement"
    }
    
    return summary


def estimate_document_size(data: Dict[str, Any]) -> int:
    """
    Estime la taille approximative d'un document en bytes
    
    Args:
        data: Document à estimer
    
    Returns:
        Taille estimée en bytes
    """
    try:
        json_str = json.dumps(data, default=str)
        return len(json_str.encode('utf-8'))
    except Exception:
        return 0


def should_optimize_for_mongodb(data_type: str, indicators: Dict[str, Any], size_limit_mb: float = 15.0) -> bool:
    """
    Détermine si les métriques doivent être optimisées pour MongoDB
    
    Args:
        data_type: Type de données
        indicators: Indicateurs à vérifier
        size_limit_mb: Limite en MB (défaut: 15 MB pour marge sécurité)
    
    Returns:
        True si optimisation nécessaire
    """
    # Toujours optimiser les comptages (connu pour être volumineux)
    if data_type == "comptages":
        return True
    
    # Vérifier la taille pour les autres types
    size_bytes = estimate_document_size(indicators)
    size_mb = size_bytes / (1024 * 1024)
    
    return size_mb > size_limit_mb


def optimize_metrics_for_storage(data_type: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimise les métriques selon le type de données et les limites de stockage
    
    Args:
        data_type: Type de données
        indicators: Indicateurs complets
    
    Returns:
        Métriques optimisées pour stockage
    """
    if data_type == "comptages":
        return create_comptages_summary(indicators)
    
    # Pour les autres types, retourner tel quel (pas d'optimisation nécessaire)
    return indicators

