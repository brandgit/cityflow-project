# 📁 Chemins corrects sur EC2

## ✅ Structure des dossiers

```
/home/ec2-user/cityflow-project/
│
├── data/
│   └── cityflow-raw/
│       └── raw/
│           ├── batch/                    # ← Fichiers CSV
│           │   ├── comptages-routiers-permanents.csv
│           │   ├── chantiers-perturbants-la-circulation.csv
│           │   └── referentiel-geographique-*.csv
│           │
│           └── api/                      # ← Fichiers JSON/JSONL
│               ├── bikes/
│               ├── traffic/
│               └── weather/
│
├── output/                               # ← Résultats du traitement
│   ├── metrics/
│   └── reports/
│
└── logs/
```

---

## 📋 Chemins absolus

| Type | Chemin complet |
|------|----------------|
| **Données brutes CSV** | `/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/` |
| **Données brutes JSON** | `/home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/` |
| **Métriques traitées** | `/home/ec2-user/cityflow-project/output/metrics/` |
| **Rapports** | `/home/ec2-user/cityflow-project/output/reports/` |
| **Logs** | `/home/ec2-user/cityflow-project/logs/` |

---

## 📥 Télécharger depuis S3 (commandes correctes)

### Option 1 : Tout télécharger
```bash
cd /home/ec2-user/cityflow-project

# Créer la structure
mkdir -p data/cityflow-raw/raw/{batch,api}

# Télécharger TOUT
aws s3 sync s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/ \
    data/cityflow-raw/raw/ \
    --region eu-west-3
```

### Option 2 : Télécharger batch et api séparément
```bash
cd /home/ec2-user/cityflow-project

# Créer la structure
mkdir -p data/cityflow-raw/raw/batch
mkdir -p data/cityflow-raw/raw/api

# Télécharger batch (CSV)
aws s3 sync s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/batch/ \
    data/cityflow-raw/raw/batch/ \
    --region eu-west-3

# Télécharger api (JSON/JSONL)
aws s3 sync s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/api/ \
    data/cityflow-raw/raw/api/ \
    --region eu-west-3
```

---

## 🔍 Vérifier les données téléchargées

```bash
# Voir les fichiers CSV
ls -lh /home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/

# Voir les fichiers JSON/JSONL
ls -lh /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/

# Compter tous les fichiers
find /home/ec2-user/cityflow-project/data/cityflow-raw/raw/ -type f | wc -l

# Voir la taille totale
du -sh /home/ec2-user/cityflow-project/data/cityflow-raw/
```

---

## ⚙️ Configuration `.env` sur EC2

Votre fichier `.env` doit contenir ces chemins :

```bash
# ============================================
# CHEMINS DE DONNÉES SUR EC2
# ============================================
# Structure depuis S3: data/cityflow-raw/raw/
DATA_DIR=/home/ec2-user/cityflow-project/data
BATCH_DATA_PATH=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch
API_DATA_PATH=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/api
OUTPUT_DIR=/home/ec2-user/cityflow-project/output

# Fichiers CSV (dans data/cityflow-raw/raw/batch/)
COMPTAGES_CSV=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/comptages-routiers-permanents.csv
CHANTIERS_CSV=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/chantiers-perturbants-la-circulation.csv
REFERENTIEL_CSV=/home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/referentiel-geographique-pour-les-donnees-trafic-issues-des-capteurs-permanents.csv
```

---

## 🎯 Workflow complet

```bash
# 1. Se connecter à EC2
ssh -i ~/.ssh/votre-cle.pem ec2-user@VOTRE-IP

# 2. Aller dans le projet
cd /home/ec2-user/cityflow-project

# 3. Créer la structure
mkdir -p data/cityflow-raw/raw/{batch,api}

# 4. Télécharger depuis S3
aws s3 sync s3://bucket-cityflow-paris-s3-raw/cityflow-raw/raw/ \
    data/cityflow-raw/raw/ \
    --region eu-west-3

# 5. Vérifier
ls -lh data/cityflow-raw/raw/batch/
ls -lh data/cityflow-raw/raw/api/

# 6. Lancer le traitement
./run_processing.sh

# 7. Voir les résultats
ls -lh output/metrics/
ls -lh output/reports/
```

---

## 📝 Commandes rapides de référence

```bash
# Aller au dossier des données brutes
cd ~/cityflow-project/data/cityflow-raw/raw

# Lister batch
ls -lh batch/

# Lister api
ls -lh api/

# Compter les fichiers CSV
ls -1 batch/*.csv | wc -l

# Voir la taille d'un fichier
du -h batch/comptages-routiers-permanents.csv

# Taille totale données brutes
du -sh ~/cityflow-project/data/cityflow-raw/

# Taille totale résultats
du -sh ~/cityflow-project/output/
```

---

## ⚠️ IMPORTANT

**Le chemin correct est :**
```
data/cityflow-raw/raw/
```

**PAS :**
- ~~`data/raw/`~~ ❌
- ~~`data/batch/`~~ ❌
- ~~`data/api/`~~ ❌

---

## ✅ Fichiers corrigés

Les fichiers suivants ont été mis à jour avec les bons chemins :

1. ✅ `env.ec2.example` - Configuration EC2
2. ✅ `upload_data_to_ec2.sh` - Script d'upload
3. ✅ `SETUP_EC2.md` - Documentation setup
4. ✅ `UPLOAD_AWS_GUIDE.md` - Guide upload AWS
5. ✅ `CHANGEMENTS_EC2.md` - Résumé des changements

---

**Date :** 2025-11-04  
**Statut :** ✅ Chemins corrigés et testés

