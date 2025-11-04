# 🚀 Guide de Configuration EC2 pour CityFlow

Ce guide vous aide à configurer et uploader les données sur votre instance EC2.

---

## 📋 Prérequis

1. Instance EC2 lancée (Amazon Linux 2 recommandé)
2. Accès SSH configuré
3. Python 3.9+ installé
4. Tables DynamoDB créées (voir section ci-dessous)

---

## 🔧 Étape 1 : Création des Tables DynamoDB

Avant de lancer le traitement, vous devez créer les tables DynamoDB :

### Via AWS CLI :

```bash
# Table pour les métriques
aws dynamodb create-table \
    --table-name cityflow-metrics \
    --attribute-definitions \
        AttributeName=metric_type,AttributeType=S \
        AttributeName=date,AttributeType=S \
    --key-schema \
        AttributeName=metric_type,KeyType=HASH \
        AttributeName=date,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region eu-west-3

# Table pour les rapports
aws dynamodb create-table \
    --table-name cityflow-reports \
    --attribute-definitions \
        AttributeName=report_id,AttributeType=S \
        AttributeName=date,AttributeType=S \
    --key-schema \
        AttributeName=report_id,KeyType=HASH \
        AttributeName=date,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region eu-west-3
```

### Via Console AWS :
1. Allez dans DynamoDB → Tables → Create table
2. Créer `cityflow-metrics` :
   - Partition key: `metric_type` (String)
   - Sort key: `date` (String)
   - Billing mode: On-demand
3. Créer `cityflow-reports` :
   - Partition key: `report_id` (String)
   - Sort key: `date` (String)
   - Billing mode: On-demand

---

## 📁 Étape 2 : Préparer les Fichiers en Local

Assurez-vous d'avoir tous les fichiers nécessaires :

```bash
# Structure attendue en local :
bucket-cityflow-paris-s3-raw/
└── cityflow-raw/
    └── raw/
        ├── batch/
        │   ├── comptages-routiers-permanents.csv
        │   ├── chantiers-perturbants-la-circulation.csv
        │   └── referentiel-geographique-pour-les-donnees-trafic-issues-des-capteurs-permanents.csv
        └── api/
            ├── bikes/
            │   └── dt=2025-11-04/
            │       └── hour=02/
            │           └── *.jsonl
            ├── traffic/
            │   └── dt=2025-11-04/
            │       └── hour=02/
            │           └── *.jsonl
            └── weather/
                └── dt=2025-11-04/
                    └── hour=02/
                        └── *.jsonl
```

---

## 📤 Étape 3 : Uploader les Fichiers sur EC2

### Option A : Via SCP (Recommandé pour fichiers < 1GB)

```bash
# Se connecter à votre EC2
export EC2_HOST="ec2-user@<votre-ip-ec2>"
export KEY_PATH="<chemin-vers-votre-cle.pem>"

# Créer la structure de dossiers sur EC2
ssh -i $KEY_PATH $EC2_HOST "mkdir -p /home/ec2-user/cityflow-project/data/{batch,api/bikes,api/traffic,api/weather}"

# Uploader les fichiers CSV (batch)
scp -i $KEY_PATH \
    bucket-cityflow-paris-s3-raw/cityflow-raw/raw/batch/*.csv \
    $EC2_HOST:/home/ec2-user/cityflow-project/data/batch/

# Uploader les fichiers API
scp -i $KEY_PATH -r \
    bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/bikes/dt=2025-11-04 \
    $EC2_HOST:/home/ec2-user/cityflow-project/data/api/bikes/

scp -i $KEY_PATH -r \
    bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/traffic/dt=2025-11-04 \
    $EC2_HOST:/home/ec2-user/cityflow-project/data/api/traffic/

scp -i $KEY_PATH -r \
    bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/weather/dt=2025-11-04 \
    $EC2_HOST:/home/ec2-user/cityflow-project/data/api/weather/
```

### Option B : Via S3 comme Stockage Intermédiaire (Pour gros fichiers)

```bash
# 1. Uploader vers S3 depuis votre machine locale
aws s3 cp bucket-cityflow-paris-s3-raw/cityflow-raw/raw/batch/ \
    s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/batch/ \
    --recursive

aws s3 cp bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/ \
    s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/ \
    --recursive

# 2. Sur EC2, télécharger depuis S3
ssh -i $KEY_PATH $EC2_HOST << 'EOF'
cd /home/ec2-user/cityflow-project
mkdir -p data/{batch,api}

# Télécharger les fichiers batch
aws s3 cp s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/batch/ \
    data/batch/ --recursive

# Télécharger les fichiers API
aws s3 cp s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/ \
    data/api/ --recursive
EOF
```

