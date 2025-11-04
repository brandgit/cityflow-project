"""
Utilitaires d'agrégation : agrégations horaires, par arrondissement, totaux, etc.
"""

from collections import defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from .time_utils import parse_iso_date, normalize_hour


def aggregate_by_hour(data: List[Dict], 
                      date_field: str = "date",
                      count_field: str = "sum_counts") -> Dict[int, float]:
    """
    Agrège les données par heure
    
    Args:
        data: Liste des données
        date_field: Nom du champ date
        count_field: Nom du champ comptage
    
    Returns:
        Dict {heure: total} (0-23)
    """
    hourly_totals = defaultdict(float)
    
    for record in data:
        date_str = record.get(date_field)
        if not date_str:
            continue
        
        date_obj = parse_iso_date(date_str)
        if not date_obj:
            continue
        
        hour = normalize_hour(date_obj.hour)
        count = record.get(count_field, 0) or 0
        
        hourly_totals[hour] += float(count)
    
    return dict(hourly_totals)


def aggregate_by_arrondissement(data: List[Dict],
                                 arrondissement_field: str = "arrondissement",
                                 count_field: str = "sum_counts") -> Dict[str, float]:
    """
    Agrège les données par arrondissement
    
    Args:
        data: Liste des données
        arrondissement_field: Nom du champ arrondissement
        count_field: Nom du champ comptage
    
    Returns:
        Dict {arrondissement: total}
    """
    arrondissement_totals = defaultdict(float)
    
    for record in data:
        arrondissement = record.get(arrondissement_field)
        if not arrondissement:
            continue
        
        count = record.get(count_field, 0) or 0
        arrondissement_totals[arrondissement] += float(count)
    
    return dict(arrondissement_totals)


def calculate_daily_total(data: List[Dict],
                          count_field: str = "sum_counts") -> float:
    """
    Calcule le total quotidien
    
    Args:
        data: Liste des données
        count_field: Nom du champ comptage
    
    Returns:
        Total quotidien
    """
    total = 0.0
    
    for record in data:
        count = record.get(count_field, 0) or 0
        total += float(count)
    
    return total


def calculate_hourly_average(data: List[Dict],
                           count_field: str = "sum_counts") -> float:
    """
    Calcule la moyenne horaire
    
    Args:
        data: Liste des données
        count_field: Nom du champ comptage
    
    Returns:
        Moyenne horaire
    """
    if not data:
        return 0.0
    
    total = calculate_daily_total(data, count_field)
    return total / 24.0


def find_peak_hour(data: List[Dict],
                  date_field: str = "date",
                  count_field: str = "sum_counts") -> Optional[int]:
    """
    Trouve l'heure de pic (maximum)
    
    Args:
        data: Liste des données
        date_field: Nom du champ date
        count_field: Nom du champ comptage
    
    Returns:
        Heure de pic (0-23) ou None
    """
    hourly_totals = aggregate_by_hour(data, date_field, count_field)
    
    if not hourly_totals:
        return None
    
    return max(hourly_totals.items(), key=lambda x: x[1])[0]


def find_low_hours(data: List[Dict],
                  date_field: str = "date",
                  count_field: str = "sum_counts",
                  threshold_percent: float = 5.0) -> List[int]:
    """
    Trouve les heures creuses (< threshold_percent du total)
    
    Args:
        data: Liste des données
        date_field: Nom du champ date
        count_field: Nom du champ comptage
        threshold_percent: Seuil en % du total
    
    Returns:
        Liste des heures creuses
    """
    hourly_totals = aggregate_by_hour(data, date_field, count_field)
    
    if not hourly_totals:
        return []
    
    daily_total = sum(hourly_totals.values())
    threshold = daily_total * (threshold_percent / 100.0)
    
    low_hours = [hour for hour, total in hourly_totals.items() if total < threshold]
    return sorted(low_hours)


