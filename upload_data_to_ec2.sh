#!/bin/bash

################################################################################
# Script d'Upload des Données CityFlow vers EC2
# Usage: ./upload_data_to_ec2.sh <ip-ec2> <chemin-cle.pem>
################################################################################

set -e

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher messages
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

################################################################################
# Vérification des arguments
################################################################################

if [ "$#" -ne 2 ]; then
    error "Usage: $0 <ip-ec2> <chemin-cle.pem>"
    echo ""
    echo "Exemple:"
    echo "  $0 ec2-35-180-123-45.eu-west-3.compute.amazonaws.com ~/.ssh/cityflow-key.pem"
    exit 1
fi

EC2_IP="$1"
KEY_PATH="$2"
EC2_USER="ec2-user"
EC2_HOST="${EC2_USER}@${EC2_IP}"
PROJECT_DIR="/home/ec2-user/cityflow-project"

################################################################################
# Vérifications préalables
################################################################################

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🚀 CityFlow - Upload Données vers EC2"
echo "════════════════════════════════════════════════════════════"
echo ""

info "Vérification des prérequis..."

# Vérifier que la clé existe
if [ ! -f "$KEY_PATH" ]; then
    error "Clé SSH introuvable: $KEY_PATH"
    exit 1
fi
success "Clé SSH trouvée"

# Vérifier que la clé a les bonnes permissions
PERMS=$(stat -f "%A" "$KEY_PATH" 2>/dev/null || stat -c "%a" "$KEY_PATH" 2>/dev/null)
if [ "$PERMS" != "400" ] && [ "$PERMS" != "600" ]; then
    warning "Permissions de la clé incorrectes (actuellement: $PERMS)"
    info "Correction des permissions..."
    chmod 400 "$KEY_PATH"
    success "Permissions corrigées (400)"
fi

# Vérifier que les données locales existent
LOCAL_DATA_DIR="bucket-cityflow-paris-s3-raw/cityflow-raw/raw"
if [ ! -d "$LOCAL_DATA_DIR" ]; then
    error "Répertoire de données local introuvable: $LOCAL_DATA_DIR"
    exit 1
fi
success "Données locales trouvées"

# Tester la connexion SSH
info "Test de connexion SSH..."
if ssh -i "$KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$EC2_HOST" "echo 'OK'" > /dev/null 2>&1; then
    success "Connexion SSH OK"
else
    error "Impossible de se connecter à $EC2_HOST"
    error "Vérifiez l'IP et les règles du Security Group (port 22)"
    exit 1
fi

echo ""

################################################################################
# Création de la structure de dossiers sur EC2
################################################################################

info "Création de la structure de dossiers sur EC2..."
ssh -i "$KEY_PATH" "$EC2_HOST" << 'EOF'
mkdir -p /home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch
mkdir -p /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/bikes
mkdir -p /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/traffic
mkdir -p /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/weather
mkdir -p /home/ec2-user/cityflow-project/output/{metrics,reports,processed}
mkdir -p /home/ec2-user/cityflow-project/logs
EOF
success "Dossiers créés"

echo ""

################################################################################
# Upload des fichiers CSV (Batch)
################################################################################

echo "════════════════════════════════════════════════════════════"
echo "  📦 Upload Fichiers Batch (CSV)"
echo "════════════════════════════════════════════════════════════"
echo ""

BATCH_FILES=(
    "comptages-routiers-permanents.csv"
    "comptages-routiers-permanents-2.csv"
    "chantiers-perturbants-la-circulation.csv"
    "referentiel-geographique-pour-les-donnees-trafic-issues-des-capteurs-permanents.csv"
)

for file in "${BATCH_FILES[@]}"; do
    LOCAL_FILE="$LOCAL_DATA_DIR/batch/$file"
    if [ -f "$LOCAL_FILE" ]; then
        FILE_SIZE=$(du -h "$LOCAL_FILE" | cut -f1)
        info "Upload: $file ($FILE_SIZE)..."
        
        if scp -i "$KEY_PATH" -o StrictHostKeyChecking=no "$LOCAL_FILE" "$EC2_HOST:$PROJECT_DIR/data/cityflow-raw/raw/batch/"; then
            success "$file uploadé"
        else
            warning "Erreur upload $file"
        fi
    else
        warning "Fichier introuvable: $file (ignoré)"
    fi
