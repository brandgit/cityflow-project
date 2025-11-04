"""
Calculs spécifiques au trafic : temps perdu, alertes congestion, fiabilité, etc.
"""

from typing import Dict, List, Optional, Tuple
from config import (
    TAUX_OCCUPATION_SEUIL_CONGESTION,
    TAUX_OCCUPATION_SEUIL_CRITIQUE,
    DUREE_ALERTE_CONGESTION_MINUTES,
    VITESSE_REFERENCE_NORMALE,
    VITESSE_REFERENCE_URBAINE,
    TAUX_OCCUPATION_VITESSE
)


def calculate_observed_speed(taux_occupation: float, 
                            vitesse_reference: float = None) -> float:
    """
    Calcule la vitesse observée selon le taux d'occupation
    
    Args:
        taux_occupation: Taux d'occupation (0-100)
        vitesse_reference: Vitesse de référence (défaut: config)
    
    Returns:
        Vitesse observée en km/h
    """
    if vitesse_reference is None:
        vitesse_reference = VITESSE_REFERENCE_NORMALE
    
    taux = float(taux_occupation)
    
    # Appliquer coefficients selon taux d'occupation
    if taux < TAUX_OCCUPATION_VITESSE["faible"][1]:
        coefficient = TAUX_OCCUPATION_VITESSE["faible"][2]
    elif taux < TAUX_OCCUPATION_VITESSE["moyen"][1]:
        coefficient = TAUX_OCCUPATION_VITESSE["moyen"][2]
    elif taux < TAUX_OCCUPATION_VITESSE["eleve"][1]:
        coefficient = TAUX_OCCUPATION_VITESSE["eleve"][2]
    else:
        # Taux > 70% → vitesse critique fixe
        return 20.0  # km/h
    
    return vitesse_reference * coefficient


def calculate_lost_time(debit_horaire: float,
                       taux_occupation: float,
                       longueur_metres: float,
                       vitesse_reference: float = None) -> Tuple[float, float]:
    """
    Calcule le temps perdu pour un tronçon
    
    Args:
        debit_horaire: Débit horaire (véhicules/heure)
        taux_occupation: Taux d'occupation (0-100)
        longueur_metres: Longueur du tronçon en mètres
        vitesse_reference: Vitesse de référence (défaut: config)
    
    Returns:
        Tuple (temps_perdu_minutes, temps_perdu_total_minutes)
        - temps_perdu_minutes: Temps perdu par véhicule
        - temps_perdu_total_minutes: Temps perdu total (× nombre véhicules)
    """
    if vitesse_reference is None:
        vitesse_reference = VITESSE_REFERENCE_NORMALE
    
    if longueur_metres <= 0 or debit_horaire <= 0:
        return 0.0, 0.0
    
    # Calculer vitesses
    vitesse_observée = calculate_observed_speed(taux_occupation, vitesse_reference)
    
    # Longueur en km
    longueur_km = longueur_metres / 1000.0
    
    # Temps normal (minutes)
    temps_normal = (longueur_km / vitesse_reference) * 60.0
    
    # Temps observé (minutes)
    temps_observé = (longueur_km / vitesse_observée) * 60.0
    
    # Temps perdu par véhicule (minutes)
    temps_perdu = max(0.0, temps_observé - temps_normal)
    
    # Temps perdu total (minutes) = temps_perdu × nombre véhicules
    temps_perdu_total = temps_perdu * debit_horaire
    
    return temps_perdu, temps_perdu_total


def detect_congestion_alerts(data: List[Dict],
                            taux_occupation_field: str = "Taux d'occupation",
                            date_field: str = "Date et heure de comptage",
                            seuil_taux: float = None,
                            duree_minutes: int = None) -> List[Dict]:
    """
    Détecte les alertes de congestion
    
    Args:
        data: Liste des données de trafic
        taux_occupation_field: Nom du champ taux d'occupation
        date_field: Nom du champ date
        seuil_taux: Seuil taux d'occupation (défaut: config)
        duree_minutes: Durée minimale pour alerte (défaut: config)
    
    Returns:
        Liste des alertes de congestion
    """
    if seuil_taux is None:
        seuil_taux = TAUX_OCCUPATION_SEUIL_CONGESTION
    
    if duree_minutes is None:
        duree_minutes = DUREE_ALERTE_CONGESTION_MINUTES
    
    alerts = []
    
    # Grouper par tronçon et heure
    from utils.aggregators import group_by_field
    
    # Groupement par tronçon (on suppose qu'il y a un champ identifiant)
    # Pour simplification, on groupe par taux d'occupation élevé
    
    for record in data:
        taux = record.get(taux_occupation_field)
        if taux is None:
            continue
        
        taux_float = float(taux) if taux else 0.0
        
        if taux_float >= seuil_taux:
            # Calculer la durée si possible (nécessite données temporelles)
            date_str = record.get(date_field)
            
            alert = {
                "troncon_id": record.get("Identifiant arc", "unknown"),
                "libelle": record.get("Libelle", ""),
                "taux_occupation": taux_float,
                "date": date_str,
                "severite": "Critique" if taux_float >= TAUX_OCCUPATION_SEUIL_CRITIQUE else "Élevée",
                "geo_point_2d": record.get("geo_point_2d", ""),
            }
            
            alerts.append(alert)
    
    return alerts


