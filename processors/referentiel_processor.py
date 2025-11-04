"""
Processeur pour le Référentiel Géographique
"""

from typing import List, Dict, Any
from processors.base_processor import BaseProcessor
from processors.utils.file_utils import load_csv
from processors.utils.validators import validate_geojson, validate_date_iso
from processors.utils.geo_utils import calculate_line_length, extract_center_point


class ReferentielProcessor(BaseProcessor):
    """Processeur pour le référentiel géographique"""
    
    def validate_and_clean(self, data: Any) -> List[Dict]:
        """
        Validation et nettoyage du référentiel
        
        Args:
            data: Chemin CSV ou liste de dicts
        
        Returns:
            Liste des tronçons validés
        """
        if isinstance(data, str):
            records = load_csv(data)
        else:
            records = data
        
        cleaned = []
        
        for record in records:
            # Récupérer les données (validation permissive)
            identifiant_arc = record.get("Identifiant arc", "")
            libelle = record.get("Libelle", "")
            
            # Skip si pas d'identifiant (obligatoire)
            if not identifiant_arc or not libelle:
                continue
            
            date_debut_str = record.get("Date debut dispo data", "")
            date_fin_str = record.get("Date fin dispo data", "")
            
            # Valider GeoJSON
            geo_shape = record.get("geo_shape", "")
            if geo_shape and not validate_geojson(geo_shape):
                geo_shape = None
            
            cleaned_record = {
                "Identifiant arc": identifiant_arc,
                "Libelle": libelle,
                "Date debut dispo data": date_debut_str,
                "Date fin dispo data": date_fin_str,
                "Identifiant noeud amont": record.get("Identifiant noeud amont", ""),
                "Identifiant noeud aval": record.get("Identifiant noeud aval", ""),
                "geo_shape": geo_shape,
                "geo_point_2d": record.get("geo_point_2d", "")
            }
            
            cleaned.append(cleaned_record)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        Création table de mapping (lookup)
        
        Args:
            cleaned_data: Référentiel nettoyé
        
        Returns:
            Dict avec table de mapping
        """
        from datetime import datetime
        
        now = datetime.now()
        mapping = {}
        
        for record in cleaned_data:
            arc_id = record.get("Identifiant arc", "")
            if not arc_id:
                continue
            
            # Calculer longueur
            geo_shape = record.get("geo_shape", "")
            longueur = 0.0
            if geo_shape:
                longueur = calculate_line_length(geo_shape)
            
            # Extraire centre
            center = extract_center_point(geo_shape) if geo_shape else None
            
            mapping[arc_id] = {
                "libelle": record.get("Libelle", ""),
                "longueur_metres": longueur,
                "noeud_amont": record.get("Identifiant noeud amont", ""),
                "noeud_aval": record.get("Identifiant noeud aval", ""),
                "geo_point_2d": record.get("geo_point_2d", ""),
                "center": center,
                "actif": True  # Simplifié - vérifier date fin dans vrai projet
            }
        
        return {"mapping": mapping}
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Indicateurs référentiel (statistiques)
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec statistiques
        """
        mapping = aggregated_data.get("mapping", {})
        
        longueurs = [
            v.get("longueur_metres", 0)
            for v in mapping.values()
            if v.get("longueur_metres", 0) > 0
        ]
        
        longueur_moyenne = sum(longueurs) / len(longueurs) if longueurs else 0.0
        longueur_totale = sum(longueurs)
        
        return {
            "mapping": mapping,
            "statistiques": {
                "nombre_troncons": len(mapping),
                "longueur_totale_metres": longueur_totale,
                "longueur_moyenne_metres": longueur_moyenne
            }
        }
    
    def enrich_data(self, data: List[Dict], referentiel_mapping: Dict) -> List[Dict]:
        """
        Enrichit des données avec le référentiel
        
        Args:
            data: Données à enrichir
            referentiel_mapping: Mapping du référentiel
        
        Returns:
            Données enrichies
        """
        enriched = []
        
        for record in data:
            arc_id = record.get("Identifiant arc", "")
            
            if arc_id in referentiel_mapping:
                ref_data = referentiel_mapping[arc_id]
                record["libelle"] = ref_data.get("libelle", record.get("Libelle", ""))
                record["longueur_metres"] = ref_data.get("longueur_metres", 0.0)
            
            enriched.append(record)
        
        return enriched