def aggregate_by_date(data: List[Dict],
                      date_field: str = "date",
                      count_field: str = "sum_counts") -> Dict[str, float]:
    """
    Agrège les données par date (YYYY-MM-DD)
    
    Args:
        data: Liste des données
        date_field: Nom du champ date
        count_field: Nom du champ comptage
    
    Returns:
        Dict {date: total}
    """
    daily_totals = defaultdict(float)
    
    for record in data:
        date_str = record.get(date_field)
        if not date_str:
            continue
        
        date_obj = parse_iso_date(date_str)
        if not date_obj:
            continue
        
        date_key = date_obj.strftime("%Y-%m-%d")
        count = record.get(count_field, 0) or 0
        
        daily_totals[date_key] += float(count)
    
    return dict(daily_totals)


def calculate_max_value(data: List[Dict], field: str) -> Optional[float]:
    """
    Calcule la valeur maximale d'un champ
    
    Args:
        data: Liste des données
        field: Nom du champ
    
    Returns:
        Valeur maximale ou None
    """
    values = [record.get(field) for record in data if record.get(field) is not None]
    
    if not values:
        return None
    
    try:
        return max(float(v) for v in values)
    except (ValueError, TypeError):
        return None


def calculate_min_value(data: List[Dict], field: str) -> Optional[float]:
    """
    Calcule la valeur minimale d'un champ
    
    Args:
        data: Liste des données
        field: Nom du champ
    
    Returns:
        Valeur minimale ou None
    """
    values = [record.get(field) for record in data if record.get(field) is not None]
    
    if not values:
        return None
    
    try:
        return min(float(v) for v in values)
    except (ValueError, TypeError):
        return None


def calculate_mean_value(data: List[Dict], field: str) -> Optional[float]:
    """
    Calcule la moyenne d'un champ
    
    Args:
        data: Liste des données
        field: Nom du champ
    
    Returns:
        Moyenne ou None
    """
    values = [record.get(field) for record in data if record.get(field) is not None]
    
    if not values:
        return None
    
    try:
        numeric_values = [float(v) for v in values]
        return sum(numeric_values) / len(numeric_values)
    except (ValueError, TypeError):
        return None


def get_mode_value(data: List[Dict], field: str) -> Optional[Any]:
    """
    Calcule le mode (valeur la plus fréquente) d'un champ
    
    Args:
        data: Liste des données
        field: Nom du champ
    
    Returns:
        Mode ou None
    """
    from collections import Counter
    
    values = [record.get(field) for record in data if record.get(field) is not None]
    
    if not values:
        return None
    
    counter = Counter(values)
    if counter:
        return counter.most_common(1)[0][0]
    
    return None


def group_by_field(data: List[Dict], field: str) -> Dict[Any, List[Dict]]:
    """
    Groupe les données par valeur d'un champ
    
    Args:
        data: Liste des données
        field: Nom du champ pour groupement
    
    Returns:
        Dict {valeur: [enregistrements]}
    """
    grouped = defaultdict(list)
    
    for record in data:
        key = record.get(field)
        grouped[key].append(record)
    
    return dict(grouped)


def calculate_top_n(data: List[Dict],
                    count_field: str,
                    n: int = 10,
                    key_field: Optional[str] = None) -> List[Dict]:
    """
    Calcule le Top N selon un champ comptage
    
    Args:
        data: Liste des données
        count_field: Nom du champ comptage
        n: Nombre d'éléments du top
        key_field: Champ pour identifier l'élément (si None, utilise l'index)
    
    Returns:
        Liste des Top N enregistrements
    """
    # Grouper par clé si spécifié
    if key_field:
        grouped = group_by_field(data, key_field)
        aggregated = []
        
        for key, records in grouped.items():
            total = calculate_daily_total(records, count_field)
            aggregated.append({
                key_field: key,
                count_field: total,
                "records_count": len(records)
            })
        
        data = aggregated
    
    # Trier par count_field décroissant
    sorted_data = sorted(data, key=lambda x: x.get(count_field, 0), reverse=True)
    
    return sorted_data[:n]

