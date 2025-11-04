"""
Factory pour choisir automatiquement le service de base de données
selon l'environnement (MongoDB local ou DynamoDB production)
"""

import os
from utils.database_service import DatabaseService


def get_database_service() -> DatabaseService:
    """
    Factory qui retourne le service de base de données approprié
    selon l'environnement et la configuration
    
    Logique de sélection:
    1. Si AWS_EXECUTION_ENV existe → DynamoDB (Lambda/EC2)
    2. Si DATABASE_TYPE=dynamodb → DynamoDB
    3. Sinon → MongoDB (développement local)
    
    Returns:
        Instance de DatabaseService (MongoDB ou DynamoDB)
    
    Raises:
        ImportError: Si la librairie requise n'est pas disponible
        ValueError: Si DATABASE_TYPE est invalide
    """
    # Vérifier variable d'environnement DATABASE_TYPE
    db_type = os.getenv("DATABASE_TYPE", "mongodb").lower()
    
    # En production AWS, forcer DynamoDB
    if os.getenv("AWS_EXECUTION_ENV"):
        db_type = "dynamodb"
        print("🌐 Environnement AWS détecté → utilisation DynamoDB")
    
    # Forcer DynamoDB si USE_DYNAMODB=true
    if os.getenv("USE_DYNAMODB", "false").lower() == "true":
        db_type = "dynamodb"
    
    # Instancier le service approprié
    if db_type == "mongodb":
        print("=" * 60)
        print("📦 Base de données: MongoDB (développement local)")
        print("=" * 60)
        
        try:
            from utils.mongodb_service import MongoDBService
            return MongoDBService()
        except ImportError as e:
            print(f"✗ Erreur: {e}")
            print("\n💡 Pour utiliser MongoDB, installer pymongo:")
            print("   pip install pymongo")
            print("\n💡 Ou basculer vers DynamoDB:")
            print("   DATABASE_TYPE=dynamodb dans .env")
            raise
    
    elif db_type == "dynamodb":
        print("=" * 60)
        print("☁️  Base de données: DynamoDB (production AWS)")
        print("=" * 60)
        
        try:
            from utils.dynamodb_service_adapter import DynamoDBServiceAdapter
            return DynamoDBServiceAdapter()
        except ImportError as e:
            print(f"✗ Erreur: {e}")
            print("\n💡 Pour utiliser DynamoDB, installer boto3:")
            print("   pip install boto3")
            raise
    
    else:
        raise ValueError(
            f"Type de base de données inconnu: {db_type}\n"
            f"Valeurs valides: 'mongodb', 'dynamodb'\n"
            f"Configurez DATABASE_TYPE dans .env"
        )


def get_database_type() -> str:
    """
    Retourne le type de base de données configuré
    
    Returns:
        'mongodb' ou 'dynamodb'
    """
    db_type = os.getenv("DATABASE_TYPE", "mongodb").lower()
    
    if os.getenv("AWS_EXECUTION_ENV") or os.getenv("USE_DYNAMODB", "false").lower() == "true":
        db_type = "dynamodb"
    
    return db_type


def test_database_connection() -> bool:
    """
    Teste la connexion à la base de données configurée
    
    Returns:
        True si la connexion fonctionne
    """
    try:
        db_service = get_database_service()
        print("✓ Connexion à la base de données OK")
        
        # Fermer la connexion si MongoDB
        if hasattr(db_service, 'close'):
            db_service.close()
        
        return True
    except Exception as e:
        print(f"✗ Erreur connexion base de données: {e}")
        return False