done

echo ""

################################################################################
# Upload des fichiers API (JSON/JSONL)
################################################################################

echo "════════════════════════════════════════════════════════════"
echo "  📦 Upload Fichiers API (JSON)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Détecter la date la plus récente dans les données API
API_DATE=$(find "$LOCAL_DATA_DIR/api" -type d -name "dt=*" | sed 's/.*dt=//' | sort -r | head -1)

if [ -z "$API_DATE" ]; then
    warning "Aucune donnée API trouvée"
else
    info "Détection date API: $API_DATE"
    
    # Upload Bikes
    if [ -d "$LOCAL_DATA_DIR/api/bikes/dt=$API_DATE" ]; then
        info "Upload bikes (dt=$API_DATE)..."
        scp -i "$KEY_PATH" -o StrictHostKeyChecking=no -r \
            "$LOCAL_DATA_DIR/api/bikes/dt=$API_DATE" \
            "$EC2_HOST:$PROJECT_DIR/data/cityflow-raw/raw/api/bikes/" && \
        success "Bikes uploadé"
    else
        warning "Pas de données bikes pour $API_DATE"
    fi
    
    # Upload Traffic
    if [ -d "$LOCAL_DATA_DIR/api/traffic/dt=$API_DATE" ]; then
        info "Upload traffic (dt=$API_DATE)..."
        scp -i "$KEY_PATH" -o StrictHostKeyChecking=no -r \
            "$LOCAL_DATA_DIR/api/traffic/dt=$API_DATE" \
            "$EC2_HOST:$PROJECT_DIR/data/cityflow-raw/raw/api/traffic/" && \
        success "Traffic uploadé"
    else
        warning "Pas de données traffic pour $API_DATE"
    fi
    
    # Upload Weather
    if [ -d "$LOCAL_DATA_DIR/api/weather/dt=$API_DATE" ]; then
        info "Upload weather (dt=$API_DATE)..."
        scp -i "$KEY_PATH" -o StrictHostKeyChecking=no -r \
            "$LOCAL_DATA_DIR/api/weather/dt=$API_DATE" \
            "$EC2_HOST:$PROJECT_DIR/data/cityflow-raw/raw/api/weather/" && \
        success "Weather uploadé"
    else
        warning "Pas de données weather pour $API_DATE"
    fi
fi

echo ""

################################################################################
# Vérification sur EC2
################################################################################

echo "════════════════════════════════════════════════════════════"
echo "  🔍 Vérification des Fichiers sur EC2"
echo "════════════════════════════════════════════════════════════"
echo ""

ssh -i "$KEY_PATH" "$EC2_HOST" << 'EOF'
echo "📁 Fichiers Batch:"
ls -lh /home/ec2-user/cityflow-project/data/cityflow-raw/raw/batch/ 2>/dev/null || echo "  (vide)"
echo ""
echo "📁 Fichiers API - Bikes:"
find /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/bikes/ -type f 2>/dev/null | head -3 || echo "  (vide)"
echo ""
echo "📁 Fichiers API - Traffic:"
find /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/traffic/ -type f 2>/dev/null | head -3 || echo "  (vide)"
echo ""
echo "📁 Fichiers API - Weather:"
find /home/ec2-user/cityflow-project/data/cityflow-raw/raw/api/weather/ -type f 2>/dev/null | head -3 || echo "  (vide)"
EOF

echo ""

################################################################################
# Résumé
################################################################################

echo "════════════════════════════════════════════════════════════"
echo "  ✅ Upload Terminé !"
echo "════════════════════════════════════════════════════════════"
echo ""
success "Données uploadées sur EC2: $EC2_IP"
echo ""
echo "💡 Prochaines étapes:"
echo ""
echo "1️⃣  Copier le fichier .env:"
echo "   ssh -i $KEY_PATH $EC2_HOST"
echo "   cd $PROJECT_DIR"
echo "   cp env.ec2.example .env"
echo ""
echo "2️⃣  Vérifier la configuration:"
echo "   cat .env"
echo ""
echo "3️⃣  Lancer le traitement:"
echo "   ./run_processing.sh"
echo ""
echo "4️⃣  Surveiller les logs:"
echo "   tail -f logs/processing_*.log"
echo ""
echo "════════════════════════════════════════════════════════════"

