"""
Processeur pour les données API Traffic (perturbations RATP)
"""

from typing import List, Dict, Any, Set
import re
from processors.base_processor import BaseProcessor
from processors.utils.validators import validate_date_iso
from processors.utils.time_utils import parse_iso_date, calculate_time_difference
from config import SEVERITE_RATP

# Lignes de métro valides à Paris (1-14)
LIGNES_METRO_VALIDES: Set[str] = {str(i) for i in range(1, 15)}  # "1" à "14"


class TrafficProcessor(BaseProcessor):
    """Processeur pour les perturbations trafic RATP"""
    
    def validate_and_clean(self, data: Dict) -> List[Dict]:
        """
        Validation et nettoyage des données disruptions
        
        Args:
            data: Dict avec clé "disruptions"
        
        Returns:
            Liste des disruptions validées
        """
        disruptions = data.get("disruptions", [])
        cleaned = []
        
        for disruption in disruptions:
            # Valider dates application_periods
            periods = disruption.get("application_periods", [])
            valid_periods = []
            
            for period in periods:
                begin_str = period.get("begin", "")
                end_str = period.get("end", "")
                
                begin_date = parse_iso_date(begin_str)
                end_date = parse_iso_date(end_str)
                
                if begin_date and end_date:
                    valid_periods.append({
                        "begin": begin_date,
                        "end": end_date,
                        "begin_str": begin_str,
                        "end_str": end_str
                    })
            
            if not valid_periods:
                continue  # Pas de période valide
            
            # Extraire lignes depuis messages
            lignes_impactees = []
            messages = disruption.get("messages", [])
            for msg in messages:
                text = msg.get("text", "")
                # Extraction simple (dans un vrai projet, utiliser NLP)
                if "Ligne" in text:
                    # Tente d'extraire numéro ligne
                    matches = re.findall(r'Ligne\s+(\d+)', text)
                    # Filtrer pour ne garder que les lignes de métro valides (1-14)
                    lignes_metro = [m for m in matches if m in LIGNES_METRO_VALIDES]
                    lignes_impactees.extend(lignes_metro)
            
            # Vérifier aussi dans la catégorie (ex: "METRO", "BUS", etc.)
            category = disruption.get("category", "")
            if category and "METRO" in category.upper():
                # Essayer d'extraire depuis catégorie si disponible
                cat_matches = re.findall(r'(\d+)', category)
                lignes_metro_cat = [m for m in cat_matches if m in LIGNES_METRO_VALIDES]
                lignes_impactees.extend(lignes_metro_cat)
            
            cleaned_disruption = {
                "id": disruption.get("id", ""),
                "disruption_id": disruption.get("disruption_id", ""),
                "status": disruption.get("status", ""),
                "application_periods": valid_periods,
                "severity": disruption.get("severity", {}),
                "priority": disruption.get("severity", {}).get("priority", 0),
                "lignes_impactees": list(set(lignes_impactees)),  # Déduplication
                "cause": disruption.get("cause", ""),
                "category": disruption.get("category", "")
            }
            
            cleaned.append(cleaned_disruption)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        Agrégations quotidiennes disruptions
        
        Args:
            cleaned_data: Liste des disruptions nettoyées
        
        Returns:
            Dict avec agrégations
        """
        active_disruptions = []
        disruptions_by_severity = {"CRITIQUE": 0, "ELEVEE": 0, "MOYENNE": 0, "FAIBLE": 0}
        lignes_impactees_count = {}
        total_duration_hours = 0.0
        
        for disruption in cleaned_data:
            status = disruption.get("status", "")
            if status == "active":
                active_disruptions.append(disruption)
            
            # Catégoriser par sévérité
            priority = disruption.get("priority", 0)
            if priority >= SEVERITE_RATP["CRITIQUE"]:
                disruptions_by_severity["CRITIQUE"] += 1
            elif priority >= SEVERITE_RATP["ELEVEE"]:
                disruptions_by_severity["ELEVEE"] += 1
            elif priority >= SEVERITE_RATP["MOYENNE"]:
                disruptions_by_severity["MOYENNE"] += 1
            else:
                disruptions_by_severity["FAIBLE"] += 1
            
            # Compter lignes impactées (uniquement métro valides)
            for ligne in disruption.get("lignes_impactees", []):
                if ligne in LIGNES_METRO_VALIDES:  # Double vérification
                    lignes_impactees_count[ligne] = lignes_impactees_count.get(ligne, 0) + 1
            
            # Calculer durée totale
            for period in disruption.get("application_periods", []):
                begin = period.get("begin")
                end = period.get("end")
                if begin and end:
                    duration = calculate_time_difference(begin, end)
                    total_duration_hours += duration
        
        return {
            "active_disruptions": active_disruptions,
            "disruptions_by_severity": disruptions_by_severity,
            "lignes_impactees_count": lignes_impactees_count,
            "total_duration_hours": total_duration_hours,
            "total_disruptions": len(cleaned_data)
        }
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Calculs d'indicateurs disruptions
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec indicateurs
        """
        from utils.traffic_calculations import calculate_traffic_reliability_index
        
        active_count = len(aggregated_data.get("active_disruptions", []))
        total_count = aggregated_data.get("total_disruptions", 0)
        
        # Indice de fiabilité
        reliability_index = calculate_traffic_reliability_index(
            aggregated_data.get("active_disruptions", []),
            disruption_field="status"
        )
        
        # Top lignes impactées (uniquement métro valides)
        lignes_count = aggregated_data.get("lignes_impactees_count", {})
        # Filtrer pour ne garder que les lignes de métro valides
        lignes_metro_count = {l: c for l, c in lignes_count.items() if l in LIGNES_METRO_VALIDES}
        top_lignes = sorted(
            lignes_metro_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Alertes (disruptions critiques)
        alerts = []
        for disruption in aggregated_data.get("active_disruptions", []):
            priority = disruption.get("priority", 0)
            duration = 0.0
            
            for period in disruption.get("application_periods", []):
                begin = period.get("begin")
                end = period.get("end")
                if begin and end:
                    duration += calculate_time_difference(begin, end)
            
            # Filtrer les lignes pour ne garder que les métro valides
            lignes_impactees = disruption.get("lignes_impactees", [])
            lignes_metro = [l for l in lignes_impactees if l in LIGNES_METRO_VALIDES]
            
            # Inclure les alertes critiques OU avec durée > 2h
            # Mais exclure les alertes sans lignes si elles sont de priorité faible
            if priority >= SEVERITE_RATP["CRITIQUE"] or duration > 2.0:
                # Si priorité faible et pas de lignes, exclure (perturbations générales non pertinentes)
                if priority < SEVERITE_RATP["ELEVEE"] and not lignes_metro:
                    continue
                
                alerts.append({
                    "id": disruption.get("id", ""),
                    "priority": priority,
                    "duration_hours": duration,
                    "lignes": lignes_metro  # Uniquement lignes métro valides
                })
        
        return {
            "reliability_index": reliability_index,
            "active_disruptions_count": active_count,
            "total_disruptions_count": total_count,
            "top_lignes_impactees": [{"ligne": l, "count": c} for l, c in top_lignes],
            "alerts": alerts,
            "disruptions_by_severity": aggregated_data.get("disruptions_by_severity", {})
        }

