"""
Implémentation MongoDB pour le développement local
Permet de stocker métriques et rapports dans MongoDB Compass
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("⚠ pymongo non disponible - installer avec: pip install pymongo")

from utils.database_service import DatabaseService


class MongoDBService(DatabaseService):
    """Implémentation MongoDB pour développement local"""
    
    def __init__(self):
        """Initialise la connexion MongoDB"""
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo requis pour MongoDB. Installer avec: pip install pymongo")
        
        # URL depuis .env ou local par défaut
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
        database_name = os.getenv("MONGODB_DATABASE", "cityflow")
        
        try:
            self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Test de connexion
            self.client.admin.command('ping')
            
            self.db = self.client[database_name]
            
            # Collections
            self.metrics_collection = self.db["metrics"]
            self.reports_collection = self.db["reports"]
            
            # Créer des index pour optimiser les requêtes
            self.metrics_collection.create_index([("metric_type", 1), ("date", 1)], unique=True)
            self.metrics_collection.create_index([("date", 1)])
            self.reports_collection.create_index([("date", 1)], unique=True)
            
            print(f"✓ Connecté à MongoDB: {mongo_url} / {database_name}")
        except ConnectionFailure as e:
            print(f"✗ Erreur connexion MongoDB: {e}")
            print("💡 Assurez-vous que MongoDB est démarré (mongod)")
            raise
        except Exception as e:
            print(f"✗ Erreur initialisation MongoDB: {e}")
            raise
    
    def save_metrics(self, metrics: Dict[str, Any], data_type: str, date: str) -> bool:
        """
        Sauvegarde des métriques dans MongoDB
        
        Args:
            metrics: Métriques à sauvegarder
            data_type: Type de données (bikes, traffic, weather, etc.)
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        try:
            document = {
                "metric_type": data_type,
                "date": date,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Upsert: remplace si existe déjà (même metric_type + date)
            result = self.metrics_collection.update_one(
                {"metric_type": data_type, "date": date},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"  ✓ Nouvelles métriques {data_type} insérées (ID: {result.upserted_id})")
            else:
                print(f"  ✓ Métriques {data_type} mises à jour")
            
            return True
        except OperationFailure as e:
            print(f"✗ Erreur MongoDB save_metrics (opération): {e}")
            return False
        except Exception as e:
            print(f"✗ Erreur MongoDB save_metrics: {e}")
            return False
    
    def load_metrics(self, data_type: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge des métriques depuis MongoDB
        
        Args:
            data_type: Type de données
            date: Date au format YYYY-MM-DD
        
        Returns:
            Métriques ou None si non trouvées
        """
        try:
            doc = self.metrics_collection.find_one({
                "metric_type": data_type,
                "date": date
            })
            
            if doc:
                return doc.get("metrics")
            return None
        except Exception as e:
            print(f"✗ Erreur MongoDB load_metrics: {e}")
            return None
    
    def save_report(self, report: Dict[str, Any], date: str) -> bool:
        """
        Sauvegarde un rapport dans MongoDB
        
        Args:
            report: Rapport à sauvegarder
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        try:
            document = {
                "report_id": f"daily_report_{date}",
                "date": date,
                "timestamp": datetime.now().isoformat(),
                "report": report,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # Upsert: remplace si existe déjà (même date)
            result = self.reports_collection.update_one(
                {"date": date},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"  ✓ Nouveau rapport inséré (ID: {result.upserted_id})")
            else:
                print(f"  ✓ Rapport mis à jour")
            
            return True
        except OperationFailure as e:
            print(f"✗ Erreur MongoDB save_report (opération): {e}")
            return False
        except Exception as e:
            print(f"✗ Erreur MongoDB save_report: {e}")
            return False
    
    def load_report(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge un rapport depuis MongoDB
        
        Args:
            date: Date au format YYYY-MM-DD
        
        Returns:
            Rapport ou None si non trouvé
        """
        try:
            doc = self.reports_collection.find_one({"date": date})
            if doc:
                return doc.get("report")
            return None
        except Exception as e:
            print(f"✗ Erreur MongoDB load_report: {e}")
            return None
    
    def query_metrics_by_date_range(self, data_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Interroge les métriques sur une plage de dates
        
        Args:
            data_type: Type de données
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
        
        Returns:
            Liste des métriques
        """
        try:
            cursor = self.metrics_collection.find({
                "metric_type": data_type,
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", 1)
            
            results = []
            for doc in cursor:
                results.append({
                    "date": doc.get("date"),
                    "metrics": doc.get("metrics")
                })
            
            return results
        except Exception as e:
            print(f"✗ Erreur MongoDB query_metrics_by_date_range: {e}")
            return []
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
            print("✓ Connexion MongoDB fermée")
    
    def __enter__(self):
        """Support du context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support du context manager"""
        self.close()

