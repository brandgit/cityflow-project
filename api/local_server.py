#!/usr/bin/env python3
"""
Serveur local pour développement de l'API CityFlow
Simule API Gateway + Lambda en local avec Flask

Usage:
    python3 api/local_server.py
    
    # Ou avec un port personnalisé
    API_PORT=8080 python3 api/local_server.py
    
Puis tester :
    curl http://localhost:5001/health  # Port par défaut 5001 (évite conflit AirPlay)
    curl http://localhost:5001/metrics/bikes/2025-11-03
"""

import sys
import os
import socket
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠ Flask non disponible. Installer avec: pip install flask flask-cors")
    sys.exit(1)


def find_free_port(start_port=5001, max_attempts=10):
    """
    Trouve un port libre en commençant par start_port
    
    Args:
        start_port: Port de départ
        max_attempts: Nombre maximum de tentatives
    
    Returns:
        Numéro de port libre
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Aucun port libre trouvé entre {start_port} et {start_port + max_attempts - 1}")

from api.lambda_function import (
    handle_health_check,
    handle_stats,
    handle_metrics_request,
    handle_report_request
)


# Créer l'application Flask
app = Flask(__name__)
CORS(app)  # Activer CORS pour développement


def simulate_lambda_event(path: str, path_params: dict = None, query_params: dict = None) -> dict:
    """
    Simule un événement API Gateway pour Lambda
    
    Args:
        path: Chemin de la requête
        path_params: Paramètres de chemin
        query_params: Paramètres de requête
    
    Returns:
        Event dict formaté pour Lambda
    """
    return {
        "httpMethod": request.method,
        "path": path,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params or {},
        "headers": dict(request.headers)
    }


def lambda_response_to_flask(lambda_response: dict):
    """
    Convertit une réponse Lambda en réponse Flask
    
    Args:
        lambda_response: Réponse formatée Lambda
    
    Returns:
        Réponse Flask
    """
    import json
    
    body = lambda_response.get("body", "{}")
    status_code = lambda_response.get("statusCode", 200)
    
    # Parser le body si c'est une string JSON
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            pass
    
    response = jsonify(body)
    response.status_code = status_code
    
    # Ajouter les headers
    headers = lambda_response.get("headers", {})
    for key, value in headers.items():
        response.headers[key] = value
    
    return response


# ============================================================
# Routes API
# ============================================================

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    lambda_response = handle_health_check()
    return lambda_response_to_flask(lambda_response)


@app.route('/stats', methods=['GET'])
@app.route('/api/stats', methods=['GET'])
def stats():
    """Statistiques globales"""
    lambda_response = handle_stats()
    return lambda_response_to_flask(lambda_response)


@app.route('/metrics/<metric_type>/<date>', methods=['GET'])
@app.route('/api/metrics/<metric_type>/<date>', methods=['GET'])
def get_specific_metrics(metric_type: str, date: str):
    """Métriques d'un type spécifique"""
    path_params = {"type": metric_type, "date": date}
    query_params = dict(request.args)
    
    lambda_response = handle_metrics_request(path_params, query_params)
    return lambda_response_to_flask(lambda_response)


@app.route('/metrics/<date>', methods=['GET'])
@app.route('/api/metrics/<date>', methods=['GET'])
def get_all_metrics_for_date(date: str):
    """Toutes les métriques d'une date"""
    path_params = {"date": date}
    query_params = dict(request.args)
    
    lambda_response = handle_metrics_request(path_params, query_params)
    return lambda_response_to_flask(lambda_response)


@app.route('/report/<date>', methods=['GET'])
@app.route('/api/report/<date>', methods=['GET'])
def get_daily_report(date: str):
    """Rapport quotidien"""
    path_params = {"date": date}
    query_params = dict(request.args)
    
    lambda_response = handle_report_request(path_params, query_params)
    return lambda_response_to_flask(lambda_response)


