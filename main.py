#!/usr/bin/env python3
"""
Point d'entrée principal CityFlow Analytics
Orchestre l'ensemble du pipeline : Traitement + Génération de rapport

Usage:
    python3 main.py [date]
    
Exemples:
    python3 main.py                    # Traite et génère rapport pour aujourd'hui
    python3 main.py 2025-11-03         # Traite et génère rapport pour la date spécifiée
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire courant au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))


def print_banner(title: str):
    """Affiche une bannière"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def run_processors(date: str = None):
    """
    Exécute le traitement des données (processors)
    
    Args:
        date: Date au format YYYY-MM-DD (défaut: aujourd'hui)
    
    Returns:
        bool: True si succès, False sinon
    """
    print_banner("ÉTAPE 1/2 : TRAITEMENT DES DONNÉES")
    
    try:
        # Importer et exécuter le main des processors
        from processors import main as processors_main
        
        print("🔄 Lancement du traitement des données...")
        print()
        
        results = processors_main.main(date=date)
        
        if results is None:
            print("\n❌ Erreur lors du traitement des données")
            return False
        
        print("\n✅ Traitement des données terminé avec succès")
        return True
    
    except Exception as e:
        print(f"\n❌ ERREUR lors du traitement des données: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_report_generator(date: str = None):
    """
    Exécute la génération du rapport quotidien
    
    Args:
        date: Date du rapport (format YYYY-MM-DD), None pour aujourd'hui
    
    Returns:
        bool: True si succès, False sinon
    """
    print_banner("ÉTAPE 2/2 : GÉNÉRATION DU RAPPORT")
    
    try:
        # Importer et exécuter le main du générateur de rapport
        from report_generator import main as report_main
        
        print("📊 Lancement de la génération du rapport...")
        print()
        
        # Passer la date en argument si fournie
        if date:
            sys.argv = [sys.argv[0], date]
        
        exit_code = report_main.main()
        
        if exit_code != 0:
            print("\n❌ Erreur lors de la génération du rapport")
            return False
        
        print("\n✅ Génération du rapport terminée avec succès")
        return True
    
    except Exception as e:
        print(f"\n❌ ERREUR lors de la génération du rapport: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Point d'entrée principal - Orchestre le pipeline complet
    """
    # Récupérer la date depuis les arguments ou utiliser aujourd'hui
    date = None
    if len(sys.argv) > 1:
        date = sys.argv[1]
        # Valider le format de la date
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Format de date invalide: {date}")
            print("   Format attendu: YYYY-MM-DD")
            print("\nUsage:")
            print("   python3 main.py [YYYY-MM-DD]")
            return 1
    else:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Bannière de démarrage
    print("\n" + "=" * 70)
    print("  🚀 CityFlow Analytics - Pipeline Complet")
    print("=" * 70)
    print(f"\n📅 Date de traitement: {date}")
    print(f"🕐 Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Vérifier l'environnement
    if os.getenv("AWS_EXECUTION_ENV"):
        print("☁️  Environnement: AWS (Lambda/EC2)")
    else:
        print("🏠 Environnement: Local (Développement)")
    
    # Timer de début
    start_time = datetime.now()
    
    # ================================================================
    # ÉTAPE 1 : Traitement des données
    # ================================================================
    success_processors = run_processors()
    
    if not success_processors:
        print("\n" + "=" * 70)
        print("❌ ÉCHEC : Le traitement des données a échoué")
        print("=" * 70)
        return 1
    
    # ================================================================
    # ÉTAPE 2 : Génération du rapport
    # ================================================================
    success_report = run_report_generator(date)
    
    if not success_report:
        print("\n" + "=" * 70)
        print("⚠️  PARTIEL : Traitement OK, mais rapport échoué")
        print("=" * 70)
        return 1
    
    # ================================================================
    # RÉSUMÉ FINAL
    # ================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("  ✅ SUCCÈS : Pipeline complet terminé")
    print("=" * 70)
    print(f"\n⏱️  Durée totale: {duration:.2f} secondes ({duration/60:.2f} minutes)")
    print(f"🕐 Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Résumé des fichiers générés
    print("\n📂 Fichiers générés:")
    
    if not os.getenv("AWS_EXECUTION_ENV"):
        # Mode local
        print(f"   📊 Métriques: output/metrics/*_metrics_{date}.json")
        print(f"   📈 Rapport CSV: output/reports/daily_report_{date}.csv")
        print(f"   📄 Rapport JSON: output/reports/daily_report_{date}.json")
        print(f"   💾 Base de données: MongoDB (collection metrics + reports)")
        
        print("\n💡 Pour visualiser:")
        print("   - MongoDB Compass: mongodb://localhost:27017/")
        print(f"   - Fichiers locaux: ls -lh output/reports/")
    else:
        # Mode AWS
        print(f"   📊 Métriques: DynamoDB (table cityflow-metrics)")
        print(f"   📈 Rapport CSV: S3 (s3://cityflow-reports/reports/daily_report_{date}.csv)")
        print(f"   📄 Rapport JSON: DynamoDB (table cityflow-daily-reports)")
        
        print("\n💡 Pour visualiser:")
        print("   - AWS Console DynamoDB")
        print("   - AWS Console S3")
    
    print("\n" + "=" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur (Ctrl+C)")
        print("Pipeline annulé")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