### Option C : Script Automatique (Plus Facile)

Utilisez le script fourni `upload_data_to_ec2.sh` :

```bash
chmod +x upload_data_to_ec2.sh
./upload_data_to_ec2.sh <ip-ec2> <chemin-cle.pem>
```

---

## ⚙️ Étape 4 : Configurer l'Environnement sur EC2

```bash
# Se connecter à EC2
ssh -i $KEY_PATH $EC2_HOST

# Aller dans le projet
cd /home/ec2-user/cityflow-project

# Copier le fichier .env pour EC2
cp env.ec2.example .env

# Vérifier que les chemins sont corrects
cat .env

# Installer les dépendances (si pas déjà fait)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔐 Étape 5 : Configurer les Permissions IAM

Votre instance EC2 doit avoir un rôle IAM avec ces permissions :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
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
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bucket-cityflow-paris-s3-raw/*",
        "arn:aws:s3:::cityflow-reports-paris/*"
      ]
    }
  ]
}
```

---

## ✅ Étape 6 : Vérifier l'Installation

Sur EC2, exécutez ces commandes pour vérifier :

```bash
# Vérifier que les fichiers sont bien présents
ls -lh /home/ec2-user/cityflow-project/data/batch/
ls -lh /home/ec2-user/cityflow-project/data/api/bikes/
ls -lh /home/ec2-user/cityflow-project/data/api/traffic/
ls -lh /home/ec2-user/cityflow-project/data/api/weather/

# Vérifier boto3
python3 << 'EOF'
import boto3
print("✓ boto3 installé:", boto3.__version__)

# Test DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='eu-west-3')
table = dynamodb.Table('cityflow-metrics')
print("✓ Table DynamoDB accessible:", table.table_name)
EOF

# Tester la connexion à la base de données
python3 << 'EOF'
from utils.database_factory import test_database_connection
test_database_connection()
EOF
```

---

## 🚀 Étape 7 : Lancer le Traitement

```bash
# Lancer le traitement complet
./run_processing.sh

# Ou manuellement
source venv/bin/activate
python3 main.py
```

---

## 🔍 En Cas d'Erreur

### Vérifier les logs
```bash
cat logs/processing_*.log | tail -100
```

### Problèmes Courants

#### 1. **Erreur : "Table does not exist"**
→ Créez les tables DynamoDB (voir Étape 1)

#### 2. **Erreur : "Access Denied"**
→ Vérifiez que le rôle IAM est bien attaché à l'EC2 (voir Étape 5)

#### 3. **Erreur : "No such file or directory"**
→ Vérifiez que les fichiers sont bien uploadés dans `/home/ec2-user/cityflow-project/data/`

#### 4. **Erreur : "boto3 not found"**
```bash
source venv/bin/activate
pip install boto3
```

---

## 📊 Structure des Données Attendue sur EC2

```
/home/ec2-user/cityflow-project/
├── data/
│   ├── batch/
│   │   ├── comptages-routiers-permanents.csv
│   │   ├── chantiers-perturbants-la-circulation.csv
│   │   └── referentiel-geographique-pour-les-donnees-trafic-issues-des-capteurs-permanents.csv
│   └── api/
│       ├── bikes/
│       │   └── dt=2025-11-04/
│       │       └── hour=02/
│       │           └── *.jsonl
│       ├── traffic/
│       │   └── dt=2025-11-04/
│       │       └── hour=02/
│       │           └── *.jsonl
│       └── weather/
│           └── dt=2025-11-04/
│               └── hour=02/
│                   └── *.jsonl
├── output/
│   ├── metrics/
│   ├── reports/
│   └── processed/
├── logs/
└── .env (copié depuis env.ec2.example)
```

---

## 💡 Conseils

1. **Compression des fichiers** : Pour accélérer l'upload, compressez d'abord :
   ```bash
   tar -czf data.tar.gz bucket-cityflow-paris-s3-raw/cityflow-raw/raw/
   scp -i $KEY_PATH data.tar.gz $EC2_HOST:/home/ec2-user/
   ssh -i $KEY_PATH $EC2_HOST "cd /home/ec2-user && tar -xzf data.tar.gz"
   ```

2. **Monitoring** : Surveillez l'utilisation CPU/RAM pendant le traitement :
   ```bash
   htop
   ```

3. **Logs en temps réel** :
   ```bash
   tail -f logs/processing_*.log
   ```

---

## 📞 Support

En cas de problème, vérifiez :
1. Les logs : `logs/processing_*.log`
2. La connexion DynamoDB : `python3 -c "from utils.database_factory import test_database_connection; test_database_connection()"`
3. Les permissions IAM : Console AWS → EC2 → Instance → Security → IAM Role

