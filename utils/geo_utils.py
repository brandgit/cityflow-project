"""
Utilitaires géographiques : calcul longueurs, arrondissements, intersections
"""

import json
import math
from typing import Optional, List, Tuple, Dict, Any
from utils.validators import validate_geojson


def calculate_line_length(geo_shape_linestring: Any) -> float:
    """
    Calcule la longueur d'un LineString GeoJSON en mètres
    
    Args:
        geo_shape_linestring: GeoJSON LineString (dict ou string)
    
    Returns:
        Longueur en mètres
    """
    try:
        if isinstance(geo_shape_linestring, str):
            geo_shape_linestring = json.loads(geo_shape_linestring)
        
        if not validate_geojson(geo_shape_linestring):
            return 0.0
        
        if geo_shape_linestring.get("type") != "LineString":
            return 0.0
        
        coordinates = geo_shape_linestring.get("coordinates", [])
        if len(coordinates) < 2:
            return 0.0
        
        # Calculer la distance totale entre tous les points
        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            lon1, lat1 = coordinates[i]
            lon2, lat2 = coordinates[i + 1]
            distance = haversine_distance(lat1, lon1, lat2, lon2)
            total_distance += distance
        
        return total_distance
    except Exception:
        return 0.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance entre deux points GPS (formule Haversine)
    
    Args:
        lat1, lon1: Coordonnées point 1
        lat2, lon2: Coordonnées point 2
    
    Returns:
        Distance en mètres
    """
    # Rayon de la Terre en mètres
    R = 6371000
    
    # Conversion en radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Formule Haversine
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_arrondissement_from_coordinates(lon: float, lat: float) -> Optional[str]:
    """
    Détermine l'arrondissement depuis les coordonnées GPS
    (Version simplifiée - dans un vrai projet, utiliser une API géographique)
    
    Args:
        lon: Longitude
        lat: Latitude
    
    Returns:
        Code arrondissement ou None
    """
    # Vérification zone Paris
    if not (2.2 <= lon <= 2.4 and 48.8 <= lat <= 48.9):
        return None
    
    # Approximation basée sur zones géographiques
    # Zones approximatives des arrondissements Paris
    
    # Centre (1er, 2e, 3e, 4e)
    if 2.33 <= lon <= 2.36 and 48.85 <= lat <= 48.86:
        if lat < 48.855:
            return "75004"
        else:
            return "75001"
    
    # Nord (9e, 10e)
    if 2.34 <= lon <= 2.37 and 48.87 <= lat <= 48.88:
        return "75009"
    
    # Est (11e, 12e)
    if 2.37 <= lon <= 2.40 and 48.84 <= lat <= 48.86:
        if lat < 48.85:
            return "75012"
        else:
            return "75011"
    
    # Ouest (16e, 17e)
    if 2.25 <= lon <= 2.30 and 48.84 <= lat <= 48.88:
        return "75016"
    
    # Sud (13e, 14e, 15e)
    if 2.30 <= lon <= 2.36 and 48.82 <= lat <= 48.84:
        if lon < 2.33:
            return "75015"
        elif lon < 2.35:
            return "75014"
        else:
            return "75013"
    
    # Par défaut, retourner None
    # Dans un vrai projet, utiliser shapely ou une API géographique
    return None


def point_in_polygon(point: Tuple[float, float], polygon_coords: List[List[float]]) -> bool:
    """
    Vérifie si un point est dans un polygone (algorithme ray casting)
    
    Args:
        point: Point (lon, lat)
        polygon_coords: Liste des coordonnées du polygone
    
    Returns:
        True si point dans polygone
    """
    lon, lat = point
    inside = False
    
    j = len(polygon_coords) - 1
    for i in range(len(polygon_coords)):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        
        intersect = ((yi > lat) != (yj > lat)) and \
                    (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)
        
        if intersect:
            inside = not inside
        
        j = i
    
    return inside


def calculate_polygon_area(geo_shape_polygon: Any) -> float:
    """
    Calcule l'aire d'un polygone GeoJSON en m²
    
    Args:
        geo_shape_polygon: GeoJSON Polygon (dict ou string)
    
    Returns:
        Aire en m²
    """
    try:
        if isinstance(geo_shape_polygon, str):
            geo_shape_polygon = json.loads(geo_shape_polygon)
        
        if not validate_geojson(geo_shape_polygon):
            return 0.0
        
        geo_type = geo_shape_polygon.get("type")
        if geo_type not in ["Polygon", "MultiPolygon"]:
            return 0.0
        
        coordinates = geo_shape_polygon.get("coordinates", [])
        if not coordinates:
            return 0.0
        
        # Pour Polygon, prendre le premier ring (exterior)
        if geo_type == "Polygon":
            ring = coordinates[0]
        else:  # MultiPolygon
            # Somme des aires de tous les polygones
            total_area = 0.0
            for polygon in coordinates:
                if polygon:
                    total_area += calculate_polygon_area_simple(polygon[0])
            return total_area
        
        return calculate_polygon_area_simple(ring)
    except Exception:
        return 0.0


def calculate_polygon_area_simple(coordinates: List[List[float]]) -> float:
    """
    Calcule l'aire d'un polygone simple (formule shoelace adaptée pour GPS)
    
    Args:
        coordinates: Liste des coordonnées du polygone
    
    Returns:
        Aire en m²
    """
    if len(coordinates) < 3:
        return 0.0
    
    # Utiliser la formule de l'aire de Gauss (adaptée pour coordonnées GPS)
    area = 0.0
    n = len(coordinates)
    
    for i in range(n):
        j = (i + 1) % n
        lat1, lon1 = coordinates[i][1], coordinates[i][0]  # Inverser pour lat/lon
        lat2, lon2 = coordinates[j][1], coordinates[j][0]
        
        # Approximation simple (dans un vrai projet, utiliser projection UTM)
        area += math.radians(lon1) * math.radians(lat2) - math.radians(lon2) * math.radians(lat1)
    
    area = abs(area) / 2.0
    
    # Convertir en m² (approximation)
    R = 6371000  # Rayon Terre en m
    area_m2 = area * R * R
    
    return area_m2


def extract_center_point(geo_shape: Any) -> Optional[Tuple[float, float]]:
    """
    Extrait le point central d'un GeoJSON
    
    Args:
        geo_shape: GeoJSON (Point, LineString, Polygon)
    
    Returns:
        Point central (lon, lat) ou None
    """
    try:
        if isinstance(geo_shape, str):
            geo_shape = json.loads(geo_shape)
        
        if not validate_geojson(geo_shape):
            return None
        
        geo_type = geo_shape.get("type")
        coordinates = geo_shape.get("coordinates", [])
        
        if geo_type == "Point":
            return tuple(coordinates)
        
        elif geo_type == "LineString":
            # Milieu du LineString
            mid_index = len(coordinates) // 2
            return tuple(coordinates[mid_index])
        
        elif geo_type == "Polygon":
            # Centre du premier ring (exterior)
            if coordinates:
                ring = coordinates[0]
                lons = [c[0] for c in ring]
                lats = [c[1] for c in ring]
                return (sum(lons) / len(lons), sum(lats) / len(lats))
        
        return None
    except Exception:
        return None

