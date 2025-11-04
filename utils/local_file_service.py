"""
Service pour gérer les métriques et rapports via fichiers JSON locaux
Utilisé sur EC2 avant chargement manuel vers AWS
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.database_service import DatabaseService


class LocalFileService(DatabaseService):
    """Service pour stocker métriques et rapports dans des fichiers JSON locaux"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialise le service de fichiers locaux
        
        Args:
            base_dir: Répertoire de base (défaut: output/)
        """
        # Utiliser OUTPUT_DIR de .env ou "output" par défaut
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            output_dir = os.getenv("OUTPUT_DIR", "output")
            self.base_dir = Path(output_dir)
            
            # Si le chemin n'existe pas et n'est pas relatif, utiliser "output" local
            if not self.base_dir.exists() and self.base_dir.is_absolute():
                print(f"  ⚠ Chemin {output_dir} n'existe pas, utilisation de 'output' local")
                self.base_dir = Path("output")
        
        self.metrics_dir = self.base_dir / "metrics"
        self.reports_dir = self.base_dir / "reports"
        
        # Créer les répertoires s'ils n'existent pas
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"✗ Erreur création répertoires: {e}")
            # Fallback sur chemin relatif
            self.base_dir = Path("output")
            self.metrics_dir = self.base_dir / "metrics"
            self.reports_dir = self.base_dir / "reports"
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        print("✓ Service fichiers locaux initialisé")
        print(f"  📁 Métriques: {self.metrics_dir}")
        print(f"  📁 Rapports: {self.reports_dir}")
    
    def _get_metrics_path(self, data_type: str, date: str) -> Path:
        """Retourne le chemin du fichier de métriques"""
        return self.metrics_dir / f"{data_type}_metrics_{date}.json"
    
    def _get_report_path(self, date: str) -> Path:
        """Retourne le chemin du fichier de rapport"""
        return self.reports_dir / f"daily_report_{date}.json"
    
    def save_metrics(self, metrics: Dict[str, Any], data_type: str, date: str) -> bool:
        """
        Sauvegarde des métriques dans un fichier JSON local
        
        Args:
            metrics: Métriques à sauvegarder
            data_type: Type de données (bikes, traffic, weather, etc.)
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        try:
            file_path = self._get_metrics_path(data_type, date)
            
            # Préparer les données avec métadonnées
            data = {
                "metric_type": data_type,
                "date": date,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics
            }
            
            # Sauvegarder
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"  ✓ Métriques {data_type} sauvegardées: {file_path}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur sauvegarde métriques {data_type}: {e}")
            return False
    
    def load_metrics(self, data_type: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge des métriques depuis un fichier JSON local
        
        Args:
            data_type: Type de données
            date: Date au format YYYY-MM-DD
        
        Returns:
            Métriques ou None si non trouvées
        """
        try:
            file_path = self._get_metrics_path(data_type, date)
            
            if not file_path.exists():
                print(f"  ⚠ Fichier métriques non trouvé: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"  ✓ Métriques {data_type} chargées depuis: {file_path.name}")
            return data.get("metrics")
            
        except Exception as e:
            print(f"✗ Erreur chargement métriques {data_type}: {e}")
            return None
    
    def save_report(self, report: Dict[str, Any], date: str) -> bool:
        """
        Sauvegarde un rapport dans un fichier JSON local
        
        Args:
            report: Rapport à sauvegarder
            date: Date au format YYYY-MM-DD
        
        Returns:
            True si succès
        """
        try:
            file_path = self._get_report_path(date)
            
            # Préparer les données avec métadonnées
            data = {
                "report_id": f"daily_report_{date}",
                "date": date,
                "timestamp": datetime.now().isoformat(),
                "report": report
            }
            
            # Sauvegarder
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"  ✓ Rapport sauvegardé: {file_path}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur sauvegarde rapport: {e}")
            return False
    
    def load_report(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Charge un rapport depuis un fichier JSON local
        
        Args:
            date: Date au format YYYY-MM-DD
        
        Returns:
            Rapport ou None si non trouvé
        """
        try:
            file_path = self._get_report_path(date)
            
            if not file_path.exists():
                print(f"  ⚠ Fichier rapport non trouvé: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"  ✓ Rapport chargé depuis: {file_path.name}")
            return data.get("report")
            
        except Exception as e:
            print(f"✗ Erreur chargement rapport: {e}")
            return None
    
    def query_metrics_by_date_range(self, data_type: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Interroge les métriques sur une plage de dates
        
        Args:
            data_type: Type de données
            start_date: Date de début (YYYY-MM-DD)
            end_date: Date de fin (YYYY-MM-DD)
        
        Returns:
            Liste des métriques
        """
        results = []
        
        try:
            # Lister tous les fichiers de métriques pour ce type
            pattern = f"{data_type}_metrics_*.json"
            for file_path in self.metrics_dir.glob(pattern):
                # Extraire la date du nom de fichier
                filename = file_path.stem
                # Format: {data_type}_metrics_{date}
                parts = filename.split('_')
                if len(parts) >= 3:
                    file_date = parts[-1]  # Dernière partie = date
                    
                    # Vérifier si dans la plage
                    if start_date <= file_date <= end_date:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            results.append({
                                "date": data.get("date", file_date),
                                "metrics": data.get("metrics")
                            })
            
            # Trier par date
            results.sort(key=lambda x: x.get("date", ""))
            
            print(f"  ✓ {len(results)} fichier(s) de métriques {data_type} trouvé(s) pour {start_date} à {end_date}")
            return results
            
        except Exception as e:
            print(f"✗ Erreur query métriques {data_type}: {e}")
            return []
    
    def list_available_dates(self, data_type: str) -> List[str]:
        """
        Liste toutes les dates disponibles pour un type de données
        
        Args:
            data_type: Type de données
        
        Returns:
            Liste des dates (YYYY-MM-DD)
        """
        dates = []
        
        try:
            pattern = f"{data_type}_metrics_*.json"
            for file_path in self.metrics_dir.glob(pattern):
                filename = file_path.stem
                parts = filename.split('_')
                if len(parts) >= 3:
                    date = parts[-1]
                    dates.append(date)
            
            dates.sort()
            return dates
            
        except Exception as e:
            print(f"✗ Erreur listage dates {data_type}: {e}")
            return []
    
    def get_latest_metrics(self, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les métriques les plus récentes pour un type
        
        Args:
            data_type: Type de données
        
        Returns:
            Métriques ou None
        """
        dates = self.list_available_dates(data_type)
        if not dates:
            return None
        
        latest_date = dates[-1]
        return self.load_metrics(data_type, latest_date)
    
    def close(self):
        """Ferme la connexion (pas nécessaire pour fichiers locaux)"""
        pass

