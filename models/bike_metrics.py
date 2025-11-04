"""
Modèles de données pour les métriques vélos
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class BikeMetrics:
    """Métriques de comptage vélos"""
    date: str
    id_compteur: str
    nom_compteur: str
    total_jour: float = 0.0
    moyenne_horaire: float = 0.0
    pic_horaire: Optional[int] = None
    arrondissement: Optional[str] = None
    coordinates: Optional[Dict] = None
    anomalie_detectee: bool = False
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour DynamoDB"""
        return {
            "date": self.date,
            "id_compteur": self.id_compteur,
            "nom_compteur": self.nom_compteur,
            "total_jour": self.total_jour,
            "moyenne_horaire": self.moyenne_horaire,
            "pic_horaire": self.pic_horaire,
            "arrondissement": self.arrondissement,
            "coordinates": self.coordinates,
            "anomalie_detectee": self.anomalie_detectee
        }

