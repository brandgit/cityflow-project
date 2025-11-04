"""
Services AWS : DynamoDB et S3
Utilisé pour stocker métriques et rapports
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("⚠ boto3 non disponible, utilisation mode simulation (local)")


class DynamoDBService:
    """Service pour interagir avec DynamoDB"""
    
    def __init__(self, table_name: str, region_name: Optional[str] = None):
        """
        Initialise le service DynamoDB
        
        Args:
            table_name: Nom de la table DynamoDB
            region_name: Région AWS (défaut: depuis env ou eu-west-3)
        """
        self.table_name = table_name
        self.region_name = region_name or os.getenv("AWS_REGION", "eu-west-3")
        
        if BOTO3_AVAILABLE:
            try:
                self.dynamodb = boto3.resource("dynamodb", region_name=self.region_name)
                self.table = self.dynamodb.Table(table_name)
            except Exception as e:
                print(f"⚠ Erreur initialisation DynamoDB: {e}")
                self.table = None
        else:
            self.table = None
            print("⚠ Mode simulation DynamoDB (boto3 non disponible)")
    
    def put_item(self, item: Dict[str, Any]) -> bool:
        """
        Insère ou met à jour un élément dans DynamoDB
        
        Args:
            item: Élément à insérer (dict)
        
        Returns:
            True si succès
        """
        if not self.table:
            print(f"[SIMULATION] DynamoDB.put_item({self.table_name}): {json.dumps(item, default=str)[:100]}...")
            return True
        
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"✗ Erreur DynamoDB.put_item: {e}")
            return False
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Récupère un élément depuis DynamoDB
        
        Args:
            key: Clé primaire de l'élément
        
        Returns:
            Élément ou None
        """
        if not self.table:
            print(f"[SIMULATION] DynamoDB.get_item({self.table_name}, key={key})")
            return None
        
        try:
            response = self.table.get_item(Key=key)
            return response.get("Item")
        except ClientError as e:
            print(f"✗ Erreur DynamoDB.get_item: {e}")
            return None
    
    def query_by_date(self, date: str, date_field: str = "date") -> List[Dict[str, Any]]:
        """
        Interroge DynamoDB par date
        
        Args:
            date: Date au format YYYY-MM-DD
            date_field: Nom du champ date
        
        Returns:
            Liste des éléments
        """
        if not self.table:
            print(f"[SIMULATION] DynamoDB.query_by_date({self.table_name}, date={date})")
            return []
        
        try:
            from boto3.dynamodb.conditions import Key, Attr
            response = self.table.scan(
                FilterExpression=Attr(date_field).eq(date)
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"✗ Erreur DynamoDB.query_by_date: {e}")
            return []


