"""
Utilitaires temporels : parsing dates, jour type, etc.
"""

from datetime import datetime, timedelta
from typing import Optional

try:
    from dateutil.parser import parse
except ImportError:
    def parse(date_string):
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")

try:
    import holidays
except ImportError:
    holidays = None


def parse_iso_date(date_string: str) -> Optional[datetime]:
    """
    Parse une date ISO 8601 avec gestion timezone
    
    Args:
        date_string: Date ISO (ex: "2025-11-03T02:00:00+01:00")
    
    Returns:
        datetime object ou None
    """
    try:
        return parse(date_string)
    except Exception:
        return None


def get_day_type(date: datetime) -> str:
    """
    Détermine le type de jour (Lundi, Mardi, Weekend, Férié)
    
    Args:
        date: Date à analyser
    
    Returns:
        Type de jour ("Lundi", "Mardi", ..., "Dimanche", "Weekend", "Férié")
    """
    # Vérifier si jour férié (France)
    if holidays:
        try:
            fr_holidays = holidays.France()
            if date.date() in fr_holidays:
                return "Férié"
        except Exception:
            pass
    
    # Vérifier weekend
    weekday = date.weekday()
    if weekday >= 5:  # Samedi (5) ou Dimanche (6)
        return "Weekend"
    
    # Jours de semaine
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return days[weekday]


def normalize_hour(hour: int) -> int:
    """
    Normalise une heure (0-23)
    
    Args:
        hour: Heure à normaliser
    
    Returns:
        Heure normalisée (0-23)
    """
    return max(0, min(23, int(hour)))


def calculate_time_difference(date1: datetime, date2: datetime) -> float:
    """
    Calcule la différence en heures entre deux dates
    
    Args:
        date1: Première date
        date2: Deuxième date
    
    Returns:
        Différence en heures
    """
    delta = abs(date1 - date2)
    return delta.total_seconds() / 3600.0


def format_date_for_storage(date: datetime) -> str:
    """
    Formate une date pour stockage (YYYY-MM-DD)
    
    Args:
        date: Date à formater
    
    Returns:
        Date formatée
    """
    return date.strftime("%Y-%m-%d")


def get_previous_week_same_day(current_date: datetime) -> datetime:
    """
    Retourne la date du même jour la semaine précédente
    
    Args:
        current_date: Date actuelle
    
    Returns:
        Date semaine précédente
    """
    return current_date - timedelta(days=7)


def is_business_day(date: datetime) -> bool:
    """
    Vérifie si c'est un jour ouvré
    
    Args:
        date: Date à vérifier
    
    Returns:
        True si jour ouvré
    """
    if holidays:
        try:
            fr_holidays = holidays.France()
            return date.weekday() < 5 and date.date() not in fr_holidays
        except Exception:
            return date.weekday() < 5
    return date.weekday() < 5


def get_time_slot(hour: int) -> str:
    """
    Détermine la tranche horaire
    
    Args:
        hour: Heure (0-23)
    
    Returns:
        Tranche horaire ("Nuit", "Matin", "Après-midi", "Soir")
    """
    if 0 <= hour < 6:
        return "Nuit"
    elif 6 <= hour < 12:
        return "Matin"
    elif 12 <= hour < 18:
        return "Après-midi"
    else:
        return "Soir"

