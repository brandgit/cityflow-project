"""
Handler AWS Lambda pour l'API REST CityFlow Analytics
Point d'entrée pour API Gateway → Lambda

Endpoints:
  GET /metrics/{type}/{date}      - Récupère les métriques d'un type
  GET /metrics/{date}             - Récupère toutes les métriques d'une date
  GET /report/{date}              - Récupère le rapport quotidien
  GET /health                     - Health check
  GET /stats                      - Statistiques globales
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au PYTHONPATH pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.utils.response import create_response, create_error_response
from api.utils.validation import validate_date, validate_metric_type
from api.handlers.metrics_handler import get_metrics, get_all_metrics
from api.handlers.report_handler import get_report
from api.handlers.stats_handler import get_stats


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal AWS Lambda
    
    Args:
        event: Événement API Gateway
        context: Contexte Lambda
    
    Returns:
        Réponse HTTP formatée pour API Gateway
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Extraire méthode HTTP et chemin
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_parameters = event.get("pathParameters", {}) or {}
        query_parameters = event.get("queryStringParameters", {}) or {}
        
        # Router selon le chemin
        if path == "/health" or path == "/api/health":
            return handle_health_check()
        
        elif path == "/stats" or path == "/api/stats":
            return handle_stats()
        
        elif "/metrics/" in path:
            return handle_metrics_request(path_parameters, query_parameters)
        
        elif "/report/" in path:
            return handle_report_request(path_parameters, query_parameters)
        
        else:
            return create_error_response(
                404,
                "Endpoint non trouvé",
                f"Chemin invalide: {path}"
            )
    
    except Exception as e:
        print(f"Erreur Lambda: {e}")
        import traceback
        traceback.print_exc()
        
        return create_error_response(
            500,
            "Erreur interne du serveur",
            str(e)
        )


def handle_health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    from utils.database_factory import get_database_type
    
    return create_response(200, {
        "status": "healthy",
        "service": "CityFlow Analytics API",
        "version": "1.0.0",
        "database": get_database_type(),
        "environment": "AWS" if os.getenv("AWS_EXECUTION_ENV") else "Local"
    })


def handle_stats() -> Dict[str, Any]:
    """Statistiques globales"""
    try:
        stats = get_stats()
        return create_response(200, stats)
    except Exception as e:
        return create_error_response(500, "Erreur récupération statistiques", str(e))


def handle_metrics_request(path_params: Dict, query_params: Dict) -> Dict[str, Any]:
    """
    Gère les requêtes /metrics/*
    
    Routes:
      /metrics/{type}/{date}  - Métriques d'un type spécifique
      /metrics/{date}         - Toutes les métriques d'une date
    """
    metric_type = path_params.get("type")
    date = path_params.get("date")
    
    # Validation date
    if date and not validate_date(date):
        return create_error_response(400, "Format de date invalide", "Format attendu: YYYY-MM-DD")
    
    # Route : /metrics/{type}/{date}
    if metric_type and date:
        # Valider type
        if not validate_metric_type(metric_type):
            return create_error_response(
                400,
                "Type de métrique invalide",
                f"Types valides: bikes, traffic, weather, comptages, chantiers, referentiel"
            )
        
        try:
            metrics = get_metrics(metric_type, date)
            
            if metrics is None:
                return create_error_response(
                    404,
                    "Métriques non trouvées",
                    f"Aucune métrique {metric_type} pour la date {date}"
                )
            
            return create_response(200, {
                "metric_type": metric_type,
                "date": date,
                "data": metrics
            })
        except Exception as e:
            return create_error_response(500, "Erreur récupération métriques", str(e))
    
    # Route : /metrics/{date}
    elif date:
        try:
            all_metrics = get_all_metrics(date)
            return create_response(200, {
                "date": date,
                "metrics": all_metrics
            })
        except Exception as e:
            return create_error_response(500, "Erreur récupération métriques", str(e))
    
    else:
        return create_error_response(400, "Paramètres manquants", "Date requise")


def handle_report_request(path_params: Dict, query_params: Dict) -> Dict[str, Any]:
    """
    Gère les requêtes /report/{date}
    """
    date = path_params.get("date")
    
    if not date:
        return create_error_response(400, "Date manquante", "Format: /report/{YYYY-MM-DD}")
    
    if not validate_date(date):
        return create_error_response(400, "Format de date invalide", "Format attendu: YYYY-MM-DD")
    
    try:
        report = get_report(date)
        
        if report is None:
            return create_error_response(
                404,
                "Rapport non trouvé",
                f"Aucun rapport pour la date {date}"
            )
        
        return create_response(200, {
            "date": date,
            "report": report
        })
    except Exception as e:
        return create_error_response(500, "Erreur récupération rapport", str(e))


# Alias pour compatibilité
handler = lambda_handler

