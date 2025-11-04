"""
Utilitaires pour formater les réponses HTTP
Compatible AWS Lambda API Gateway
"""

import json
from typing import Dict, Any, Optional


def create_response(status_code: int, 
                   body: Any, 
                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Crée une réponse HTTP formatée pour API Gateway
    
    Args:
        status_code: Code HTTP (200, 404, 500, etc.)
        body: Corps de la réponse (dict, list, etc.)
        headers: En-têtes HTTP additionnels
    
    Returns:
        Réponse formatée pour API Gateway
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # CORS
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }


def create_error_response(status_code: int, 
                         error: str, 
                         message: str = "",
                         details: Any = None) -> Dict[str, Any]:
    """
    Crée une réponse d'erreur formatée
    
    Args:
        status_code: Code HTTP d'erreur
        error: Message d'erreur court
        message: Description détaillée
        details: Détails additionnels
    
    Returns:
        Réponse d'erreur formatée
    """
    error_body = {
        "error": error,
        "message": message,
        "statusCode": status_code
    }
    
    if details:
        error_body["details"] = details
    
    return create_response(status_code, error_body)


def create_success_response(data: Any, message: str = "Succès") -> Dict[str, Any]:
    """
    Crée une réponse de succès formatée
    
    Args:
        data: Données à retourner
        message: Message de succès
    
    Returns:
        Réponse de succès formatée
    """
    return create_response(200, {
        "success": True,
        "message": message,
        "data": data
    })

