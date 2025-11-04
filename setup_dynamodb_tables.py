#!/usr/bin/env python3
"""
Script pour créer automatiquement les tables DynamoDB nécessaires pour CityFlow
Usage: python3 setup_dynamodb_tables.py
"""

import sys
import time

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("❌ boto3 non installé. Installez-le avec: pip install boto3")
    sys.exit(1)


def create_table(dynamodb, table_name, partition_key, sort_key, region):
    """
    Crée une table DynamoDB
    
    Args:
        dynamodb: Client DynamoDB
        table_name: Nom de la table
        partition_key: Nom de la partition key
        sort_key: Nom de la sort key
        region: Région AWS
    
    Returns:
        True si succès
    """
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': partition_key,
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': sort_key,
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': partition_key,
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': sort_key,
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # Mode on-demand (pas besoin de provisionner)
        )
        
        # Attendre que la table soit créée
        print(f"  ⏳ Création de la table {table_name} en cours...")
        table.wait_until_exists()
        print(f"  ✅ Table {table_name} créée avec succès")
        return True
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"  ℹ️  Table {table_name} existe déjà")
            return True
        else:
            print(f"  ❌ Erreur création {table_name}: {e}")
            return False
    except Exception as e:
        print(f"  ❌ Erreur inattendue: {e}")
        return False


def verify_table(dynamodb, table_name):
    """
    Vérifie qu'une table existe et est active
    
    Args:
        dynamodb: Client DynamoDB
        table_name: Nom de la table
    
    Returns:
        True si la table existe et est active
    """
    try:
        table = dynamodb.Table(table_name)
        table.load()
        
        status = table.table_status
        if status == 'ACTIVE':
            print(f"  ✅ Table {table_name} : ACTIVE")
            print(f"     - Partition Key: {table.key_schema[0]['AttributeName']}")
            print(f"     - Sort Key: {table.key_schema[1]['AttributeName']}")
            print(f"     - Item Count: {table.item_count}")
            return True
        else:
            print(f"  ⚠️  Table {table_name} : {status}")
            return False
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f"  ❌ Table {table_name} n'existe pas")
            return False
        else:
            print(f"  ❌ Erreur vérification {table_name}: {e}")
            return False


def main():
    """Point d'entrée principal"""
    print("=" * 70)
    print("  🚀 CityFlow - Configuration Tables DynamoDB")
    print("=" * 70)
    print()
    
    # Configuration
    REGION = 'eu-west-3'
    
    TABLES = [
        {
            'name': 'cityflow-metrics',
            'partition_key': 'metric_type',
            'sort_key': 'date',
            'description': 'Stockage des métriques (bikes, traffic, weather, etc.)'
        },
        {
            'name': 'cityflow-reports',
            'partition_key': 'report_id',
            'sort_key': 'date',
            'description': 'Stockage des rapports quotidiens'
        }
    ]
    
    print(f"📍 Région AWS: {REGION}")
    print(f"📊 Tables à créer: {len(TABLES)}")
    print()
    
    # Initialiser le client DynamoDB
    try:
        print("🔗 Connexion à DynamoDB...")
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        print("✅ Connexion établie")
        print()
    except Exception as e:
        print(f"❌ Erreur connexion DynamoDB: {e}")
        print()
        print("💡 Vérifiez:")
        print("   1. Que AWS CLI est configuré (aws configure)")
        print("   2. Que vos credentials AWS sont valides")
        print("   3. Que vous avez les permissions DynamoDB")
        sys.exit(1)
    
    # Créer les tables
    print("=" * 70)
    print("  📦 Création des Tables")
    print("=" * 70)
    print()
    
    created_tables = []
    failed_tables = []
    
    for table_config in TABLES:
        table_name = table_config['name']
        print(f"🔨 {table_name}")
        print(f"   Description: {table_config['description']}")
        print(f"   Partition Key: {table_config['partition_key']}")
        print(f"   Sort Key: {table_config['sort_key']}")
        
        success = create_table(
            dynamodb,
            table_name,
            table_config['partition_key'],
            table_config['sort_key'],
            REGION
        )
        
        if success:
            created_tables.append(table_name)
        else:
            failed_tables.append(table_name)
        
        print()
        time.sleep(1)  # Pause entre les créations
    
    # Vérification des tables
    print("=" * 70)
    print("  🔍 Vérification des Tables")
    print("=" * 70)
    print()
    
    all_ok = True
    for table_config in TABLES:
        table_name = table_config['name']
        print(f"🔍 Vérification: {table_name}")
        if not verify_table(dynamodb, table_name):
            all_ok = False
        print()
    
    # Résumé
    print("=" * 70)
    if all_ok:
        print("  ✅ Configuration Réussie !")
    else:
        print("  ⚠️  Configuration Partielle")
    print("=" * 70)
    print()
    
    if created_tables:
        print(f"✅ Tables créées/vérifiées: {len(created_tables)}")
        for table_name in created_tables:
            print(f"   • {table_name}")
        print()
    
    if failed_tables:
        print(f"❌ Erreurs: {len(failed_tables)}")
        for table_name in failed_tables:
            print(f"   • {table_name}")
        print()
        print("💡 Essayez de créer les tables manuellement via la console AWS")
        print("   ou vérifiez vos permissions IAM")
        print()
    
    print("🎯 Prochaines étapes:")
    print()
    print("1️⃣  Vérifier les tables dans la console AWS:")
    print("   https://eu-west-3.console.aws.amazon.com/dynamodbv2/home?region=eu-west-3#tables")
    print()
    print("2️⃣  Configurer les permissions IAM pour votre EC2:")
    print("   - Actions: dynamodb:PutItem, GetItem, Query, Scan")
    print("   - Resources: arn:aws:dynamodb:eu-west-3:*:table/cityflow-*")
    print()
    print("3️⃣  Tester la connexion depuis votre code:")
    print("   python3 -c 'from utils.database_factory import test_database_connection; test_database_connection()'")
    print()
    print("=" * 70)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

