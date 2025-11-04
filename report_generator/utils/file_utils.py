"""
Utilitaires pour la manipulation de fichiers JSON/CSV pour les rapports
"""

import json
import csv
import os
from typing import Any, List, Dict


def save_json(data: Any,
             file_path: str,
             indent: int = 2) -> bool:
    """
    Sauvegarde des données en JSON
    
    Args:
        data: Données à sauvegarder
        file_path: Chemin de sortie
        indent: Indentation JSON
    
    Returns:
        True si succès
    """
    try:
        # Créer répertoire si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        return True
    
    except Exception as e:
        print(f"Erreur sauvegarde JSON {file_path}: {e}")
        return False


def save_csv(data: List[Dict],
            file_path: str,
            separator: str = ";",
            encoding: str = "utf-8") -> bool:
    """
    Sauvegarde des données en CSV
    
    Args:
        data: Liste des enregistrements ou lignes (liste de listes)
        file_path: Chemin de sortie
        separator: Séparateur
        encoding: Encodage
    
    Returns:
        True si succès
    """
    try:
        # Créer répertoire si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding, newline='') as f:
            writer = csv.writer(f, delimiter=separator)
            for row in data:
                writer.writerow(row)
        
        return True
    
    except Exception as e:
        print(f"Erreur sauvegarde CSV {file_path}: {e}")
        return False

