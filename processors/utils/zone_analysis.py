"""
Utilitaires pour l'analyse des zones à forte affluence
Gère les cas où l'arrondissement n'est pas disponible
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict


def get_zone_from_coordinates(lon: float, lat: float) -> str:
    """
    Détermine une zone géographique à partir des coordonnées
    (Alternative à arrondissement quand non disponible)
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        Zone géographique (Nord, Sud, Est, Ouest, Centre, Nord-Ouest, Nord-Est, Sud-Ouest, Sud-Est, Unknown)
    """
    # Vérification zone Paris (élargie pour couvrir banlieue proche)
    if not (2.2 <= lon <= 2.5 and 48.7 <= lat <= 49.0):
        return "Unknown"
    
    # Déterminer la zone approximative
    # Centre de Paris: 2.3522, 48.8566
    
    # Centre (zone très centrale)
    if 2.33 <= lon <= 2.37 and 48.85 <= lat <= 48.87:
        return "Centre"
    
    # Nord (zone au-dessus du centre)
    if lat > 48.86:
        if lon < 2.33:
            return "Nord-Ouest"
        elif lon > 2.37:
            return "Nord-Est"
        else:
            # Zone entre 2.33 et 2.37, mais au nord
            return "Nord"
    
    # Sud (zone en-dessous du centre)
    if lat < 48.85:
        if lon < 2.33:
            return "Sud-Ouest"
        elif lon > 2.37:
            return "Sud-Est"
        else:
            # Zone entre 2.33 et 2.37, mais au sud
            return "Sud"
    
    # Est (zone à droite du centre, mais pas nord/sud extrême)
    if lon > 2.37:
        if lat > 48.86:
            return "Nord-Est"
        elif lat < 48.85:
            return "Sud-Est"
        else:
            return "Est"
    
    # Ouest (zone à gauche du centre, mais pas nord/sud extrême)
    if lon < 2.33:
        if lat > 48.86:
            return "Nord-Ouest"
        elif lat < 48.85:
            return "Sud-Ouest"
        else:
            return "Ouest"
    
    # Zone centrale mais pas dans le centre strict
    # Utiliser le quadrant comme fallback
    return get_quadrant_from_coordinates(lon, lat)


def get_quadrant_from_coordinates(lon: float, lat: float) -> str:
    """
    Détermine le quadrant géographique (plus précis que zone)
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        Quadrant (ex: "Centre-Nord", "Est-Sud")
    """
    if not (2.2 <= lon <= 2.4 and 48.8 <= lat <= 48.9):
        return "Unknown"
    
    # Centre de Paris
    center_lon = 2.3522
    center_lat = 48.8566
    
    # Déterminer quadrant
    if lon < center_lon and lat > center_lat:
        return "Nord-Ouest"
    elif lon >= center_lon and lat > center_lat:
        return "Nord-Est"
    elif lon < center_lon and lat <= center_lat:
        return "Sud-Ouest"
    elif lon >= center_lon and lat <= center_lat:
        return "Sud-Est"
    
    return "Unknown"


def extract_zone_from_libelle(libelle: str) -> Optional[str]:
    """
    Extrait une zone géographique depuis le libellé du tronçon
    (Les libellés contiennent souvent le nom de la rue/quartier)
    
    Args:
        libelle: Libellé du tronçon (ex: "Boulevard Haussmann")
    
    Returns:
        Zone identifiée ou None
    """
    if not libelle:
        return None
    
    libelle_lower = libelle.lower()
    
    # Mapping de rues/quartiers vers zones
    # Centre
    if any(word in libelle_lower for word in ["châtelet", "louvre", "rivoli", "hôtel de ville"]):
        return "Centre"
    
    # Nord
    if any(word in libelle_lower for word in ["gare du nord", "gare de l'est", "belleville", "ménilmontant"]):
        return "Nord"
    
    # Est
    if any(word in libelle_lower for word in ["nation", "bastille", "oberkampf"]):
        return "Est"
    
    # Ouest
    if any(word in libelle_lower for word in ["arc de triomphe", "champs-élysées", "concorde", "madeleine"]):
        return "Ouest"
    
    # Sud
    if any(word in libelle_lower for word in ["montparnasse", "gare d'austerlitz", "gobelins"]):
        return "Sud"
    
    return None


def group_by_zone(metrics: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Groupe les métriques par zone géographique
    (Utilise arrondissement si disponible, sinon zone ou quadrant)
    
    Args:
        metrics: Liste des métriques de tronçons
    
    Returns:
        Dict {zone: [métriques]}
    """
    by_zone = defaultdict(list)
    
    for metric in metrics:
        # Priorité 1: Arrondissement
        arrondissement = metric.get("arrondissement")
        if arrondissement and arrondissement != "Unknown":
            by_zone[f"Arrondissement {arrondissement}"].append(metric)
            continue
        
        # Priorité 2: Zone depuis libellé
        libelle = metric.get("libelle", "")
        zone_from_libelle = extract_zone_from_libelle(libelle)
        if zone_from_libelle:
            by_zone[zone_from_libelle].append(metric)
            continue
        
        # Priorité 3: Zone depuis coordonnées
        geo_point = metric.get("geo_point_2d")
        if geo_point:
            try:
                # Format: "lat, lon"
                lat_str, lon_str = geo_point.split(", ")
                lon = float(lon_str)
                lat = float(lat_str)
                zone = get_zone_from_coordinates(lon, lat)
                by_zone[zone].append(metric)
            except Exception:
                by_zone["Unknown"].append(metric)
        else:
            by_zone["Unknown"].append(metric)
    
    return dict(by_zone)


