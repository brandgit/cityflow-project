# 🔧 Changements pour EC2 - Mode Fichiers Locaux

## 📋 Résumé

Le système a été modifié pour **NE PLUS utiliser DynamoDB pendant le traitement sur EC2**. 

À la place, toutes les données sont maintenant stockées en **fichiers JSON locaux**, puis vous pouvez les uploader manuellement vers AWS quand vous voulez.

---

## ✅ Modifications effectuées

### 1️⃣ **Nouveau service : `LocalFileService`**

**Fichier créé :** `utils/local_file_service.py`

- Implémente l'interface `DatabaseService`
- Stocke métriques et rapports en JSON local
- Gère automatiquement les chemins relatifs/absolus
- Compatible avec MongoDB pour le développement local

### 2️⃣ **Factory modifié : `database_factory.py`**

**Modifications :**
- ❌ Avant : EC2 → DynamoDB
- ✅ Maintenant : EC2 → Fichiers JSON locaux
- MongoDB reste utilisé en développement local

**Logique de détection :**
```python
# Si dossier "bucket-cityflow-paris-s3-raw" n'existe pas
#   → Mode EC2 → LocalFileService (fichiers JSON)
# Sinon
#   → Mode Local → MongoDB
```

### 3️⃣ **Script d'upload : `upload_to_aws.py`**

**Fichier créé :** Script Python pour uploader manuellement vers AWS

**Fonctionnalités :**
- Upload métriques → DynamoDB
- Upload rapports → DynamoDB + S3 (JSON + CSV)
- Mode `--dry-run` pour tester
- Upload sélectif par date ou type
- Gestion automatique des erreurs

**Usage :**
```bash
python upload_to_aws.py                    # Tout uploader
python upload_to_aws.py --date 2025-11-04  # Date spécifique
python upload_to_aws.py --type metrics     # Seulement métriques
python upload_to_aws.py --dry-run          # Simulation
```

### 4️⃣ **Guide d'utilisation : `UPLOAD_AWS_GUIDE.md`**

Documentation complète avec :
- Workflow complet
- Configuration requise
- Exemples d'utilisation
- Dépannage
- Tableau des commandes

---

## 🔄 Nouveau Workflow

### **Avant (problématique)**
```
EC2 Traitement → ❌ Erreur DynamoDB → ❌ Échec
```

### **Maintenant (solution)**
```
EC2 Traitement → ✅ Fichiers JSON locaux → ✅ Succès
                          ↓
                   Upload manuel vers AWS (quand prêt)
                          ↓
                   DynamoDB + S3
```

---

## 📊 Structure des fichiers générés

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

**Format JSON des métriques :**
```json
{
  "metric_type": "bikes",
  "date": "2025-11-04",
  "timestamp": "2025-11-04T10:30:00",
  "metrics": {
    // ... données métriques ...
  }
}
```

**Format JSON des rapports :**
```json
{
  "report_id": "daily_report_2025-11-04",
  "date": "2025-11-04",
  "timestamp": "2025-11-04T10:35:00",
  "report": {
    // ... données du rapport ...
  }
}
```

---

## 🚀 Comment utiliser sur EC2

### **1. Traiter les données**

```bash
cd /home/ec2-user/cityflow-project
./run_processing.sh
```

**Résultat attendu :**
```
✅ Traitement terminé avec succès
📁 Fichiers JSON créés dans output/
```

### **2. Vérifier les fichiers**

```bash
ls -lh output/metrics/
ls -lh output/reports/
```

### **3. (Optionnel) Tester l'upload**

```bash
python upload_to_aws.py --dry-run
```

### **4. Uploader vers AWS**

```bash
# Upload tout
python upload_to_aws.py

# Ou upload sélectif
python upload_to_aws.py --date 2025-11-04
```

---

## ✅ Avantages de cette approche

| Aspect | Avant | Maintenant |
|--------|-------|------------|
| **Dépendances** | ❌ Requiert DynamoDB + boto3 | ✅ Aucune dépendance AWS |
| **Traitement** | ❌ Échoue si DynamoDB inaccessible | ✅ Fonctionne toujours |
| **Coûts** | 💰 Écritures DynamoDB à chaque test | 💰 Pas d'écritures DynamoDB inutiles |
| **Debugging** | 🔍 Difficile (données dans DynamoDB) | 🔍 Facile (fichiers JSON lisibles) |
| **Flexibilité** | ⏱️ Upload immédiat automatique | ⏱️ Upload quand vous voulez |
| **Backup** | 📦 Seulement dans DynamoDB | 📦 Fichiers JSON + DynamoDB |
| **Tests** | 🧪 Requiert AWS configuré | 🧪 Fonctionne sans AWS |

