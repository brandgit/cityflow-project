"""
Processeur pour les données API Weather (météo)
"""

from typing import List, Dict, Any
from processors.base_processor import BaseProcessor
from processors.utils.validators import validate_date_iso
from models.weather_metrics import WeatherMetrics


class WeatherProcessor(BaseProcessor):
    """Processeur pour les données météorologiques"""
    
    def validate_and_clean(self, data: Dict) -> Dict:
        """
        Validation et nettoyage des données météo
        
        Args:
            data: Dict avec données météo (clé "days")
        
        Returns:
            Dict nettoyé
        """
        cleaned = {
            "current_conditions": data.get("currentConditions", {}),
            "days": []
        }
        
        days = data.get("days", [])
        
        for day in days:
            # Valider cohérence températures
            temp_max = day.get("tempmax", 0)
            temp_min = day.get("tempmin", 0)
            temp = day.get("temp", 0)
            
            if temp_min > temp_max:
                continue  # Incohérence
            
            if not (temp_min <= temp <= temp_max):
                temp = (temp_min + temp_max) / 2  # Corriger
            
            cleaned_day = {
                "datetime": day.get("datetime", ""),
                "tempmax": float(temp_max),
                "tempmin": float(temp_min),
                "temp": float(temp),
                "precip": float(day.get("precip", 0)),
                "windspeed": float(day.get("windspeed", 0)),
                "conditions": day.get("conditions", "Inconnu")
            }
            
            cleaned["days"].append(cleaned_day)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: Dict) -> Dict[str, Any]:
        """
        Agrégations quotidiennes météo
        
        Args:
            cleaned_data: Données nettoyées
        
        Returns:
            Dict avec agrégations (prend le premier jour disponible)
        """
        days = cleaned_data.get("days", [])
        
        if not days:
            return {"metrics": None}
        
        # Prendre le premier jour (ou jour courant)
        day_data = days[0]
        
        aggregated = {
            "date": day_data.get("datetime", ""),
            "temp_moyenne": day_data.get("temp", 0.0),
            "temp_min": day_data.get("tempmin", 0.0),
            "temp_max": day_data.get("tempmax", 0.0),
            "precip_totale": day_data.get("precip", 0.0),
            "vent_moyen": day_data.get("windspeed", 0.0),
            "conditions": day_data.get("conditions", "Inconnu")
        }
        
        # Catégoriser jour météo
        categories = []
        from config import CONDITIONS_METEO
        
        if aggregated["precip_totale"] >= CONDITIONS_METEO["PLUVIEUX"]["precip"]:
            categories.append("Pluvieux")
        
        if aggregated["vent_moyen"] >= CONDITIONS_METEO["VENTEUX"]["windspeed"]:
            categories.append("Venteux")
        
        if aggregated["temp_moyenne"] < CONDITIONS_METEO["FROID"]["temp"]:
            categories.append("Froid")
        elif aggregated["temp_moyenne"] > CONDITIONS_METEO["CHAUD"]["temp"]:
            categories.append("Chaud")
        
        aggregated["categories"] = categories
        
        return {"metrics": aggregated}
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Calculs d'indicateurs météo
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec indicateurs météo
        """
        metrics_data = aggregated_data.get("metrics")
        
        if not metrics_data:
            return {"metrics": None, "impact_mobilite": 50.0}
        
        # Calculer impact sur mobilité (score 0-100)
        impact = 50.0  # Neutre par défaut
        
        # Ajuster selon conditions
        if "Pluvieux" in metrics_data.get("categories", []):
            impact -= 20  # Pluie réduit mobilité
        
        if "Froid" in metrics_data.get("categories", []):
            impact -= 10  # Froid réduit mobilité
        
        if "Chaud" in metrics_data.get("categories", []):
            impact += 5  # Chaud augmente légèrement
        
        impact = max(0.0, min(100.0, impact))
        
        metrics = WeatherMetrics(
            date=metrics_data.get("date", ""),
            temp_moyenne=metrics_data.get("temp_moyenne", 0.0),
            temp_min=metrics_data.get("temp_min", 0.0),
            temp_max=metrics_data.get("temp_max", 0.0),
            precip_totale=metrics_data.get("precip_totale", 0.0),
            vent_moyen=metrics_data.get("vent_moyen", 0.0),
            conditions=metrics_data.get("conditions", "Inconnu"),
            impact_mobilite=impact
        )
        
        return {
            "metrics": metrics.to_dict(),
            "impact_mobilite": impact,
            "categories": metrics_data.get("categories", [])
        }

