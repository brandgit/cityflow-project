"""
Modèles de données pour les métriques de trafic
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class TrafficMetrics:
    """Métriques de trafic pour un tronçon"""
    date: str
    identifiant_arc: str
    libelle: str
    debit_horaire_moyen: float = 0.0
    debit_journalier_total: float = 0.0
    debit_max: float = 0.0
    taux_occupation_moyen: float = 0.0
    etat_trafic_dominant: str = "Inconnu"
    heure_pic: Optional[str] = None
    temps_perdu_minutes: float = 0.0
    temps_perdu_total_minutes: float = 0.0
    congestion_alerte: bool = False
    arrondissement: Optional[str] = None
    geo_point_2d: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour DynamoDB"""
        return {
            "date": self.date,
            "identifiant_arc": self.identifiant_arc,
            "libelle": self.libelle,
            "debit_horaire_moyen": self.debit_horaire_moyen,
            "debit_journalier_total": self.debit_journalier_total,
            "debit_max": self.debit_max,
            "taux_occupation_moyen": self.taux_occupation_moyen,
            "etat_trafic_dominant": self.etat_trafic_dominant,
            "heure_pic": self.heure_pic,
            "temps_perdu_minutes": self.temps_perdu_minutes,
            "temps_perdu_total_minutes": self.temps_perdu_total_minutes,
            "congestion_alerte": self.congestion_alerte,
            "arrondissement": self.arrondissement,
            "geo_point_2d": self.geo_point_2d
        }


@dataclass
class TrafficGlobal:
    """Métriques globales de trafic pour Paris"""
    date: str
    total_vehicules_jour: float = 0.0
    moyenne_debit_par_troncon: float = 0.0
    nombre_troncons_satures: int = 0
    taux_disponibilite_capteurs: float = 100.0
    temps_perdu_total_paris: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour DynamoDB"""
        return {
            "date": self.date,
            "total_vehicules_jour": self.total_vehicules_jour,
            "moyenne_debit_par_troncon": self.moyenne_debit_par_troncon,
            "nombre_troncons_satures": self.nombre_troncons_satures,
            "taux_disponibilite_capteurs": self.taux_disponibilite_capteurs,
            "temps_perdu_total_paris": self.temps_perdu_total_paris
        }

