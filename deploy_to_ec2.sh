#!/bin/bash
#
# Script pour déployer les modifications sur EC2
# Usage: ./deploy_to_ec2.sh [ec2-user@ip-address]
#

set -e  # Arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Vérifier les arguments
if [ $# -eq 0 ]; then
    print_error "Usage: $0 [ec2-user@ip-address] [ssh-key-path]"
    echo ""
    echo "Exemples:"
    echo "  $0 ec2-user@3.250.100.50"
    echo "  $0 ec2-user@3.250.100.50 ~/.ssh/my-key.pem"
    exit 1
fi

EC2_HOST=$1
SSH_KEY=${2:-""}

# Construire la commande SSH
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="ssh -i $SSH_KEY"
    SCP_CMD="scp -i $SSH_KEY"
else
    SSH_CMD="ssh"
    SCP_CMD="scp"
fi

print_header "🚀 Déploiement vers EC2"

print_info "Hôte EC2: $EC2_HOST"
if [ -n "$SSH_KEY" ]; then
    print_info "Clé SSH: $SSH_KEY"
fi

# Vérifier la connexion
print_info "Test de connexion..."
if ! $SSH_CMD $EC2_HOST "echo 'OK'" > /dev/null 2>&1; then
    print_error "Impossible de se connecter à $EC2_HOST"
    exit 1
fi
print_success "Connexion OK"

# Créer un répertoire temporaire pour les fichiers à déployer
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

print_info "Préparation des fichiers..."

# Copier les fichiers à déployer
cp utils/local_file_service.py $TEMP_DIR/
cp utils/database_factory.py $TEMP_DIR/
cp upload_to_aws.py $TEMP_DIR/
cp UPLOAD_AWS_GUIDE.md $TEMP_DIR/
cp CHANGEMENTS_EC2.md $TEMP_DIR/

print_success "Fichiers préparés"

# Upload des fichiers
print_header "📤 Upload des fichiers"

print_info "Upload utils/local_file_service.py..."
$SCP_CMD $TEMP_DIR/local_file_service.py $EC2_HOST:~/cityflow-project/utils/
print_success "local_file_service.py uploadé"

print_info "Upload utils/database_factory.py..."
$SCP_CMD $TEMP_DIR/database_factory.py $EC2_HOST:~/cityflow-project/utils/
print_success "database_factory.py uploadé"

print_info "Upload upload_to_aws.py..."
$SCP_CMD $TEMP_DIR/upload_to_aws.py $EC2_HOST:~/cityflow-project/
$SSH_CMD $EC2_HOST "chmod +x ~/cityflow-project/upload_to_aws.py"
print_success "upload_to_aws.py uploadé et rendu exécutable"

print_info "Upload documentation..."
$SCP_CMD $TEMP_DIR/UPLOAD_AWS_GUIDE.md $EC2_HOST:~/cityflow-project/
$SCP_CMD $TEMP_DIR/CHANGEMENTS_EC2.md $EC2_HOST:~/cityflow-project/
print_success "Documentation uploadée"

# Vérification sur EC2
print_header "🔍 Vérification sur EC2"

print_info "Test du nouveau système..."
$SSH_CMD $EC2_HOST << 'EOF'
cd ~/cityflow-project
source venv/bin/activate 2>/dev/null || true
python3 << 'PYEOF'
try:
    from utils.database_factory import get_database_service, get_database_type
    
    print("\n✓ Import réussi")
    print(f"  Type détecté: {get_database_type()}")
    
    db = get_database_service()
    print("✓ Service initialisé")
    
    # Test rapide
    test_data = {"test": "deploy"}
    db.save_metrics(test_data, "test_deploy", "2025-11-04")
    print("✓ Test d'écriture OK")
    
    loaded = db.load_metrics("test_deploy", "2025-11-04")
    if loaded:
        print("✓ Test de lecture OK")
    
    if hasattr(db, 'close'):
        db.close()
    
    print("\n✅ Tous les tests passent!")
    
except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
PYEOF
EOF

if [ $? -eq 0 ]; then
    print_success "Tests réussis sur EC2"
else
    print_error "Tests échoués sur EC2"
    exit 1
fi

# Nettoyer le fichier de test
print_info "Nettoyage du fichier de test..."
$SSH_CMD $EC2_HOST "rm -f ~/cityflow-project/output/metrics/test_deploy_metrics_2025-11-04.json"

# Résumé
print_header "✅ Déploiement terminé"

echo "Fichiers déployés:"
echo "  ✓ utils/local_file_service.py"
echo "  ✓ utils/database_factory.py"
echo "  ✓ upload_to_aws.py"
echo "  ✓ UPLOAD_AWS_GUIDE.md"
echo "  ✓ CHANGEMENTS_EC2.md"
echo ""
echo "Prochaines étapes sur EC2:"
echo "  1. Lancer le traitement:      ./run_processing.sh"
echo "  2. Vérifier les fichiers:     ls -lh output/metrics/"
echo "  3. Uploader vers AWS:         python upload_to_aws.py"
echo ""
echo "Pour vous connecter:"
if [ -n "$SSH_KEY" ]; then
    echo "  ssh -i $SSH_KEY $EC2_HOST"
else
    echo "  ssh $EC2_HOST"
fi
echo ""
print_success "Déploiement réussi! 🎉"

