"""
Adaptateur pour utiliser DynamoDB via l'interface DatabaseService commune
Permet de réutiliser le code existant dans aws_services.py
"""

import os
from typing import Dict, Any, Optional, List

from utils.database_service import DatabaseService
from utils.aws_services import (
    save_metrics_to_dynamodb,
    save_report_to_dynamodb,
    load_metrics_from_dynamodb,
    DynamoDBService
)


class DynamoDBServiceAdapter(DatabaseService):
    """Adaptateur pour utiliser DynamoDB via l'interface commune"""
    
    def __init__(self):
        """Initialise l'adaptateur DynamoDB"""
        self.metrics_table = os.getenv("DYNAMODB_METRICS_TABLE", "cityflow-metrics")
        self.reports_table = os.getenv("DYNAMODB_REPORTS_TABLE", "cityflow-daily-reports")
        
        # Tester la connexion
        try:
            service = DynamoDBService(self.metrics_table)
            if service.table:
                print(f"✓ Connecté à DynamoDB: {self.metrics_table}")
            else:
                print("⚠ Mode simulation DynamoDB (boto3 non disponible)")
        except Exception as e:
            print(f"⚠ Erreur test connexion DynamoDB: {e}")
    
    def save_metrics(self, metrics: Dict[str, Any], data_type: str, date: str) -> bool:
        """
        Sauvegarde des métriques dans DynamoDB
        
        Args:
            metrics: Métriques à sauvegarder
            data_type: Type de données (bikes, traffic, weather, etc.)
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        return save_metrics_to_dynamodb(
            metrics=metrics,
            data_type=data_type,
            date=date,
            table_name=self.metrics_table
        )
    
    def load_metrics(self, data_type: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge des métriques depuis DynamoDB
        
        Args:
            data_type: Type de données
            date: Date au format YYYY-MM-DD
        
        Returns:
            Métriques ou None si non trouvées
        """
        return load_metrics_from_dynamodb(
            data_type=data_type,
            date=date,
            table_name=self.metrics_table
        )
    
    def save_report(self, report: Dict[str, Any], date: str) -> bool:
        """
        Sauvegarde un rapport dans DynamoDB
        
        Args:
            report: Rapport à sauvegarder
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        return save_report_to_dynamodb(
            report=report,
            date=date,
            table_name=self.reports_table
        )
    
    def load_report(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge un rapport depuis DynamoDB
        
        Args:
            date: Date au format YYYY-MM-DD
        
        Returns:
            Rapport ou None si non trouvé
        """
        service = DynamoDBService(self.reports_table)
        item = service.get_item({"report_id": f"daily_report_{date}", "date": date})
        
        if item:
            return item.get("report")
        return None
    
    def query_metrics_by_date_range(self, data_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Interroge les métriques sur une plage de dates dans DynamoDB
        
        Args:
            data_type: Type de données
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
        
        Returns:
            Liste des métriques
        """
        service = DynamoDBService(self.metrics_table)
        
        if not service.table:
            print("[SIMULATION] DynamoDB.query_metrics_by_date_range")
            return []
        
        try:
            from boto3.dynamodb.conditions import Key, Attr
            
            # Scan avec filtre (pas optimal mais fonctionne)
            # En production, utiliser un GSI avec date comme partition key
            response = service.table.scan(
                FilterExpression=Attr("metric_type").eq(data_type) & 
                                Attr("date").between(start_date, end_date)
            )
            
            results = []
            for item in response.get("Items", []):
                results.append({
                    "date": item.get("date"),
                    "metrics": item.get("metrics")
                })
            
            # Trier par date
            results.sort(key=lambda x: x.get("date", ""))
            
            return results
        except Exception as e:
            print(f"✗ Erreur DynamoDB query_metrics_by_date_range: {e}")
            return []

