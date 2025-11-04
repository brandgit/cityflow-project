"""
Classe abstraite de base pour tous les processeurs de données
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from config import settings


class BaseProcessor(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les processeurs.
    Chaque processeur doit implémenter : validate_and_clean, aggregate_daily, calculate_indicators
    """
    
    def __init__(self, config=None):
        """
        Initialise le processeur
        
        Args:
            config: Configuration (défaut: settings global)
        """
        self.config = config or settings
    
    @abstractmethod
    def validate_and_clean(self, data: Any) -> Any:
        """
        Étape 1 : Validation et nettoyage des données brutes
        
        Args:
            data: Données brutes (format variable selon source)
        
        Returns:
            Données nettoyées et validées
        """
        raise NotImplementedError("Chaque processeur doit implémenter validate_and_clean")
    
    @abstractmethod
    def aggregate_daily(self, cleaned_data: Any) -> Any:
        """
        Étape 2 : Agrégations quotidiennes
        
        Args:
            cleaned_data: Données nettoyées
        
        Returns:
            Données agrégées
        """
        raise NotImplementedError("Chaque processeur doit implémenter aggregate_daily")
    
    @abstractmethod
    def calculate_indicators(self, aggregated_data: Any) -> Any:
        """
        Étape 3 : Calculs d'indicateurs avancés
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Indicateurs calculés
        """
        raise NotImplementedError("Chaque processeur doit implémenter calculate_indicators")
    
    def process(self, raw_data: Any) -> Dict[str, Any]:
        """
        Pipeline complet de traitement : validate → aggregate → calculate
        
        Args:
            raw_data: Données brutes
        
        Returns:
            Dict avec les résultats de chaque étape et les indicateurs finaux
        """
        try:
            # Étape 1 : Validation et nettoyage
            cleaned_data = self.validate_and_clean(raw_data)
            
            # Étape 2 : Agrégations quotidiennes
            aggregated_data = self.aggregate_daily(cleaned_data)
            
            # Étape 3 : Calculs d'indicateurs
            indicators = self.calculate_indicators(aggregated_data)
            
            return {
                "cleaned_data": cleaned_data,
                "aggregated_data": aggregated_data,
                "indicators": indicators,
                "success": True,
                "errors": []
            }
        
        except Exception as e:
            return {
                "cleaned_data": None,
                "aggregated_data": None,
                "indicators": None,
                "success": False,
                "errors": [str(e)]
            }