def calculate_zone_metrics(by_zone: Dict[str, List[Dict]]) -> List[Dict]:
    """
    Calcule les métriques agrégées par zone
    
    Args:
        by_zone: Dict {zone: [métriques]}
    
    Returns:
        Liste des métriques par zone (triée par affluence)
    """
    zone_metrics = []
    
    for zone, metrics in by_zone.items():
        if not metrics:
            continue
        
        # Calculer agrégations
        total_vehicules = sum(m.get("debit_journalier_total", 0) for m in metrics)
        temps_perdu_total = sum(m.get("temps_perdu_total_minutes", 0) for m in metrics)
        nombre_troncons = len(metrics)
        nombre_troncons_satures = len([m for m in metrics if m.get("congestion_alerte", False)])
        
        # Tronçons les plus fréquentés de la zone
        top_troncons = sorted(
            metrics,
            key=lambda x: x.get("debit_journalier_total", 0),
            reverse=True
        )[:5]
        
        zone_metrics.append({
            "zone": zone,
            "nombre_troncons": nombre_troncons,
            "total_vehicules": total_vehicules,
            "temps_perdu_total_minutes": temps_perdu_total,
            "nombre_troncons_satures": nombre_troncons_satures,
            "taux_saturation": (nombre_troncons_satures / nombre_troncons * 100) if nombre_troncons > 0 else 0,
            "moyenne_vehicules_par_troncon": total_vehicules / nombre_troncons if nombre_troncons > 0 else 0,
            "top_troncons": [
                {
                    "libelle": t.get("libelle", ""),
                    "debit_journalier_total": t.get("debit_journalier_total", 0),
                    "etat_trafic": t.get("etat_trafic_dominant", "Inconnu")
                }
                for t in top_troncons
            ]
        })
    
    # Trier par affluence (total véhicules)
    return sorted(zone_metrics, key=lambda x: x["total_vehicules"], reverse=True)


def identify_high_traffic_zones(zone_metrics: List[Dict], top_n: int = 10) -> List[Dict]:
    """
    Identifie les zones à forte affluence
    
    Args:
        zone_metrics: Métriques par zone
        top_n: Nombre de zones à retourner
    
    Returns:
        Top N zones à forte affluence
    """
    # Trier par plusieurs critères
    # 1. Total véhicules
    # 2. Temps perdu
    # 3. Taux de saturation
    
    sorted_zones = sorted(
        zone_metrics,
        key=lambda x: (
            x["total_vehicules"],
            x["temps_perdu_total_minutes"],
            x["taux_saturation"]
        ),
        reverse=True
    )
    
    return sorted_zones[:top_n]


def create_zone_clusters(metrics: List[Dict], cluster_size: int = 500) -> Dict[str, List[Dict]]:
    """
    Crée des clusters géographiques pour l'analyse
    (Utile quand arrondissement non disponible)
    
    Args:
        metrics: Liste des métriques
        cluster_size: Taille approximative des clusters (en mètres)
    
    Returns:
        Dict {cluster_id: [métriques]}
    """
    clusters = defaultdict(list)
    
    for metric in metrics:
        geo_point = metric.get("geo_point_2d")
        if not geo_point:
            clusters["no_coordinates"].append(metric)
            continue
        
        try:
            lat_str, lon_str = geo_point.split(", ")
            lon = float(lon_str)
            lat = float(lat_str)
            
            # Créer un ID de cluster basé sur la grille
            # Diviser Paris en grille de ~500m
            cluster_lon = int(lon * 1000) // cluster_size
            cluster_lat = int(lat * 1000) // cluster_size
            cluster_id = f"Cluster_{cluster_lon}_{cluster_lat}"
            
            clusters[cluster_id].append(metric)
        except Exception:
            clusters["no_coordinates"].append(metric)
    
    return dict(clusters)