class S3Service:
    """Service pour interagir avec S3"""
    
    def __init__(self, bucket_name: str, region_name: Optional[str] = None):
        """
        Initialise le service S3
        
        Args:
            bucket_name: Nom du bucket S3
            region_name: Région AWS (défaut: depuis env ou eu-west-3)
        """
        self.bucket_name = bucket_name
        self.region_name = region_name or os.getenv("AWS_REGION", "eu-west-3")
        
        if BOTO3_AVAILABLE:
            try:
                self.s3 = boto3.client("s3", region_name=self.region_name)
            except Exception as e:
                print(f"⚠ Erreur initialisation S3: {e}")
                self.s3 = None
        else:
            self.s3 = None
            print("⚠ Mode simulation S3 (boto3 non disponible)")
    
    def read_json_from_s3(self, key: str) -> Optional[Dict]:
        """
        Lit un fichier JSON ou JSONL directement depuis S3
        
        Args:
            key: Clé S3 du fichier
        
        Returns:
            Dict avec les données ou None
        """
        if not self.s3:
            return None
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            # Si JSONL (JSON Lines), lire ligne par ligne
            if key.endswith('.jsonl'):
                lines = content.strip().split('\n')
                data = []
                for line in lines:
                    if line.strip():
                        data.append(json.loads(line))
                # Retourner au format attendu
                return {"data": data} if data else None
            else:
                # JSON normal
                return json.loads(content)
        except Exception as e:
            print(f"⚠ Erreur lecture S3 {key}: {e}")
            return None
    
    def read_csv_from_s3(self, key: str) -> Optional[str]:
        """
        Lit un fichier CSV directement depuis S3
        
        Args:
            key: Clé S3 du fichier
        
        Returns:
            Contenu CSV en string ou None
        """
        if not self.s3:
            return None
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8-sig')
            return content
        except Exception as e:
            print(f"⚠ Erreur lecture S3 {key}: {e}")
            return None
    
    def list_files_in_s3(self, prefix: str, extension: str = None) -> List[str]:
        """
        Liste les fichiers dans un préfixe S3
        
        Args:
            prefix: Préfixe S3 (ex: "cityflow-raw/raw/batch/")
            extension: Extension optionnelle (ex: ".csv", ".jsonl")
        
        Returns:
            Liste des clés S3
        """
        if not self.s3:
            return []
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' not in response:
                return []
            
            files = [obj['Key'] for obj in response['Contents']]
            
            # Filtrer par extension si spécifié
            if extension:
                files = [f for f in files if f.endswith(extension)]
            
            # Exclure les "dossiers" (clés se terminant par /)
            files = [f for f in files if not f.endswith('/')]
            
            return files
        except Exception as e:
            print(f"⚠ Erreur listage S3 {prefix}: {e}")
            return []
    
    def upload_file(self, local_path: str, s3_key: str, content_type: Optional[str] = None) -> bool:
        """
        Upload un fichier vers S3
        
        Args:
            local_path: Chemin local du fichier
            s3_key: Clé S3 (chemin dans le bucket)
            content_type: Type MIME (défaut: auto-détecté)
        
        Returns:
            True si succès
        """
        if not self.s3:
            print(f"[SIMULATION] S3.upload_file({self.bucket_name}/{s3_key})")
            return True
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3.upload_file(local_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            print(f"✗ Erreur S3.upload_file: {e}")
            return False
    
    def upload_bytes(self, data: bytes, s3_key: str, content_type: Optional[str] = None) -> bool:
        """
        Upload des données bytes vers S3
        
        Args:
            data: Données à uploader (bytes)
            s3_key: Clé S3 (chemin dans le bucket)
            content_type: Type MIME
        
        Returns:
            True si succès
        """
        if not self.s3:
            print(f"[SIMULATION] S3.upload_bytes({self.bucket_name}/{s3_key}, size={len(data)})")
            return True
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3.put_object(Bucket=self.bucket_name, Key=s3_key, Body=data, **extra_args)
            return True
        except ClientError as e:
            print(f"✗ Erreur S3.upload_bytes: {e}")
            return False
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Télécharge un fichier depuis S3
        
        Args:
            s3_key: Clé S3
            local_path: Chemin local de destination
        
        Returns:
            True si succès
        """
        if not self.s3:
            print(f"[SIMULATION] S3.download_file({self.bucket_name}/{s3_key})")
            return False
        
        try:
            self.s3.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            print(f"✗ Erreur S3.download_file: {e}")
            return False
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Vérifie si un fichier existe dans S3
        
        Args:
            s3_key: Clé S3
        
        Returns:
            True si existe
        """
        if not self.s3:
            return False
        
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


def save_metrics_to_dynamodb(metrics: Dict[str, Any], data_type: str, date: str, 
                             table_name: Optional[str] = None) -> bool:
    """
    Sauvegarde des métriques dans DynamoDB
    
    Args:
        metrics: Métriques à sauvegarder
        data_type: Type de données (bikes, traffic, etc.)
        date: Date au format YYYY-MM-DD
        table_name: Nom de la table (défaut: depuis env)
    
    Returns:
        True si succès
    """
    if not table_name:
        table_name = os.getenv("DYNAMODB_METRICS_TABLE", f"cityflow-{data_type}-metrics")
    
    service = DynamoDBService(table_name)
    
    # Préparer l'item DynamoDB
    item = {
        "metric_type": data_type,
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "ttl": int((datetime.now().timestamp() + (365 * 24 * 3600)))  # TTL 1 an
    }
    
    return service.put_item(item)


def save_report_to_s3_csv(csv_content: str, date: str, bucket_name: Optional[str] = None,
                          s3_prefix: Optional[str] = None) -> bool:
    """
    Sauvegarde un rapport CSV dans S3
    
    Args:
        csv_content: Contenu CSV (string)
        date: Date au format YYYY-MM-DD
        bucket_name: Nom du bucket (défaut: depuis env)
        s3_prefix: Préfixe S3 (défaut: depuis env ou "reports/")
    
    Returns:
        True si succès
    """
    if not bucket_name:
        bucket_name = os.getenv("S3_REPORTS_BUCKET", "cityflow-reports")
    
    if not s3_prefix:
        s3_prefix = os.getenv("S3_REPORTS_PREFIX", "reports")
    
    s3_key = f"{s3_prefix}/daily_report_{date}.csv"
    service = S3Service(bucket_name)
    
    csv_bytes = csv_content.encode("utf-8")
    return service.upload_bytes(csv_bytes, s3_key, content_type="text/csv")


def save_report_to_dynamodb(report: Dict[str, Any], date: str,
                            table_name: Optional[str] = None) -> bool:
    """
    Sauvegarde un rapport dans DynamoDB
    
    Args:
        report: Rapport à sauvegarder (dict)
        date: Date au format YYYY-MM-DD
        table_name: Nom de la table (défaut: depuis env)
    
    Returns:
        True si succès
    """
    if not table_name:
        table_name = os.getenv("DYNAMODB_REPORTS_TABLE", "cityflow-daily-reports")
    
    service = DynamoDBService(table_name)
    
    # Préparer l'item DynamoDB
    item = {
        "report_id": f"daily_report_{date}",
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "report": report,
        "ttl": int((datetime.now().timestamp() + (365 * 24 * 3600)))  # TTL 1 an
    }
    
    return service.put_item(item)


def load_metrics_from_dynamodb(data_type: str, date: str,
                               table_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Charge des métriques depuis DynamoDB
    
    Args:
        data_type: Type de données
        date: Date au format YYYY-MM-DD
        table_name: Nom de la table (défaut: depuis env)
    
    Returns:
        Métriques ou None
    """
    if not table_name:
        table_name = os.getenv("DYNAMODB_METRICS_TABLE", f"cityflow-{data_type}-metrics")
    
    service = DynamoDBService(table_name)
    item = service.get_item({"metric_type": data_type, "date": date})
    
    if item:
        return item.get("metrics")
    
    return None

