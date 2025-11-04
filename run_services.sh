#!/bin/bash

################################################################################
# Script de lancement des services CityFlow Analytics
# Crée l'environnement, installe les dépendances et lance API + Streamlit
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

# Ports
API_PORT=5001
DASHBOARD_PORT=8501

# Début
clear
print_header "🚀 CityFlow Analytics - Lancement des Services"
echo ""

# 1. Vérifier Python
print_info "Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 non trouvé !"
    exit 1
fi
print_success "Python trouvé: $(python3 --version)"

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
        print_success "Fichier .env créé"
    fi
fi

# 6. Créer les répertoires
mkdir -p logs

# 7. Vérifier si les ports sont disponibles
print_info "Vérification des ports..."

if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_error "Port $API_PORT déjà utilisé !"
    print_info "Arrêtez le processus existant ou changez le port"
    exit 1
fi

if lsof -Pi :$DASHBOARD_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_error "Port $DASHBOARD_PORT déjà utilisé !"
    print_info "Arrêtez le processus existant ou changez le port"
    exit 1
fi

print_success "Ports disponibles"

# 8. Lancer l'API
echo ""
print_header "🔌 Lancement de l'API"
print_info "Démarrage sur le port $API_PORT..."

nohup python3 api/local_server.py > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid

# Attendre que l'API démarre
sleep 3

if ps -p $API_PID > /dev/null 2>&1; then
    print_success "API démarrée (PID: $API_PID)"
else
    print_error "Échec du démarrage de l'API"
    cat logs/api.log | tail -20
    exit 1
fi

# 9. Lancer Streamlit
echo ""
print_header "📊 Lancement du Dashboard"
print_info "Démarrage sur le port $DASHBOARD_PORT..."

nohup streamlit run dashboard/app.py --server.port $DASHBOARD_PORT --server.address 0.0.0.0 > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > logs/dashboard.pid

# Attendre que Streamlit démarre
sleep 5

if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
    print_success "Dashboard démarré (PID: $DASHBOARD_PID)"
else
    print_error "Échec du démarrage du Dashboard"
    cat logs/dashboard.log | tail -20
    exit 1
fi

# 10. Résumé
echo ""
print_header "✅ Services actifs"
echo ""
echo -e "  🔌 ${GREEN}API${NC}       : http://localhost:$API_PORT"
echo -e "  📊 ${GREEN}Dashboard${NC} : http://localhost:$DASHBOARD_PORT"
echo ""
echo -e "  📝 Logs API       : logs/api.log"
echo -e "  📝 Logs Dashboard : logs/dashboard.log"
echo ""
print_info "Pour arrêter les services:"
echo -e "  ${YELLOW}kill \$(cat logs/api.pid) \$(cat logs/dashboard.pid)${NC}"
echo ""
print_success "🎉 Services lancés avec succès !"
echo ""
