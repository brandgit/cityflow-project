"""
Validation des paramètres API
"""

from datetime import datetime
from typing import Optional


VALID_METRIC_TYPES = [
    "bikes",
    "traffic",
    "weather",
    "comptages",
    "chantiers",
    "referentiel"
]


def validate_date(date_str: str) -> bool:
    """
    Valide le format d'une date
    
    Args:
        date_str: Date au format YYYY-MM-DD
    
    Returns:
        True si valide
    """
    if not date_str:
        return False
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_metric_type(metric_type: str) -> bool:
    """
    Valide le type de métrique
    
    Args:
        metric_type: Type de métrique
    
    Returns:
        True si valide
    """
    return metric_type in VALID_METRIC_TYPES


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Valide une plage de dates
    
    Args:
        start_date: Date de début
        end_date: Date de fin
    
    Returns:
        True si valide
    """
    if not validate_date(start_date) or not validate_date(end_date):
        return False
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start <= end
    except ValueError:
        return False

