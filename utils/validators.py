"""
Utilitaires de validation et nettoyage des données
"""

import re
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
from config import CAPTEUR_DEFAILLANT_HEURES, VARIATION_ANOMALIE_POURCENT


def validate_coordinates(lon: float, lat: float) -> bool:
    """
    Valide les coordonnées GPS
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        True si coordonnées valides
    """
    return -180 <= lon <= 180 and -90 <= lat <= 90


def validate_date_iso(date_string: str) -> Optional[datetime]:
    """
    Parse et valide une date ISO 8601
    
    Args:
        date_string: Date au format ISO (ex: "2025-11-03T02:00:00+01:00")
    
    Returns:
        datetime object ou None si invalide
    """
    try:
        # Formats ISO supportés
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        return None
    except Exception:
        return None


def detect_failing_sensors(data: List[Dict], 
                           sensor_id_field: str = "id_compteur",
                           date_field: str = "date",
                           count_field: str = "sum_counts",
                           threshold_hours: int = None) -> List[str]:
    """
    Détecte les capteurs défaillants (inactifs > threshold_hours)
    
    Args:
        data: Liste des données
        sensor_id_field: Nom du champ ID capteur
        date_field: Nom du champ date
        count_field: Nom du champ comptage
        threshold_hours: Heures minimum sans données (défaut: config)
    
    Returns:
        Liste des IDs capteurs défaillants
    """
    if threshold_hours is None:
        threshold_hours = CAPTEUR_DEFAILLANT_HEURES
    
    failing_sensors = []
    
    # Grouper par capteur
    sensors_data = {}
    for record in data:
        sensor_id = record.get(sensor_id_field)
        if not sensor_id:
            continue
        
        if sensor_id not in sensors_data:
            sensors_data[sensor_id] = []
        
        sensors_data[sensor_id].append(record)
    
    # Vérifier chaque capteur
    for sensor_id, records in sensors_data.items():
        # Trier par date
        sorted_records = sorted(records, key=lambda x: x.get(date_field, ""))
        
        # Vérifier si inactif (count = 0 ou null)
        inactive_count = sum(1 for r in sorted_records 
                           if not r.get(count_field) or r.get(count_field) == 0)
        
        # Si toutes les données sont nulles ou 0
        if len(sorted_records) > 0 and inactive_count == len(sorted_records):
            failing_sensors.append(sensor_id)
            continue
        
        # Vérifier si valeur constante (anomalie)
        values = [r.get(count_field) for r in sorted_records if r.get(count_field)]
        if len(values) > 12 and len(set(values)) == 1:  # Même valeur pendant > 12h
            failing_sensors.append(sensor_id)
    
    return failing_sensors


def validate_geojson(geo_shape: Any) -> bool:
    """
    Valide un objet GeoJSON
    
    Args:
        geo_shape: Objet GeoJSON (dict ou string JSON)
    
    Returns:
        True si GeoJSON valide
    """
    try:
        if isinstance(geo_shape, str):
            geo_shape = json.loads(geo_shape)
        
        if not isinstance(geo_shape, dict):
            return False
        
        # Vérifier type GeoJSON
        geo_type = geo_shape.get("type")
        if geo_type not in ["Point", "LineString", "Polygon", "MultiPolygon"]:
            return False
        
        # Vérifier présence coordinates
        if "coordinates" not in geo_shape:
            return False
        
        return True
    except Exception:
        return False


def normalize_traffic_status(etat_trafic: str) -> str:
    """
    Normalise les statuts de trafic
    
    Args:
        etat_trafic: Statut brut
    
    Returns:
        Statut normalisé
    """
    etat_trafic = etat_trafic.upper().strip()
    
    mapping = {
        "FLUIDE": "Fluide",
        "FLU": "Fluide",
        "PRÉ-SATURÉ": "Pré-saturé",
        "PRE-SATURE": "Pré-saturé",
        "SATURÉ": "Saturé",
        "SATURE": "Saturé",
        "INCONNU": "Inconnu",
        "UNKNOWN": "Inconnu"
    }
    
    return mapping.get(etat_trafic, etat_trafic)


def detect_anomalies(current_value: float, 
                    historical_mean: float,
                    threshold_percent: int = None) -> bool:
    """
    Détecte des anomalies (variation > threshold)
    
    Args:
        current_value: Valeur actuelle
        historical_mean: Moyenne historique
        threshold_percent: Seuil % (défaut: config)
    
    Returns:
        True si anomalie détectée
    """
    if threshold_percent is None:
        threshold_percent = VARIATION_ANOMALIE_POURCENT
    
    if historical_mean == 0:
        return False
    
    variation = abs((current_value - historical_mean) / historical_mean) * 100
    return variation > threshold_percent


def validate_csv_separator(file_path: str, expected_separator: str = ";") -> bool:
    """
    Vérifie que le CSV utilise le bon séparateur
    
    Args:
        file_path: Chemin du fichier CSV
        expected_separator: Séparateur attendu
    
    Returns:
        True si séparateur correct
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            return expected_separator in first_line
    except Exception:
        return False


def clean_null_values(record: Dict, fields: List[str]) -> Dict:
    """
    Nettoie les valeurs nulles d'un enregistrement
    
    Args:
        record: Enregistrement à nettoyer
        fields: Champs à vérifier
    
    Returns:
        Enregistrement nettoyé
    """
    cleaned = record.copy()
    for field in fields:
        if field in cleaned and (cleaned[field] == "" or cleaned[field] is None):
            cleaned[field] = None  # Marquer comme None au lieu de ""
    
    return cleaned


def validate_arrondissement(arrondissement: str) -> bool:
    """
    Valide un code arrondissement Paris
    
    Args:
        arrondissement: Code arrondissement (ex: "75001")
    
    Returns:
        True si valide
    """
    from config import ARRONDISSEMENTS_PARIS
    return arrondissement in ARRONDISSEMENTS_PARIS


def extract_arrondissement_from_coord(lon: float, lat: float) -> Optional[str]:
    """
    Extrait l'arrondissement depuis les coordonnées GPS
    (Simplification - dans un vrai projet, utiliser une API géographique)
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        Code arrondissement ou None
    """
    # Zone approximative Paris centre
    if not (2.2 <= lon <= 2.4 and 48.8 <= lat <= 48.9):
        return None
    
    # Approximation basée sur la latitude (zone nord/sud)
    # Dans un vrai projet, utiliser une bibliothèque comme shapely
    # ou une API de géolocalisation
    
    # Approximation simple basée sur longitude
    if 2.30 <= lon <= 2.37:
        if 48.84 <= lat <= 48.87:
            return "75001"  # Centre
        elif 48.87 <= lat <= 48.90:
            return "75009"  # Nord-centre
    
    # Par défaut, retourner None (nécessite vraie API géographique)
    return None

