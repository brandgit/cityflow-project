"""
Modèle de rapport quotidien
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DailyReport:
    """Rapport quotidien complet"""
    date: str
    generated_at: str
    summary: Dict = field(default_factory=dict)
    top_10_troncons_frequentes: List[Dict] = field(default_factory=list)
    top_10_zones_congestionnees: List[Dict] = field(default_factory=list)
    capteurs_defaillants: List[Dict] = field(default_factory=list)
    alertes_congestion: List[Dict] = field(default_factory=list)
    chantiers_actifs: List[Dict] = field(default_factory=list)
    evolution_vs_semaine_precedente: Dict = field(default_factory=dict)
    meteo_impact: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour export JSON"""
        return {
            "date": self.date,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "top_10_troncons_frequentes": self.top_10_troncons_frequentes,
            "top_10_zones_congestionnees": self.top_10_zones_congestionnees,
            "capteurs_defaillants": self.capteurs_defaillants,
            "alertes_congestion": self.alertes_congestion,
            "chantiers_actifs": self.chantiers_actifs,
            "evolution_vs_semaine_precedente": self.evolution_vs_semaine_precedente,
            "meteo_impact": self.meteo_impact
        }
    
    def to_csv_rows(self) -> List[List[str]]:
        """Convertit en lignes CSV"""
        rows = []
        
        # Header
        rows.append(["Section", "Valeur"])
        
        # Summary
        rows.append(["Total véhicules Paris", str(self.summary.get("total_vehicules_paris", 0))])
        rows.append(["Temps perdu total (min)", str(self.summary.get("temps_perdu_total_minutes", 0))])
        rows.append(["Tronçons saturés", str(self.summary.get("nombre_troncons_satures", 0))])
        rows.append(["Taux disponibilité capteurs (%)", str(self.summary.get("taux_disponibilite_capteurs", 100.0))])
        rows.append(["Total vélos Paris", str(self.summary.get("total_velos_paris", 0))])
        
        # Ligne vide pour séparation
        rows.append(["", ""])
        
        # Top 10 Tronçons
        rows.append(["=== TOP 10 TRONÇONS FRÉQUENTÉS ===", ""])
        if self.top_10_troncons_frequentes:
            rows.append(["Tronçon", "Débit Total"])
            for item in self.top_10_troncons_frequentes[:10]:
                libelle = item.get("libelle", item.get("identifiant_arc", "N/A"))
                debit = item.get("debit_journalier_total", item.get("debit_total", 0))
                rows.append([libelle, str(debit)])
        else:
            rows.append(["Aucune donnée disponible", ""])
        
        # Ligne vide pour séparation
        rows.append(["", ""])
        
        # Top 10 Zones Congestionnées
        rows.append(["=== TOP 10 ZONES CONGESTIONNÉES ===", ""])
        if self.top_10_zones_congestionnees:
            rows.append(["Zone", "Temps Perdu (min)"])
            for item in self.top_10_zones_congestionnees[:10]:
                zone = item.get("arrondissement", item.get("libelle", "N/A"))
                temps_perdu = item.get("temps_perdu_total_minutes", item.get("temps_perdu_total", 0))
                rows.append([zone, str(temps_perdu)])
        else:
            rows.append(["Aucune donnée disponible", ""])
        
        # Ligne vide pour séparation
        rows.append(["", ""])
        
        # Capteurs défaillants
        rows.append(["=== CAPTEURS DÉFAILLANTS ===", ""])
        if self.capteurs_defaillants:
            rows.append(["ID Capteur", "Type"])
            for capteur in self.capteurs_defaillants[:20]:  # Limiter à 20
                rows.append([
                    capteur.get("id_compteur", capteur.get("identifiant_arc", "N/A")),
                    capteur.get("type", "N/A")
                ])
        else:
            rows.append(["Aucun capteur défaillant", ""])
        
        # Ligne vide pour séparation
        rows.append(["", ""])
        
        # Alertes congestion
        rows.append(["=== ALERTES CONGESTION ===", ""])
        if self.alertes_congestion:
            rows.append(["Tronçon", "Taux Occupation (%)", "Sévérité"])
            for alerte in self.alertes_congestion[:20]:  # Limiter à 20
                rows.append([
                    alerte.get("libelle", alerte.get("identifiant_arc", "N/A")),
                    str(alerte.get("taux_occupation_moyen", alerte.get("taux_occupation", 0))),
                    alerte.get("severite", "Élevée")
                ])
        else:
            rows.append(["Aucune alerte", ""])
        
        # Ligne vide pour séparation
        rows.append(["", ""])
        
        # Chantiers actifs
        rows.append(["=== CHANTIERS ACTIFS ===", ""])
        if self.chantiers_actifs:
            rows.append(["Identifiant", "Typologie", "Impact", "Arrondissement"])
            for chantier in self.chantiers_actifs[:20]:  # Limiter à 20
                rows.append([
                    chantier.get("identifiant", "N/A"),
                    chantier.get("typologie", "N/A"),
                    chantier.get("impact", "N/A"),
                    chantier.get("arrondissement", "N/A")
                ])
        else:
            rows.append(["Aucun chantier actif", ""])
        
        return rows

