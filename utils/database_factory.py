"""
Factory pour choisir automatiquement le service de base de données
selon l'environnement (MongoDB local ou Fichiers JSON sur EC2)
"""

import os
from utils.database_service import DatabaseService


def get_database_service() -> DatabaseService:
    """
    Factory qui retourne le service de base de données approprié
    selon l'environnement et la configuration
    
    Logique de sélection:
    1. Si pas de bucket local → EC2 → Fichiers JSON locaux
    2. Sinon → MongoDB (développement local)
    
    Note: Sur EC2, les données seront stockées en JSON puis chargées manuellement vers AWS
    
    Returns:
        Instance de DatabaseService (MongoDB ou LocalFileService)
    
    Raises:
        ImportError: Si la librairie requise n'est pas disponible
    """
    # DÉTECTION AUTOMATIQUE
    # Si pas de bucket local → on est sur EC2 → Fichiers JSON
    from pathlib import Path
    local_bucket = Path("bucket-cityflow-paris-s3-raw")
    
    if not local_bucket.exists():
        db_type = "local_files"
        print("🌐 Détection EC2 → utilisation Fichiers JSON locaux")
    else:
        db_type = "mongodb"
        print("💻 Détection Local → utilisation MongoDB")
    
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
            print("\n💡 Alternative: utiliser fichiers JSON locaux")
            print("   Supprimez le dossier bucket-cityflow-paris-s3-raw")
            raise
    
    elif db_type == "local_files":
        print("=" * 60)
        print("📁 Stockage: Fichiers JSON locaux (EC2)")
        print("=" * 60)
        
        try:
            from utils.local_file_service import LocalFileService
            return LocalFileService()
        except ImportError as e:
            print(f"✗ Erreur: {e}")
            raise
    
    else:
        raise ValueError(
            f"Type de base de données inconnu: {db_type}\n"
            f"Valeurs valides: 'mongodb', 'local_files'"
        )


def get_database_type() -> str:
    """
    Retourne le type de base de données configuré
    
    Returns:
        'mongodb' ou 'local_files'
    """
    from pathlib import Path
    local_bucket = Path("bucket-cityflow-paris-s3-raw")
    
    if not local_bucket.exists():
        return "local_files"
    else:
        return "mongodb"


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

