"""
Interface abstraite pour le stockage des métriques et rapports
Permet de basculer entre MongoDB (local) et DynamoDB (production)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class DatabaseService(ABC):
    """Interface abstraite pour le stockage des métriques et rapports"""
    
    @abstractmethod
    def save_metrics(self, metrics: Dict[str, Any], data_type: str, date: str) -> bool:
        """
        Sauvegarde des métriques
        
        Args:
            metrics: Métriques à sauvegarder
            data_type: Type de données (bikes, traffic, weather, etc.)
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        pass
    
    @abstractmethod
    def load_metrics(self, data_type: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge des métriques
        
        Args:
            data_type: Type de données
            date: Date au format YYYY-MM-DD
        
        Returns:
            Métriques ou None si non trouvées
        """
        pass
    
    @abstractmethod
    def save_report(self, report: Dict[str, Any], date: str) -> bool:
        """
        Sauvegarde un rapport quotidien
        
        Args:
            report: Rapport à sauvegarder
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        pass
    
    @abstractmethod
    def load_report(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge un rapport quotidien
        
        Args:
            date: Date au format YYYY-MM-DD
        
        Returns:
            Rapport ou None si non trouvé
        """
        pass
    
    @abstractmethod
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
        pass

