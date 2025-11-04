#!/bin/bash

################################################################################
# Script de traitement CityFlow Analytics
# Crée l'environnement, installe les dépendances et lance le traitement
################################################################################

set -e  # Arrêter en cas d'erreur

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Début
clear
print_header "🚀 CityFlow Analytics - Setup & Traitement"

# Date
DATE=${1:-$(date +%Y-%m-%d)}

echo ""
print_info "Date de traitement: $DATE"
echo ""

# 1. Vérifier Python
print_info "Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 non trouvé !"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
print_success "Python trouvé: $PYTHON_VERSION"

# 2. Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    print_info "Création de l'environnement virtuel..."
    python3 -m venv venv
    print_success "Environnement virtuel créé"
else
    print_success "Environnement virtuel existe déjà"
fi

# 3. Activer l'environnement virtuel
print_info "Activation de l'environnement virtuel..."
source venv/bin/activate
print_success "Environnement virtuel activé"

# 4. Installer/Mettre à jour les dépendances
print_info "Installation des dépendances..."
pip install -r requirements.txt --quiet --upgrade
print_success "Dépendances installées"

# 5. Vérifier le fichier .env
if [ ! -f ".env" ]; then
    print_info "Fichier .env non trouvé, utilisation de env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        print_success "Fichier .env créé depuis env.example"
    else
        print_error "Aucun fichier de configuration trouvé !"
        exit 1
    fi
else
    print_success "Fichier .env trouvé"
fi

# 6. Créer les répertoires nécessaires
print_info "Création des répertoires..."
mkdir -p logs
mkdir -p data/raw
mkdir -p output/metrics
mkdir -p output/reports
print_success "Répertoires créés"

# 7. Lancement du traitement
echo ""
print_header "📊 Traitement des données - $DATE"
echo ""

LOG_FILE="logs/processing_$(date +%Y%m%d_%H%M%S).log"

# Lancer main.py
python3 main.py $DATE 2>&1 | tee $LOG_FILE

# Vérifier le résultat
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    print_success "🎉 Traitement terminé avec succès !"
    print_info "Logs: $LOG_FILE"
    
    # Afficher les fichiers générés
    echo ""
    print_info "Fichiers générés:"
    ls -lh output/metrics/*_$DATE.json 2>/dev/null | awk '{print "  📊 " $9 " (" $5 ")"}'
    ls -lh output/reports/*_$DATE.* 2>/dev/null | awk '{print "  📈 " $9 " (" $5 ")"}'
    echo ""
    exit 0
else
    echo ""
    print_error "❌ Échec du traitement"
    print_info "Consultez: $LOG_FILE"
    exit 1
fi
