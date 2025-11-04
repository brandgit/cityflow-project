# 📤 Guide d'Upload vers AWS

Ce guide explique comment uploader manuellement les données JSON vers AWS après traitement sur EC2.

---

## 📋 Nouveau Workflow

### 1️⃣ **Sur EC2 : Traitement des données**

Le système stocke maintenant **automatiquement** les données en JSON local :

```bash
# Sur EC2
cd /home/ec2-user/cityflow-project
./run_processing.sh
```

**Résultat :**
```
output/
├── metrics/
│   ├── bikes_metrics_2025-11-04.json
│   ├── traffic_metrics_2025-11-04.json
│   ├── weather_metrics_2025-11-04.json
│   ├── comptages_metrics_2025-11-04.json
│   ├── chantiers_metrics_2025-11-04.json
│   └── referentiel_metrics_2025-11-04.json
└── reports/
    ├── daily_report_2025-11-04.json
    └── daily_report_2025-11-04.csv
```

✅ **Plus besoin de DynamoDB** pendant le traitement !

---

### 2️⃣ **Upload manuel vers AWS**

Quand vous êtes prêt, uploadez les données :

#### **Upload tout (métriques + rapports)**
```bash
python upload_to_aws.py
```

#### **Upload une date spécifique**
```bash
python upload_to_aws.py --date 2025-11-04
```

#### **Upload seulement les métriques**
```bash
python upload_to_aws.py --type metrics
```

#### **Upload seulement les rapports**
```bash
python upload_to_aws.py --type reports
```

#### **Mode simulation (voir ce qui serait uploadé)**
```bash
python upload_to_aws.py --dry-run
```

---

## 🔧 Configuration requise

### **1. Tables DynamoDB**

Créez les tables avant l'upload :

```bash
# Script de création des tables
python setup_dynamodb_tables.py
```

Ou manuellement dans la console AWS :

**Table 1: `cityflow-metrics`**
- Partition key: `metric_type` (String)
- Sort key: `date` (String)
- Billing: On-demand ou 5 RCU / 5 WCU

**Table 2: `cityflow-reports`**
- Partition key: `report_id` (String)
- Sort key: `date` (String)
- Billing: On-demand ou 5 RCU / 5 WCU

### **2. Bucket S3**

Créez le bucket pour les rapports :

```bash
aws s3 mb s3://cityflow-reports-paris --region eu-west-3
```

### **3. IAM Role EC2**

Votre EC2 doit avoir ces permissions :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:eu-west-3:*:table/cityflow-metrics",
        "arn:aws:dynamodb:eu-west-3:*:table/cityflow-reports"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::cityflow-reports-paris/*"
      ]
    }
  ]
}
```

### **4. Fichier `.env` sur EC2**

```bash
# Région AWS
AWS_REGION=eu-west-3

# Tables DynamoDB
DYNAMODB_METRICS_TABLE=cityflow-metrics
DYNAMODB_REPORTS_TABLE=cityflow-reports

# Bucket S3
S3_REPORTS_BUCKET=cityflow-reports-paris
S3_REPORTS_PREFIX=reports

# Chemins locaux (sur EC2)
DATA_DIR=/home/ec2-user/cityflow-project/data
BATCH_DATA_PATH=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch
API_DATA_PATH=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/api
OUTPUT_DIR=/home/ec2-user/cityflow-project/output
```

---

## 📊 Exemple d'utilisation complète

```bash
# 1. Traiter les données (génère les JSON)
./run_processing.sh

# 2. Vérifier les fichiers générés
ls -lh output/metrics/
ls -lh output/reports/

# 3. Tester l'upload en mode simulation
python upload_to_aws.py --dry-run

# 4. Upload réel vers AWS
python upload_to_aws.py

# 5. Vérifier dans AWS
aws dynamodb scan --table-name cityflow-metrics --max-items 5
aws s3 ls s3://cityflow-reports-paris/reports/
```

---

## ✅ Avantages de cette approche

1. **Pas de dépendance DynamoDB** pendant le traitement
2. **Flexibilité** : vous choisissez quand uploader
3. **Économies** : pas d'écritures DynamoDB inutiles pendant les tests
4. **Backup local** : tous les fichiers JSON restent sur EC2
5. **Debugging facile** : fichiers JSON lisibles et modifiables
6. **Upload sélectif** : uploadez seulement certaines dates/types

---

## 🔍 Dépannage

### **Erreur : "Table does not exist"**

➡️ Créez les tables DynamoDB :
```bash
python setup_dynamodb_tables.py
```

### **Erreur : "Access Denied"**

➡️ Vérifiez le role IAM de votre EC2 :
```bash
aws sts get-caller-identity
aws iam get-role --role-name NomDeVotreRole
```

### **Erreur : "boto3 not found"**

➡️ Installez boto3 :
```bash
pip install boto3
```

### **Fichiers manquants**

➡️ Vérifiez que le traitement s'est bien terminé :
```bash
ls -lh output/metrics/
ls -lh output/reports/
```

---

## 🎯 Résumé des commandes

| Action | Commande |
|--------|----------|
| Traiter les données | `./run_processing.sh` |
| Voir fichiers générés | `ls -lh output/metrics/` |
| Upload simulation | `python upload_to_aws.py --dry-run` |
| Upload tout | `python upload_to_aws.py` |
| Upload date | `python upload_to_aws.py --date 2025-11-04` |
| Upload métriques | `python upload_to_aws.py --type metrics` |
| Upload rapports | `python upload_to_aws.py --type reports` |
| Créer tables | `python setup_dynamodb_tables.py` |
| Vérifier AWS | `aws dynamodb scan --table-name cityflow-metrics --max-items 5` |

---

## 📝 Notes

- Les fichiers JSON restent sur EC2 après upload (backup)
- Les données ont un TTL de 1 an dans DynamoDB
- Les rapports sont uploadés dans DynamoDB ET S3
- Le CSV est uploadé uniquement dans S3

---

## 🆘 Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs : `cat logs/processing_*.log`
2. Testez la connexion AWS : `aws sts get-caller-identity`
3. Vérifiez les permissions IAM
4. Utilisez `--dry-run` pour déboguer