@app.route('/', methods=['GET'])
def index():
    """Page d'accueil de l'API"""
    return jsonify({
        "service": "CityFlow Analytics API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "stats": "/stats",
            "metrics": {
                "specific": "/metrics/{type}/{date}",
                "all": "/metrics/{date}"
            },
            "report": "/report/{date}"
        },
        "examples": {
            "bikes": "http://localhost:5000/metrics/bikes/2025-11-03",
            "all_metrics": "http://localhost:5000/metrics/2025-11-03",
            "report": "http://localhost:5000/report/2025-11-03"
        }
    })


@app.route('/docs', methods=['GET'])
def docs():
    """Documentation de l'API"""
    return jsonify({
        "title": "CityFlow Analytics API Documentation",
        "version": "1.0.0",
        "base_url_local": "http://localhost:5000",
        "base_url_aws": "https://your-api-id.execute-api.eu-west-3.amazonaws.com/prod",
        "endpoints": [
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check de l'API",
                "response": {"status": "healthy", "service": "CityFlow Analytics API"}
            },
            {
                "path": "/stats",
                "method": "GET",
                "description": "Statistiques globales",
                "response": {"api_version": "1.0.0", "database_type": "mongodb"}
            },
            {
                "path": "/metrics/{type}/{date}",
                "method": "GET",
                "description": "Métriques d'un type spécifique",
                "parameters": {
                    "type": "bikes|traffic|weather|comptages|chantiers|referentiel",
                    "date": "YYYY-MM-DD"
                },
                "example": "/metrics/bikes/2025-11-03"
            },
            {
                "path": "/metrics/{date}",
                "method": "GET",
                "description": "Toutes les métriques d'une date",
                "parameters": {
                    "date": "YYYY-MM-DD"
                },
                "example": "/metrics/2025-11-03"
            },
            {
                "path": "/report/{date}",
                "method": "GET",
                "description": "Rapport quotidien complet",
                "parameters": {
                    "date": "YYYY-MM-DD"
                },
                "example": "/report/2025-11-03"
            }
        ]
    })


# ============================================================
# Démarrage du serveur
# ============================================================

def main():
    """Point d'entrée principal du serveur local"""
    # Déterminer le port à utiliser
    # 1. Variable d'environnement API_PORT
    # 2. Port par défaut 5001 (évite conflit avec AirPlay sur macOS)
    # 3. Si 5001 occupé, trouver un port libre
    default_port = int(os.getenv("API_PORT", "5001"))
    
    try:
        # Vérifier si le port est libre
        port = default_port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
    except OSError:
        # Port occupé, trouver un port libre
        print(f"⚠ Port {default_port} occupé, recherche d'un port libre...")
        port = find_free_port(start_port=5001)
        print(f"✅ Port libre trouvé: {port}")
    
    print("=" * 70)
    print("  🚀 CityFlow Analytics API - Serveur Local")
    print("=" * 70)
    print()
    print(f"📍 URL: http://localhost:{port}")
    print(f"📖 Documentation: http://localhost:{port}/docs")
    print()
    print("🔗 Endpoints disponibles:")
    print("   - GET /health                        → Health check")
    print("   - GET /stats                         → Statistiques")
    print("   - GET /metrics/{type}/{date}         → Métriques spécifiques")
    print("   - GET /metrics/{date}                → Toutes les métriques")
    print("   - GET /report/{date}                 → Rapport quotidien")
    print()
    print("💡 Exemples:")
    print(f"   curl http://localhost:{port}/health")
    print(f"   curl http://localhost:{port}/metrics/bikes/2025-11-03")
    print(f"   curl http://localhost:{port}/report/2025-11-03")
    print()
    if port != default_port:
        print(f"💡 Note: Port {default_port} était occupé, utilisation du port {port}")
        print("   Pour forcer un port spécifique: export API_PORT=8080")
        print()
    print("=" * 70)
    print()
    
    # Démarrer le serveur Flask
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )


if __name__ == "__main__":
    if not FLASK_AVAILABLE:
        print("❌ Flask requis pour le serveur local")
        print("\n💡 Installation:")
        print("   pip install flask flask-cors")
        sys.exit(1)
    
    main()