def calculate_traffic_reliability_index(data: List[Dict],
                                     disruption_field: str = "disruptions") -> float:
    """
    Calcule l'indice de fiabilité du trafic (% temps sans perturbation)
    
    Args:
        data: Liste des données
        disruption_field: Nom du champ disruptions
    
    Returns:
        Indice de fiabilité (0-100)
    """
    if not data:
        return 100.0
    
    total_periods = len(data)
    disrupted_periods = sum(1 for record in data 
                           if record.get(disruption_field))
    
    if total_periods == 0:
        return 100.0
    
    reliability = ((total_periods - disrupted_periods) / total_periods) * 100.0
    return max(0.0, min(100.0, reliability))


def compare_to_day_type(current_data: List[Dict],
                       day_type_profile: Dict,
                       count_field: str = "sum_counts") -> Dict:
    """
    Compare les données actuelles au profil "jour type"
    
    Args:
        current_data: Données actuelles
        day_type_profile: Profil jour type {heure: moyenne}
        count_field: Nom du champ comptage
    
    Returns:
        Dict avec comparaison et écart normalisé
    """
    from utils.aggregators import aggregate_by_hour, calculate_daily_total
    from utils.time_utils import parse_iso_date
    
    # Agrégation par heure des données actuelles
    current_hourly = aggregate_by_hour(current_data, count_field=count_field)
    
    # Calculer totaux
    current_total = calculate_daily_total(current_data, count_field)
    day_type_total = sum(day_type_profile.values())
    
    # Calculer écart normalisé
    if day_type_total == 0:
        ecart_normalise = 0.0
    else:
        ecart_normalise = ((current_total - day_type_total) / day_type_total) * 100.0
    
    # Comparaison par heure
    hourly_comparison = {}
    for hour in range(24):
        current = current_hourly.get(hour, 0)
        day_type = day_type_profile.get(hour, 0)
        
        if day_type == 0:
            deviation = 0.0 if current == 0 else 100.0
        else:
            deviation = ((current - day_type) / day_type) * 100.0
        
        hourly_comparison[hour] = {
            "current": current,
            "day_type": day_type,
            "deviation_percent": deviation
        }
    
    return {
        "total_current": current_total,
        "total_day_type": day_type_total,
        "ecart_normalise_percent": ecart_normalise,
        "hourly_comparison": hourly_comparison
    }


def calculate_congestion_index(taux_occupation: float) -> float:
    """
    Calcule un indice de congestion (0-100)
    
    Args:
        taux_occupation: Taux d'occupation (0-100)
    
    Returns:
        Indice de congestion (0-100)
    """
    taux = float(taux_occupation)
    
    # Indice basé sur taux d'occupation
    if taux < 30:
        return taux * 0.5  # Faible congestion
    elif taux < 50:
        return 15 + (taux - 30) * 0.75  # Congestion moyenne
    elif taux < 70:
        return 30 + (taux - 50) * 1.0  # Congestion élevée
    else:
        return 50 + (taux - 70) * 1.67  # Congestion critique (max 100)


def estimate_impact_on_traffic(chantier_impact: str,
                               base_traffic: float) -> float:
    """
    Estime l'impact d'un chantier sur le trafic
    
    Args:
        chantier_impact: Type d'impact (BARRAGE_TOTAL, IMPASSE, etc.)
        base_traffic: Trafic de base
    
    Returns:
        Trafic estimé après impact
    """
    from config import IMPACT_CHANTIERS
    
    impact_percent = IMPACT_CHANTIERS.get(chantier_impact, 0)
    reduction = base_traffic * (impact_percent / 100.0)
    
    return max(0.0, base_traffic - reduction)

