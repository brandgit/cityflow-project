"""
Point d'entrée principal pour la génération de rapports quotidiens
Exécuté séparément dans AWS (Lambda/EC2) après le traitement des données
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from report_generator.daily_report_generator import DailyReportGenerator


def main():
    """
    Point d'entrée principal pour génération de rapport
    
    Usage:
        python report_generator/main.py [YYYY-MM-DD]
    """
    # Date peut être passée en argument ou utilisée depuis variable d'environnement
    date = None
    
    # 1. Vérifier argument ligne de commande
    if len(sys.argv) > 1:
        date = sys.argv[1]
        try:
            # Valider format date
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"✗ Format de date invalide: {date}")
            print("  Format attendu: YYYY-MM-DD")
            print("  Usage: python report_generator/main.py [YYYY-MM-DD]")
            return 1
    
    # 2. Vérifier variable d'environnement AWS (pour Lambda/EventBridge)
    if not date:
        date = os.getenv("REPORT_DATE")
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                print(f"⚠ Variable REPORT_DATE invalide: {date}")
                date = None
    
    # 3. Par défaut: date d'hier (car rapport généré le matin pour le jour précédent)
    if not date:
        yesterday = datetime.now()
        date = yesterday.strftime("%Y-%m-%d")
        print(f"ℹ Aucune date spécifiée, utilisation d'aujourd'hui: {date}")
    
    print("=" * 60)
    print("CityFlow Analytics - Génération Rapport Quotidien")
    print("=" * 60)
    print(f"Date du rapport: {date}\n")
    
    # Initialiser le générateur
    generator = DailyReportGenerator()
    
    try:
        # Générer et exporter le rapport
        files = generator.generate_and_export(date)
        
        print("\n" + "=" * 60)
        print("✓ RAPPORT GÉNÉRÉ AVEC SUCCÈS!")
        print("=" * 60)
        print("\nFichiers créés:")
        print(f"  📄 JSON: {files['json']}")
        print(f"  📊 CSV:  {files['csv']}")
        print("\n" + "=" * 60)
        
        return 0
    
    except FileNotFoundError as e:
        print(f"\n✗ ERREUR: Métriques non trouvées pour la date {date}")
        print(f"  Détail: {e}")
        print("\n💡 Assurez-vous d'avoir exécuté le traitement des données:")
        print("   python processors/main.py")
        print("   (Les métriques doivent être dans DynamoDB ou fichiers locaux)")
        return 1
    
    except Exception as e:
        print(f"\n✗ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

