"""
Processeur pour les données Batch Chantiers Perturbants
"""

from typing import List, Dict, Any
from datetime import datetime
from processors.base_processor import BaseProcessor
from processors.utils.file_utils import load_csv
from processors.utils.validators import validate_geojson, validate_date_iso
from processors.utils.geo_utils import calculate_polygon_area, extract_center_point, get_arrondissement_from_coordinates
from processors.utils.aggregators import group_by_field
from config import IMPACT_CHANTIERS


class ChantiersProcessor(BaseProcessor):
    """Processeur pour les chantiers perturbants"""
    
    def validate_and_clean(self, data: Any) -> List[Dict]:
        """
        Validation et nettoyage des chantiers
        
        Args:
            data: Chemin CSV ou liste de dicts
        
        Returns:
            Liste des chantiers nettoyés
        """
        if isinstance(data, str):
            records = load_csv(data)
        else:
            records = data
        
        cleaned = []
        
        for record in records:
            # Valider dates
            date_debut_str = record.get("Date de début", "")
            date_fin_str = record.get("Date de fin", "")
            
            try:
                date_debut = datetime.strptime(date_debut_str, "%Y-%m-%d")
                date_fin = datetime.strptime(date_fin_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue
            
            # Valider GeoJSON
            geo_shape = record.get("geo_shape", "")
            if geo_shape and not validate_geojson(geo_shape):
                geo_shape = None
            
            # Extraire arrondissement
            geo_point = record.get("geo_point_2d", "")
            arrondissement = record.get("Code postal de l'arrondissement", "")
            
            if not arrondissement and geo_point:
                try:
                    lat_str, lon_str = geo_point.split(", ")
                    lon = float(lon_str)
                    lat = float(lat_str)
                    arrondissement = get_arrondissement_from_coordinates(lon, lat)
                except Exception:
                    pass
            
            cleaned_record = {
                "Identifiant": record.get("Identifiant", ""),
                "Typologie": record.get("Typologie", ""),
                "Date de début": date_debut,
                "Date de fin": date_fin,
                "Impact sur la circulation": record.get("Impact sur la circulation", ""),
                "Niveau de perturbation": record.get("Niveau de perturbation", ""),
                "geo_shape": geo_shape,
                "geo_point_2d": geo_point,
                "arrondissement": arrondissement
            }
            
            cleaned.append(cleaned_record)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        Agrégations quotidiennes chantiers
        
        Args:
            cleaned_data: Chantiers nettoyés
        
        Returns:
            Dict avec agrégations
        """
        now = datetime.now()
        
        # Détecter chantiers actifs
        actifs = []
        for chantier in cleaned_data:
            date_debut = chantier.get("Date de début")
            date_fin = chantier.get("Date de fin")
            
            if date_debut and date_fin and date_debut <= now <= date_fin:
                actifs.append(chantier)
        
        # Par arrondissement
        by_arrondissement = group_by_field(actifs, "arrondissement")
        
        # Par type d'impact
        by_impact = group_by_field(actifs, "Impact sur la circulation")
        
        return {
            "actifs": actifs,
            "by_arrondissement": by_arrondissement,
            "by_impact": by_impact,
            "total_actifs": len(actifs)
        }
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Calculs d'indicateurs chantiers
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec indicateurs
        """
        actifs = aggregated_data.get("actifs", [])
        
        # Calculer impact estimé par arrondissement
        impact_by_arrondissement = {}
        
        for chantier in actifs:
            # Gérer le cas où arrondissement est None (MongoDB n'accepte pas None comme clé)
            arr = chantier.get("arrondissement") or "Unknown"
            impact_type = chantier.get("Impact sur la circulation", "")
            impact_percent = IMPACT_CHANTIERS.get(impact_type, 0)
            
            if arr not in impact_by_arrondissement:
                impact_by_arrondissement[arr] = 0
            
            impact_by_arrondissement[arr] += impact_percent
        
        # Zones critiques (> 3 chantiers simultanés)
        by_arr = aggregated_data.get("by_arrondissement", {})
        zones_critiques = [
            {"arrondissement": arr, "nombre_chantiers": len(chantiers)}
            for arr, chantiers in by_arr.items()
            if len(chantiers) > 3
        ]
        
        # Calculer surface totale impactée
        surface_totale = 0.0
        for chantier in actifs:
            geo_shape = chantier.get("geo_shape")
            if geo_shape:
                surface_totale += calculate_polygon_area(geo_shape)
        
        return {
            "chantiers_actifs": [
                {
                    "identifiant": c.get("Identifiant", ""),
                    "typologie": c.get("Typologie", ""),
                    "impact": c.get("Impact sur la circulation", ""),
                    "arrondissement": c.get("arrondissement")
                }
                for c in actifs
            ],
            "impact_by_arrondissement": impact_by_arrondissement,
            "zones_critiques": zones_critiques,
            "surface_totale_impactee_m2": surface_totale,
            "total_chantiers_actifs": len(actifs)
        }

