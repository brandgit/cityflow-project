# 🔧 Fix EC2 - Mode Fichiers Locaux

## 🎯 Problème résolu

**Avant :** Sur EC2, le traitement échouait car il essayait de se connecter à DynamoDB qui n'était pas configuré.

**Maintenant :** Sur EC2, le système utilise des **fichiers JSON locaux** et vous pouvez uploader manuellement vers AWS quand vous êtes prêt.

---

## 📦 Fichiers créés/modifiés

### ✨ Nouveaux fichiers

1. **`utils/local_file_service.py`** - Service pour gérer les fichiers JSON locaux
2. **`upload_to_aws.py`** - Script pour uploader vers DynamoDB et S3
3. **`deploy_to_ec2.sh`** - Script pour déployer automatiquement sur EC2
4. **`UPLOAD_AWS_GUIDE.md`** - Guide complet d'utilisation
5. **`CHANGEMENTS_EC2.md`** - Détails techniques des modifications

### 🔄 Fichiers modifiés

1. **`utils/database_factory.py`** - Utilise LocalFileService sur EC2 au lieu de DynamoDB

---

## 🚀 Déploiement sur EC2

### Option 1 : Script automatique (recommandé)

```bash
# Avec clé SSH
./deploy_to_ec2.sh ec2-user@VOTRE-IP ~/.ssh/votre-cle.pem

# Sans clé SSH (si configuré dans ~/.ssh/config)
./deploy_to_ec2.sh ec2-user@VOTRE-IP
```

Le script :
- ✅ Upload les fichiers automatiquement
- ✅ Teste le système sur EC2
- ✅ Affiche un résumé des prochaines étapes

### Option 2 : Upload manuel via SCP

```bash
# Upload des fichiers
scp -i ~/.ssh/votre-cle.pem utils/local_file_service.py ec2-user@VOTRE-IP:~/cityflow-project/utils/
scp -i ~/.ssh/votre-cle.pem utils/database_factory.py ec2-user@VOTRE-IP:~/cityflow-project/utils/
scp -i ~/.ssh/votre-cle.pem upload_to_aws.py ec2-user@VOTRE-IP:~/cityflow-project/
scp -i ~/.ssh/votre-cle.pem *.md ec2-user@VOTRE-IP:~/cityflow-project/
```

### Option 3 : Via Git (si configuré)

```bash
# En local
git add .
git commit -m "Fix EC2: Utilisation fichiers JSON locaux"
git push

# Sur EC2
ssh ec2-user@VOTRE-IP
cd ~/cityflow-project
git pull
```

---

## 🧪 Test sur EC2

Une fois les fichiers déployés :

```bash
# 1. Se connecter à EC2
ssh -i ~/.ssh/votre-cle.pem ec2-user@VOTRE-IP

# 2. Aller dans le projet
cd ~/cityflow-project

# 3. Tester le nouveau système
python3 << EOF
from utils.database_factory import get_database_service
db = get_database_service()
print("✅ OK!")
EOF

# 4. Lancer le traitement
./run_processing.sh

# 5. Vérifier les fichiers générés
ls -lh output/metrics/
ls -lh output/reports/
```

---

## 📊 Résultat attendu

Après le traitement, vous devriez avoir :

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

---

## 📤 Upload vers AWS (optionnel)

### Prérequis

1. **Tables DynamoDB créées** :
   ```bash
   python setup_dynamodb_tables.py
   ```

2. **Bucket S3 créé** :
   ```bash
   aws s3 mb s3://cityflow-reports-paris --region eu-west-3
   ```

3. **Role IAM EC2 configuré** avec permissions DynamoDB et S3

### Commandes d'upload

```bash
# Voir ce qui serait uploadé (simulation)
python upload_to_aws.py --dry-run

# Upload tout
python upload_to_aws.py

# Upload seulement une date
python upload_to_aws.py --date 2025-11-04

# Upload seulement les métriques
python upload_to_aws.py --type metrics

# Upload seulement les rapports
python upload_to_aws.py --type reports
```

---

## ✅ Avantages

| Aspect | Bénéfice |
|--------|----------|
| 🚀 **Traitement** | Fonctionne sans DynamoDB |
| 💰 **Coûts** | Pas d'écritures DynamoDB inutiles |
| 🔍 **Debugging** | Fichiers JSON lisibles |
| ⏱️ **Flexibilité** | Upload quand vous voulez |
| 📦 **Backup** | Fichiers locaux + cloud |
| 🧪 **Tests** | Pas besoin d'AWS configuré |

---

## 📚 Documentation complète

- **`UPLOAD_AWS_GUIDE.md`** - Guide d'utilisation complet
- **`CHANGEMENTS_EC2.md`** - Détails techniques

---

## 🔍 Vérification

### Sur EC2

```bash
# Type de base de données détecté
python3 -c "from utils.database_factory import get_database_type; print(get_database_type())"
# Devrait afficher: local_files

# Tester le service
python3 -c "from utils.database_factory import test_database_connection; test_database_connection()"
# Devrait afficher: ✓ Connexion à la base de données OK
```

### En local (développement)

```bash
# Type de base de données détecté
python3 -c "from utils.database_factory import get_database_type; print(get_database_type())"
# Devrait afficher: mongodb (si bucket-cityflow-paris-s3-raw existe)
```

---

## 🆘 Dépannage

### Erreur : "No module named 'utils.local_file_service'"

➡️ Les fichiers n'ont pas été déployés correctement
```bash
./deploy_to_ec2.sh ec2-user@VOTRE-IP ~/.ssh/votre-cle.pem
```

### Erreur : "Permission denied"

➡️ Rendre le script exécutable
```bash
chmod +x deploy_to_ec2.sh
```

### Traitement échoue toujours

➡️ Vérifier les logs
```bash
tail -100 logs/processing_*.log
```

---

## 📞 Support

Si vous rencontrez des problèmes :

1. ✅ Vérifiez que les fichiers sont bien sur EC2
2. ✅ Testez la détection du type de base de données
3. ✅ Lisez les logs de traitement
4. ✅ Consultez `UPLOAD_AWS_GUIDE.md` pour plus de détails

---

## 🎉 C'est tout !

Le système est maintenant prêt à fonctionner sur EC2 sans avoir besoin de DynamoDB pendant le traitement.

**Prochaine étape :** Déployer sur EC2 avec `./deploy_to_ec2.sh`

---

**Auteur :** Assistant AI  
**Date :** 2025-11-04  
**Version :** 1.0  
**Statut :** ✅ Prêt pour production

