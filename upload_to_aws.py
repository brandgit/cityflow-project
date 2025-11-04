#!/usr/bin/env python3
"""
Script pour charger manuellement les métriques et rapports
depuis les fichiers JSON locaux vers AWS (DynamoDB + S3)

Usage:
    python upload_to_aws.py                    # Upload tout
    python upload_to_aws.py --date 2025-11-04  # Upload date spécifique
    python upload_to_aws.py --type metrics     # Seulement métriques
    python upload_to_aws.py --type reports     # Seulement rapports
"""

import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Charger les variables d'environnement
from dotenv import load_dotenv
load_dotenv()

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    print("❌ boto3 n'est pas installé")
    print("   pip install boto3")
    exit(1)


class AWSUploader:
    """Classe pour uploader les données vers AWS"""
    
    def __init__(self):
        """Initialise les clients AWS"""
        self.region = os.getenv("AWS_REGION", "eu-west-3")
        
        # Tables DynamoDB
        self.metrics_table_name = os.getenv("DYNAMODB_METRICS_TABLE", "cityflow-metrics")
        self.reports_table_name = os.getenv("DYNAMODB_REPORTS_TABLE", "cityflow-reports")
        
        # Buckets S3
        self.reports_bucket = os.getenv("S3_REPORTS_BUCKET", "cityflow-reports-paris")
        self.reports_prefix = os.getenv("S3_REPORTS_PREFIX", "reports")
        
        # Clients AWS
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.s3 = boto3.client('s3', region_name=self.region)
            
            # Tables
            self.metrics_table = self.dynamodb.Table(self.metrics_table_name)
            self.reports_table = self.dynamodb.Table(self.reports_table_name)
            
            print(f"✓ Connecté à AWS région {self.region}")
            
        except Exception as e:
            print(f"❌ Erreur connexion AWS: {e}")
            exit(1)
    
    def upload_metrics_file(self, file_path: Path) -> bool:
        """
        Upload un fichier de métriques vers DynamoDB
        
        Args:
            file_path: Chemin du fichier JSON
        
        Returns:
            True si succès
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extraire les infos
            metric_type = data.get("metric_type")
            date = data.get("date")
            metrics = data.get("metrics")
            
            if not metric_type or not date or not metrics:
                print(f"  ⚠ Fichier invalide (champs manquants): {file_path.name}")
                return False
            
            # Préparer l'item DynamoDB
            item = {
                "metric_type": metric_type,
                "date": date,
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "metrics": metrics,
                "ttl": int((datetime.now().timestamp() + (365 * 24 * 3600)))  # TTL 1 an
            }
            
            # Upload vers DynamoDB
            self.metrics_table.put_item(Item=item)
            
            print(f"  ✓ Métriques uploadées: {metric_type} - {date}")
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur upload {file_path.name}: {e}")
            return False
    
    def upload_report_file(self, file_path: Path) -> bool:
        """
        Upload un fichier de rapport vers DynamoDB et S3
        
        Args:
            file_path: Chemin du fichier JSON
        
        Returns:
            True si succès
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extraire les infos
            report_id = data.get("report_id")
            date = data.get("date")
            report = data.get("report")
            
            if not report_id or not date or not report:
                print(f"  ⚠ Fichier invalide (champs manquants): {file_path.name}")
                return False
            
            # 1. Upload vers DynamoDB
            item = {
                "report_id": report_id,
                "date": date,
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "report": report,
                "ttl": int((datetime.now().timestamp() + (365 * 24 * 3600)))  # TTL 1 an
            }
            
            self.reports_table.put_item(Item=item)
            print(f"  ✓ Rapport DynamoDB: {date}")
            
            # 2. Upload vers S3 (JSON complet)
            s3_key = f"{self.reports_prefix}/daily_report_{date}.json"
            self.s3.put_object(
                Bucket=self.reports_bucket,
                Key=s3_key,
                Body=json.dumps(data, indent=2, ensure_ascii=False, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            print(f"  ✓ Rapport S3: s3://{self.reports_bucket}/{s3_key}")
            
            # 3. Upload CSV si existe
            csv_path = file_path.parent / f"daily_report_{date}.csv"
            if csv_path.exists():
                s3_csv_key = f"{self.reports_prefix}/daily_report_{date}.csv"
                self.s3.upload_file(
                    str(csv_path),
                    self.reports_bucket,
                    s3_csv_key,
                    ExtraArgs={'ContentType': 'text/csv'}
                )
                print(f"  ✓ Rapport CSV S3: s3://{self.reports_bucket}/{s3_csv_key}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur upload {file_path.name}: {e}")
            return False
    
    def upload_all_metrics(self, date_filter: str = None) -> Dict[str, int]:
        """
        Upload toutes les métriques
        
        Args:
            date_filter: Date spécifique (YYYY-MM-DD) ou None pour toutes
        
        Returns:
            Statistiques d'upload {success: X, failed: Y}
        """
        metrics_dir = Path("output/metrics")
        
        if not metrics_dir.exists():
            print(f"❌ Répertoire métriques non trouvé: {metrics_dir}")
            return {"success": 0, "failed": 0}
        
        print("\n📊 Upload des métriques vers DynamoDB...")
        print(f"   Table: {self.metrics_table_name}")
        print(f"   Répertoire: {metrics_dir}")
        
        success = 0
        failed = 0
        
        # Lister les fichiers
        pattern = f"*_metrics_{date_filter}.json" if date_filter else "*_metrics_*.json"
        files = sorted(metrics_dir.glob(pattern))
        
        if not files:
            print(f"  ⚠ Aucun fichier trouvé avec le pattern: {pattern}")
            return {"success": 0, "failed": 0}
        
        print(f"  → {len(files)} fichier(s) trouvé(s)\n")
        
        for file_path in files:
            if self.upload_metrics_file(file_path):
                success += 1
            else:
                failed += 1
        
        return {"success": success, "failed": failed}
    
    def upload_all_reports(self, date_filter: str = None) -> Dict[str, int]:
        """
        Upload tous les rapports
        
        Args:
            date_filter: Date spécifique (YYYY-MM-DD) ou None pour tous
        
        Returns:
            Statistiques d'upload {success: X, failed: Y}
        """
        reports_dir = Path("output/reports")
        
        if not reports_dir.exists():
            print(f"❌ Répertoire rapports non trouvé: {reports_dir}")
            return {"success": 0, "failed": 0}
        
        print("\n📈 Upload des rapports vers DynamoDB + S3...")
        print(f"   Table: {self.reports_table_name}")
        print(f"   Bucket: {self.reports_bucket}")
        print(f"   Répertoire: {reports_dir}")
        
        success = 0
        failed = 0
        
        # Lister les fichiers JSON
        pattern = f"daily_report_{date_filter}.json" if date_filter else "daily_report_*.json"
        files = sorted(reports_dir.glob(pattern))
        
        if not files:
            print(f"  ⚠ Aucun fichier trouvé avec le pattern: {pattern}")
            return {"success": 0, "failed": 0}
        
        print(f"  → {len(files)} fichier(s) trouvé(s)\n")
        
        for file_path in files:
            if self.upload_report_file(file_path):
                success += 1
            else:
                failed += 1
        
        return {"success": success, "failed": failed}


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Upload les données JSON vers AWS (DynamoDB + S3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python upload_to_aws.py                      # Tout uploader
  python upload_to_aws.py --date 2025-11-04    # Date spécifique
  python upload_to_aws.py --type metrics       # Seulement métriques
  python upload_to_aws.py --type reports       # Seulement rapports
  python upload_to_aws.py --dry-run            # Simulation (pas d'upload)
        """
    )
    
    parser.add_argument(
        "--date",
        help="Date spécifique à uploader (YYYY-MM-DD)",
        metavar="DATE"
    )
    
    parser.add_argument(
        "--type",
        choices=["metrics", "reports", "all"],
        default="all",
        help="Type de données à uploader (défaut: all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (liste les fichiers sans uploader)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  🚀 CityFlow - Upload vers AWS")
    print("=" * 70)
    
    # Mode dry-run
    if args.dry_run:
        print("\n⚠️  MODE SIMULATION (--dry-run)")
        print("   Aucun fichier ne sera uploadé\n")
        
        # Lister les fichiers qui seraient uploadés
        if args.type in ["metrics", "all"]:
            metrics_dir = Path("output/metrics")
            pattern = f"*_metrics_{args.date}.json" if args.date else "*_metrics_*.json"
            files = sorted(metrics_dir.glob(pattern))
            print(f"📊 Métriques à uploader: {len(files)} fichier(s)")
            for f in files[:5]:
                print(f"   - {f.name}")
            if len(files) > 5:
                print(f"   ... et {len(files) - 5} autre(s)")
        
        if args.type in ["reports", "all"]:
            reports_dir = Path("output/reports")
            pattern = f"daily_report_{args.date}.json" if args.date else "daily_report_*.json"
            files = sorted(reports_dir.glob(pattern))
            print(f"\n📈 Rapports à uploader: {len(files)} fichier(s)")
            for f in files[:5]:
                print(f"   - {f.name}")
            if len(files) > 5:
                print(f"   ... et {len(files) - 5} autre(s)")
        
        print("\n💡 Pour uploader réellement, relancez sans --dry-run")
        return
    
    # Upload réel
    try:
        uploader = AWSUploader()
        
        total_success = 0
        total_failed = 0
        
        # Upload métriques
        if args.type in ["metrics", "all"]:
            stats = uploader.upload_all_metrics(args.date)
            total_success += stats["success"]
            total_failed += stats["failed"]
        
        # Upload rapports
        if args.type in ["reports", "all"]:
            stats = uploader.upload_all_reports(args.date)
            total_success += stats["success"]
            total_failed += stats["failed"]
        
        # Résumé
        print("\n" + "=" * 70)
        print("  ✅ UPLOAD TERMINÉ")
        print("=" * 70)
        print(f"  ✓ Succès: {total_success}")
        if total_failed > 0:
            print(f"  ✗ Échecs: {total_failed}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload annulé par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        exit(1)


if __name__ == "__main__":
    main()