---

## 🔧 Configuration requise pour l'upload

### **1. Tables DynamoDB**

Créez-les avec :
```bash
python setup_dynamodb_tables.py
```

Ou manuellement :
- Table `cityflow-metrics` : PK = `metric_type` (String), SK = `date` (String)
- Table `cityflow-reports` : PK = `report_id` (String), SK = `date` (String)

### **2. Bucket S3**

```bash
aws s3 mb s3://cityflow-reports-paris --region eu-west-3
```

### **3. IAM Role EC2**

Permissions requises :
- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`
- `s3:PutObject`, `s3:GetObject`

### **4. Fichier `.env`**

```bash
AWS_REGION=eu-west-3
DYNAMODB_METRICS_TABLE=cityflow-metrics
DYNAMODB_REPORTS_TABLE=cityflow-reports
S3_REPORTS_BUCKET=cityflow-reports-paris
S3_REPORTS_PREFIX=reports
OUTPUT_DIR=/home/ec2-user/cityflow-project/output
```

---

## 🧪 Tests effectués

✅ Service LocalFileService créé et testé
✅ Factory modifié et testé
✅ Script upload créé
✅ Documentation complète
✅ Pas d'erreur de linting
✅ Compatible avec environnement local et EC2

---

## 📝 Notes importantes

1. **MongoDB toujours utilisé en local** : Si le dossier `bucket-cityflow-paris-s3-raw` existe, MongoDB est utilisé (développement local)

2. **Chemins relatifs/absolus gérés** : Le système détecte automatiquement si le chemin dans `.env` existe et utilise un fallback si nécessaire

3. **Pas de perte de données** : Les fichiers JSON restent sur EC2 après upload (backup)

4. **TTL DynamoDB** : Les données ont un TTL de 1 an dans DynamoDB

5. **Upload idempotent** : Vous pouvez réexécuter l'upload sans problème (écrase les données existantes)

---

## 🆘 Dépannage

### **Problème : "Type de base de données inconnu"**

➡️ Le factory détecte mal l'environnement
```bash
# Vérifier la détection
python3 -c "from utils.database_factory import get_database_type; print(get_database_type())"
```

### **Problème : Fichiers non créés après traitement**

➡️ Vérifier les logs
```bash
tail -100 logs/processing_*.log
```

### **Problème : Upload échoue "Access Denied"**

➡️ Vérifier le role IAM
```bash
aws sts get-caller-identity
```

---

## 🎯 Commandes rapides

```bash
# Sur EC2
./run_processing.sh                          # Traiter
python upload_to_aws.py --dry-run            # Tester upload
python upload_to_aws.py                      # Upload réel
aws dynamodb scan --table-name cityflow-metrics --max-items 5  # Vérifier

# En local (développement)
# → Continue d'utiliser MongoDB automatiquement
```

---

## ✨ Résultat final

**Sur EC2, vous avez maintenant :**

1. ✅ Traitement des données qui fonctionne toujours
2. ✅ Fichiers JSON lisibles et modifiables
3. ✅ Flexibilité pour uploader quand vous voulez
4. ✅ Pas de dépendance DynamoDB pendant le traitement
5. ✅ Économies sur les coûts AWS
6. ✅ Debugging facilité avec fichiers locaux
7. ✅ Backup local + cloud

**En local :**

1. ✅ MongoDB continue de fonctionner normalement
2. ✅ Aucun changement pour le développement

---

## 📚 Fichiers modifiés/créés

| Fichier | Action | Description |
|---------|--------|-------------|
| `utils/local_file_service.py` | ✨ Créé | Service pour fichiers JSON locaux |
| `utils/database_factory.py` | 🔧 Modifié | Utilise LocalFileService sur EC2 |
| `upload_to_aws.py` | ✨ Créé | Script d'upload manuel vers AWS |
| `UPLOAD_AWS_GUIDE.md` | ✨ Créé | Guide d'utilisation complet |
| `CHANGEMENTS_EC2.md` | ✨ Créé | Ce fichier (résumé) |

---

**Date des modifications :** 2025-11-04  
**Statut :** ✅ Prêt pour production EC2

