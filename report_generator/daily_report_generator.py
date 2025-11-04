"""
Générateur de rapport quotidien basé sur les métriques calculées
Module séparé pour exécution indépendante dans AWS
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.daily_report import DailyReport
from report_generator.utils.file_utils import save_json
from config import settings
from utils.database_factory import get_database_service, get_database_type
from utils.aws_services import save_report_to_s3_csv


class DailyReportGenerator:
    """
    Génère le rapport quotidien à partir des métriques calculées
    """
    
    def __init__(self, metrics_dir: Optional[Path] = None, reports_dir: Optional[Path] = None):
        """
        Initialise le générateur de rapport
        
        Args:
            metrics_dir: Répertoire contenant les métriques (défaut: base de données ou local)
            reports_dir: Répertoire pour sauvegarder les rapports (défaut: S3 ou local)
        
        Note: En AWS, métriques depuis DynamoDB, rapports vers S3 et DynamoDB
              En local, métriques depuis MongoDB, rapports en local
        """
        # Obtenir le service de base de données
        try:
            self.db_service = get_database_service()
            self.db_type = get_database_type()
            self.use_database = True
        except Exception as e:
            print(f"⚠ Impossible d'initialiser la base de données: {e}")
            print("  → Utilisation des fichiers locaux uniquement")
            self.db_service = None
            self.db_type = "local"
            self.use_database = False
        
        if metrics_dir:
            self.metrics_dir = Path(metrics_dir)
            self.use_database = False
        else:
            self.metrics_dir = settings.METRICS_DIR
        
        if reports_dir:
            self.reports_dir = Path(reports_dir)
        else:
            self.reports_dir = settings.REPORTS_DIR
        
        # S'assurer que le répertoire reports existe (si local)
        if isinstance(self.reports_dir, Path) and not os.getenv("AWS_EXECUTION_ENV"):
            self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def load_metrics(self, date: str) -> Dict[str, any]:
        """
        Charge toutes les métriques pour une date donnée depuis la base de données ou fichiers locaux
        
        Args:
            date: Date au format YYYY-MM-DD
        
        Returns:
            Dict avec toutes les métriques par type
        """
        metrics = {
            "comptages": None,
            "bikes": None,
            "traffic": None,
            "weather": None,
            "chantiers": None
        }
        
        if self.use_database and self.db_service:
            # Charger depuis la base de données (MongoDB ou DynamoDB)
            for metric_type in metrics.keys():
                try:
                    metric_data = self.db_service.load_metrics(
                        data_type=metric_type,
                        date=date
                    )
                    if metric_data:
                        metrics[metric_type] = metric_data
                        print(f"  ✓ Métriques {metric_type} chargées depuis {self.db_type.upper()}")
                    else:
                        # Fallback : charger depuis fichier local si non disponible en BDD
                        metric_path = self.metrics_dir / f"{metric_type}_metrics_{date}.json"
                        if metric_path.exists():
                            with open(metric_path, 'r', encoding='utf-8') as f:
                                metrics[metric_type] = json.load(f)
                                print(f"  ⚠ Métriques {metric_type} chargées depuis fichier local (fallback)")
                except Exception as e:
                    print(f"⚠ Erreur chargement métriques {metric_type} depuis {self.db_type.upper()}: {e}")
                    # Fallback : essayer depuis fichier local
                    metric_path = self.metrics_dir / f"{metric_type}_metrics_{date}.json"
                    if metric_path.exists():
                        try:
                            with open(metric_path, 'r', encoding='utf-8') as f:
                                metrics[metric_type] = json.load(f)
                                print(f"  → Fallback: métriques {metric_type} chargées depuis fichier local")
                        except Exception as e2:
                            print(f"  ✗ Erreur fallback fichier local: {e2}")
        else:
            # Charger depuis fichiers locaux (développement)
            for metric_type in metrics.keys():
                metric_path = self.metrics_dir / f"{metric_type}_metrics_{date}.json"
                if metric_path.exists():
                    try:
                        with open(metric_path, 'r', encoding='utf-8') as f:
                            metrics[metric_type] = json.load(f)
                            print(f"  ✓ Métriques {metric_type} chargées depuis fichier local")
                    except Exception as e:
                        print(f"⚠ Erreur chargement métriques {metric_type}: {e}")
        
        return metrics
    
    def generate_report(self, date: Optional[str] = None) -> DailyReport:
        """
        Génère le rapport quotidien à partir des métriques
        
        Args:
            date: Date du rapport (défaut: aujourd'hui)
        
        Returns:
            Rapport quotidien
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n{'='*60}")
        print(f"Génération Rapport Quotidien - {date}")
        print(f"{'='*60}")
        
        # Charger toutes les métriques
        print("\n[1/3] Chargement des métriques...")
        metrics = self.load_metrics(date)
        
        loaded_count = sum(1 for v in metrics.values() if v is not None)
        print(f"✓ {loaded_count} fichiers métriques chargés")
        
        # Extraire métriques de chaque source
        print("\n[2/3] Extraction des données...")
        comptages_metrics = metrics.get("comptages", {})
        bikes_metrics = metrics.get("bikes", {})
        weather_metrics = metrics.get("weather", {})
        chantiers_metrics = metrics.get("chantiers", {})
        
        # Summary (gérer le cas où comptages_metrics est None ou version summary)
        # Si version summary depuis MongoDB, charger version complète depuis fichier local
        if comptages_metrics and isinstance(comptages_metrics, dict):
            note = comptages_metrics.get("note", "")
            if note and "disponible dans fichier local" in note:
                # Version summary détectée, charger version complète depuis fichier local
                import json
                comptages_file = self.metrics_dir / f"comptages_metrics_{date}.json"
                if comptages_file.exists():
                    try:
                        with open(comptages_file, 'r', encoding='utf-8') as f:
                            full_comptages = json.load(f)
                            # Le fichier contient directement les indicateurs
                            comptages_metrics = full_comptages
                        print(f"  ℹ Version complète comptages chargée depuis fichier local")
                    except Exception as e:
                        print(f"  ⚠ Erreur chargement version complète: {e}")
        
        global_metrics = comptages_metrics.get("global_metrics", {}) if comptages_metrics else {}
        summary = {
            "total_vehicules_paris": global_metrics.get("total_vehicules_jour", 0),
            "temps_perdu_total_minutes": global_metrics.get("temps_perdu_total_paris", 0),
            "nombre_troncons_satures": global_metrics.get("nombre_troncons_satures", 0),
            "taux_disponibilite_capteurs": global_metrics.get("taux_disponibilite_capteurs", 100.0),
            "total_velos_paris": sum(
                m.get("total_jour", 0) 
                for m in bikes_metrics.get("metrics", []) if bikes_metrics
            )
        }
        
        # Top 10 tronçons fréquentés (gérer None)
        top_10_troncons = comptages_metrics.get("top_10_troncons", [])[:10] if comptages_metrics else []
        print(f"  ✓ Top 10 tronçons: {len(top_10_troncons)} éléments")
        
        # Top 10 zones congestionnées (gérer None)
        top_10_zones = comptages_metrics.get("top_10_zones_congestionnees", [])[:10] if comptages_metrics else []
        print(f"  ✓ Top 10 zones: {len(top_10_zones)} éléments")
        
        # Capteurs défaillants
        capteurs_defaillants = [
            {"id_compteur": sensor_id, "type": "bike"}
            for sensor_id in bikes_metrics.get("failing_sensors", [])
        ]
        print(f"  ✓ Capteurs défaillants: {len(capteurs_defaillants)} éléments")
        
        # Alertes congestion
        alertes_congestion = comptages_metrics.get("alertes_congestion", [])[:20] if comptages_metrics else []
        print(f"  ✓ Alertes congestion: {len(alertes_congestion)} éléments")
        
        # Chantiers actifs (gérer le cas où chantiers_metrics est None)
        chantiers_actifs = chantiers_metrics.get("chantiers_actifs", []) if chantiers_metrics else []
        print(f"  ✓ Chantiers actifs: {len(chantiers_actifs)} éléments")
        
        # Évolution (simplifié - nécessiterait données historiques)
        evolution = {
            "note": "Nécessite données historiques pour comparaison"
        }
        
        # Impact météo (gérer le cas où weather_metrics est None)
        meteo_impact = weather_metrics.get("metrics", {}) if weather_metrics else {}
        
        # Générer rapport
        print("\n[3/3] Génération rapport...")
        report = DailyReport(
            date=date,
            generated_at=datetime.now().isoformat(),
            summary=summary,
            top_10_troncons_frequentes=top_10_troncons,
            top_10_zones_congestionnees=top_10_zones,
            capteurs_defaillants=capteurs_defaillants,
            alertes_congestion=alertes_congestion,
            chantiers_actifs=chantiers_actifs,
            evolution_vs_semaine_precedente=evolution,
            meteo_impact=meteo_impact
        )
        
        print("✓ Rapport généré avec succès")
        
        return report
    
    def export_report(self, report: DailyReport) -> Dict[str, any]:
        """
        Exporte le rapport selon l'environnement :
        
        - AWS Production : JSON → DynamoDB, CSV → S3
        - Local Dev : JSON → MongoDB, CSV → répertoire local
        
        Args:
            report: Rapport quotidien
        
        Returns:
            Dict avec chemins/identifiants des fichiers exportés
        """
        date = report.date
        report_dict = report.to_dict()
        
        # Générer le contenu CSV
        csv_rows = report.to_csv_rows()
        csv_content = "\n".join([";".join([str(cell) for cell in row[:2]]) for row in csv_rows])
        
        results = {}
        is_aws = os.getenv("AWS_EXECUTION_ENV") is not None
        
        # ===================================================================
        # EXPORT CSV : S3 (AWS) ou Répertoire local (Dev)
        # ===================================================================
        if is_aws or os.getenv("USE_S3", "false").lower() == "true":
            # ☁️ AWS : Export CSV vers S3
            print("\n[Export CSV] → S3 Bucket")
            success = save_report_to_s3_csv(
                csv_content=csv_content,
                date=date,
                bucket_name=settings.S3_REPORTS_BUCKET,
                s3_prefix=settings.S3_REPORTS_PREFIX
            )
            if success:
                s3_key = f"{settings.S3_REPORTS_PREFIX}/daily_report_{date}.csv"
                results["csv"] = f"s3://{settings.S3_REPORTS_BUCKET}/{s3_key}"
                print(f"✓ Rapport CSV exporté vers S3: {results['csv']}")
            else:
                print(f"✗ Erreur export CSV vers S3")
        else:
            # 🏠 Local : Export CSV vers répertoire local
            print("\n[Export CSV] → Répertoire local (output/reports/)")
            import csv as csv_module
            report_csv_path = self.reports_dir / f"daily_report_{date}.csv"
            os.makedirs(os.path.dirname(str(report_csv_path)), exist_ok=True)
            
            with open(str(report_csv_path), 'w', encoding='utf-8', newline='') as f:
                writer = csv_module.writer(f, delimiter=';')
                for row in csv_rows:
                    if len(row) == 0:
                        writer.writerow(["", ""])
                    elif len(row) == 1:
                        writer.writerow([row[0], ""])
                    else:
                        writer.writerow(row[:2])
            
            results["csv"] = report_csv_path
            print(f"✓ Rapport CSV: {report_csv_path}")
        
        # ===================================================================
        # EXPORT JSON : DynamoDB (AWS) ou MongoDB (Local)
        # ===================================================================
        if self.use_database and self.db_service:
            # Base de données disponible (MongoDB ou DynamoDB selon config)
            if is_aws:
                print("\n[Export JSON] → DynamoDB")
            else:
                print(f"\n[Export JSON] → {self.db_type.upper()}")
            
            success = self.db_service.save_report(
                report=report_dict,
                date=date
            )
            if success:
                results["json"] = f"{self.db_type.upper()}:daily_report_{date}"
                print(f"✓ Rapport JSON exporté vers {self.db_type.upper()}")
            else:
                print(f"✗ Erreur export JSON vers {self.db_type.upper()}")
        else:
            # Fallback : Export local si base de données non disponible
            print("\n[Export JSON] → Répertoire local (fallback)")
            report_json_path = self.reports_dir / f"daily_report_{date}.json"
            save_json(report_dict, str(report_json_path))
            results["json"] = report_json_path
            print(f"✓ Rapport JSON: {report_json_path}")
        
        # Fermer connexion MongoDB si applicable
        if self.db_service and hasattr(self.db_service, 'close'):
            self.db_service.close()
        
        print("\n" + "=" * 60)
        if is_aws:
            print("☁️  Rapport exporté en mode AWS PRODUCTION")
            print("   - CSV : S3 Bucket")
            print("   - JSON : DynamoDB")
        else:
            print("🏠 Rapport exporté en mode LOCAL DÉVELOPPEMENT")
            print("   - CSV : Répertoire local (output/reports/)")
            print(f"   - JSON : {self.db_type.upper()}")
        print("=" * 60)
        
        return results
    
    def generate_and_export(self, date: Optional[str] = None) -> Dict[str, Path]:
        """
        Génère et exporte le rapport en une seule opération
        
        Args:
            date: Date du rapport (défaut: aujourd'hui)
        
        Returns:
            Dict avec chemins des fichiers exportés
        """
        report = self.generate_report(date)
        return self.export_report(report)

