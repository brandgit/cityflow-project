#!/bin/bash
#
# Script pour télécharger les données brutes depuis S3 vers EC2
# Structure: data/cityflow-raw/raw/
#

set -e  # Arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
S3_BUCKET="bucket-cityflow-paris-s3-raw"
REGION="eu-west-3"
PROJECT_DIR="$HOME/cityflow-project"
DATA_DIR="$PROJECT_DIR/data/cityflow-raw/raw"

# Fonction d'affichage
print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

print_header "📥 Téléchargement des données depuis S3"

print_info "Configuration:"
echo "  Bucket S3: s3://$S3_BUCKET"
echo "  Région: $REGION"
echo "  Destination: $DATA_DIR"
echo ""

# Vérifier la connexion AWS
print_info "Vérification de la connexion AWS..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "Impossible de se connecter à AWS"
    echo ""
    echo "Vérifiez:"
    echo "  1. Les credentials AWS sont configurés"
    echo "  2. Le role IAM de l'EC2 a les permissions S3"
    echo ""
    echo "Commande: aws configure"
    exit 1
fi
print_success "Connexion AWS OK"

# Créer les répertoires
print_info "Création de la structure de répertoires..."
mkdir -p "$DATA_DIR/batch"
mkdir -p "$DATA_DIR/api"
print_success "Répertoires créés"

# Télécharger les données batch (CSV)
print_header "📊 Téléchargement données BATCH (CSV)"

print_info "Synchronisation depuis s3://$S3_BUCKET/raw/batch/"
aws s3 sync "s3://$S3_BUCKET/raw/batch/" "$DATA_DIR/batch/" --region $REGION

if [ $? -eq 0 ]; then
    print_success "Données batch téléchargées"
    echo ""
    echo "Fichiers batch:"
    ls -lh "$DATA_DIR/batch/" 2>/dev/null || echo "  (aucun fichier)"
else
    print_error "Erreur lors du téléchargement des données batch"
fi

# Télécharger les données API (JSON/JSONL)
print_header "📡 Téléchargement données API (JSON/JSONL)"

print_info "Synchronisation depuis s3://$S3_BUCKET/raw/api/"
aws s3 sync "s3://$S3_BUCKET/raw/api/" "$DATA_DIR/api/" --region $REGION

if [ $? -eq 0 ]; then
    print_success "Données API téléchargées"
    echo ""
    echo "Fichiers API:"
    ls -lh "$DATA_DIR/api/" 2>/dev/null || echo "  (aucun fichier)"
else
    print_error "Erreur lors du téléchargement des données API"
fi

# Résumé
print_header "✅ Téléchargement terminé"

echo "Structure des données:"
echo ""
tree -L 3 "$DATA_DIR" 2>/dev/null || find "$DATA_DIR" -type d -maxdepth 3 | sed 's|[^/]*/|  |g'

echo ""
echo "Statistiques:"
echo "  Fichiers batch:"
BATCH_COUNT=$(find "$DATA_DIR/batch" -type f 2>/dev/null | wc -l)
echo "    Nombre: $BATCH_COUNT"
if [ $BATCH_COUNT -gt 0 ]; then
    echo "    Taille: $(du -sh "$DATA_DIR/batch" 2>/dev/null | cut -f1)"
fi

echo "  Fichiers API:"
API_COUNT=$(find "$DATA_DIR/api" -type f 2>/dev/null | wc -l)
echo "    Nombre: $API_COUNT"
if [ $API_COUNT -gt 0 ]; then
    echo "    Taille: $(du -sh "$DATA_DIR/api" 2>/dev/null | cut -f1)"
fi

echo ""
echo "  Taille totale: $(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)"

echo ""
print_success "Les données sont prêtes pour le traitement!"
echo ""
echo "Prochaines étapes:"
echo "  1. Vérifier le fichier .env"
echo "  2. Lancer le traitement: ./run_processing.sh"
echo ""

