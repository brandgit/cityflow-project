"""
Modèles de données pour les métriques météo
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class WeatherMetrics:
    """Métriques météorologiques"""
    date: str
    temp_moyenne: float = 0.0
    temp_min: float = 0.0
    temp_max: float = 0.0
    precip_totale: float = 0.0
    vent_moyen: float = 0.0
    conditions: str = "Inconnu"
    impact_mobilite: float = 50.0  # Score 0-100
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour DynamoDB"""
        return {
            "date": self.date,
            "temp_moyenne": self.temp_moyenne,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "precip_totale": self.precip_totale,
            "vent_moyen": self.vent_moyen,
            "conditions": self.conditions,
            "impact_mobilite": self.impact_mobilite
        }

