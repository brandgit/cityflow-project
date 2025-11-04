"""
Processeur pour les données API Bikes (compteurs vélos)
"""

from typing import List, Dict, Any
from processors.base_processor import BaseProcessor
from processors.utils.validators import (
    validate_coordinates, detect_failing_sensors, detect_anomalies
)
from processors.utils.aggregators import (
    aggregate_by_hour, calculate_daily_total, find_peak_hour,
    aggregate_by_arrondissement, calculate_hourly_average
)
from processors.utils.geo_utils import get_arrondissement_from_coordinates
from models.bike_metrics import BikeMetrics


class BikesProcessor(BaseProcessor):
    """Processeur pour les données de compteurs vélos"""
    
    def validate_and_clean(self, data: Dict) -> List[Dict]:
        """
        Validation et nettoyage des données bikes
        
        Args:
            data: Dict avec clé "results" contenant liste des compteurs
        
        Returns:
            Liste des enregistrements validés et nettoyés
        """
        results = data.get("results", [])
        cleaned = []
        
        for record in results:
            # Valider coordonnées GPS
            coords = record.get("coordinates", {})
            lon = coords.get("lon")
            lat = coords.get("lat")
            
            if not validate_coordinates(lon, lat):
                continue
            
            # Nettoyer valeurs nulles
            sum_counts = record.get("sum_counts", 0) or 0
            if sum_counts < 0:
                sum_counts = 0
            
            cleaned_record = {
                "id_compteur": record.get("id_compteur", ""),
                "nom_compteur": record.get("nom_compteur", ""),
                "id": record.get("id", ""),
                "name": record.get("name", ""),
                "sum_counts": float(sum_counts),
                "date": record.get("date", ""),
                "coordinates": coords,
                "lon": lon,
                "lat": lat
            }
            
            cleaned.append(cleaned_record)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        Agrégations quotidiennes bikes
        
        Args:
            cleaned_data: Liste des enregistrements nettoyés
        
        Returns:
            Dict avec agrégations par compteur et globales
        """
        if not cleaned_data:
            return {"by_counter": {}, "global": {}}
        
        # Agrégation par compteur
        by_counter = {}
        
        for record in cleaned_data:
            counter_id = record.get("id_compteur")
            if not counter_id:
                continue
            
            if counter_id not in by_counter:
                by_counter[counter_id] = {
                    "id_compteur": counter_id,
                    "nom_compteur": record.get("nom_compteur", ""),
                    "records": [],
                    "coordinates": record.get("coordinates")
                }
            
            by_counter[counter_id]["records"].append(record)
        
        # Calculer totaux par compteur
        for counter_id, counter_data in by_counter.items():
            records = counter_data["records"]
            counter_data["total_jour"] = calculate_daily_total(records, "sum_counts")
            counter_data["moyenne_horaire"] = calculate_hourly_average(records, "sum_counts")
            
            # Pic horaire
            hourly = aggregate_by_hour(records, "date", "sum_counts")
            if hourly:
                peak = find_peak_hour(records, "date", "sum_counts")
                counter_data["pic_horaire"] = peak
            else:
                counter_data["pic_horaire"] = None
            
            # Arrondissement
            coords = counter_data.get("coordinates", {})
            lon = coords.get("lon")
            lat = coords.get("lat")
            if lon and lat:
                arrondissement = get_arrondissement_from_coordinates(lon, lat)
                counter_data["arrondissement"] = arrondissement
        
        # Agrégation globale
        global_total = calculate_daily_total(cleaned_data, "sum_counts")
        
        # Par arrondissement
        arrondissement_totals = {}
        for record in cleaned_data:
            lon = record.get("lon")
            lat = record.get("lat")
            if lon and lat:
                arr = get_arrondissement_from_coordinates(lon, lat)
                if arr:
                    if arr not in arrondissement_totals:
                        arrondissement_totals[arr] = 0.0
                    arrondissement_totals[arr] += record.get("sum_counts", 0)
        
        return {
            "by_counter": by_counter,
            "global": {
                "total_jour": global_total,
                "arrondissement_totals": arrondissement_totals,
                "nombre_compteurs": len(by_counter)
            }
        }
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Calculs d'indicateurs bikes
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec indicateurs et métriques finales
        """
        by_counter = aggregated_data.get("by_counter", {})
        indicators = {
            "metrics": [],
            "failing_sensors": [],
            "anomalies": [],
            "top_counters": []
        }
        
        # Détecter capteurs défaillants
        all_records = []
        for counter_data in by_counter.values():
            all_records.extend(counter_data.get("records", []))
        
        failing = detect_failing_sensors(all_records)
        indicators["failing_sensors"] = failing
        
        # Créer métriques par compteur
        for counter_id, counter_data in by_counter.items():
            if counter_id in failing:
                continue  # Exclure défaillants
            
            metrics = BikeMetrics(
                date=counter_data.get("records", [{}])[0].get("date", ""),
                id_compteur=counter_id,
                nom_compteur=counter_data.get("nom_compteur", ""),
                total_jour=counter_data.get("total_jour", 0.0),
                moyenne_horaire=counter_data.get("moyenne_horaire", 0.0),
                pic_horaire=counter_data.get("pic_horaire"),
                arrondissement=counter_data.get("arrondissement"),
                coordinates=counter_data.get("coordinates")
            )
            
            indicators["metrics"].append(metrics.to_dict())
        
        # Top compteurs (par total_jour)
        sorted_counters = sorted(
            indicators["metrics"],
            key=lambda x: x.get("total_jour", 0),
            reverse=True
        )
        indicators["top_counters"] = sorted_counters[:10]
        
        # Calculer indice de fréquentation cyclable (0-100)
        global_total = aggregated_data.get("global", {}).get("total_jour", 0)
        # Normalisation basique (à ajuster selon données historiques)
        max_expected = 100000  # Valeur max attendue (à calibrer)
        frequentation_index = min(100.0, (global_total / max_expected) * 100.0)
        
        indicators["frequentation_index"] = frequentation_index
        
        return indicators

