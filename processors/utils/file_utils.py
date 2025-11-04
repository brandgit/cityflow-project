"""
Utilitaires pour la manipulation de fichiers : CSV, JSON, chunks
"""

import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
import sys

# Importer config depuis le répertoire parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import CHUNK_SIZE, PROCESSED_DIR


def load_csv(file_path: str,
            separator: str = ";",
            encoding: str = "utf-8") -> List[Dict]:
    """
    Charge un fichier CSV
    
    Args:
        file_path: Chemin du fichier CSV
        separator: Séparateur (défaut: ";")
        encoding: Encodage (défaut: "utf-8")
    
    Returns:
        Liste des enregistrements (dict)
    """
    records = []
    
    try:
        # Utiliser utf-8-sig pour retirer automatiquement le BOM si présent
        actual_encoding = 'utf-8-sig' if encoding == 'utf-8' else encoding
        
        with open(file_path, 'r', encoding=actual_encoding) as f:
            # Détection automatique du séparateur si possible
            first_line = f.readline()
            f.seek(0)
            
            reader = csv.DictReader(f, delimiter=separator)
            
            for row in reader:
                # Nettoyer les valeurs et les clés (enlever BOM si encore présent)
                cleaned_row = {k.strip().lstrip('\ufeff'): v.strip() if isinstance(v, str) else v 
                              for k, v in row.items()}
                records.append(cleaned_row)
    
    except Exception as e:
        print(f"Erreur chargement CSV {file_path}: {e}")
        return []
    
    return records


def save_csv(data: List[Dict],
            file_path: str,
            separator: str = ";",
            encoding: str = "utf-8") -> bool:
    """
    Sauvegarde des données en CSV
    
    Args:
        data: Liste des enregistrements
        file_path: Chemin de sortie
        separator: Séparateur
        encoding: Encodage
    
    Returns:
        True si succès
    """
    try:
        if not data:
            return False
        
        # Créer répertoire si nécessaire
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Extraire les colonnes
        columns = list(data[0].keys())
        
        with open(file_path, 'w', encoding=encoding, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, delimiter=separator)
            writer.writeheader()
            writer.writerows(data)
        
        return True
    
    except Exception as e:
        print(f"Erreur sauvegarde CSV {file_path}: {e}")
        return False


def load_json(file_path: str) -> Optional[Dict]:
    """
    Charge un fichier JSON
    
    Args:
        file_path: Chemin du fichier JSON
    
    Returns:
        Dict des données ou None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement JSON {file_path}: {e}")
        return None


def load_and_combine_json_files(file_paths: List[str]) -> Optional[Dict]:
    """
    Charge et combine plusieurs fichiers JSON en un seul dict
    
    Utilisé pour combiner plusieurs fichiers de données (ex: plusieurs heures de données API)
    Les données sont combinées selon leur structure :
    - Si liste : concatène toutes les listes
    - Si dict : merge les dicts (les clés du dernier fichier écrase les précédentes)
    
    Args:
        file_paths: Liste des chemins des fichiers JSON
    
    Returns:
        Dict ou List combiné, ou None si erreur
    """
    if not file_paths:
        return None
    
    all_data = []
    combined_dict = {}
    
    for file_path in file_paths:
        data = load_json(file_path)
        if data is None:
            continue
        
        if isinstance(data, list):
            # Si c'est une liste, ajouter à la liste globale
            all_data.extend(data)
        elif isinstance(data, dict):
            # Si c'est un dict, merger avec le dict global
            # Pour les données API (bikes, traffic, weather), on combine les listes
            if 'data' in data and isinstance(data['data'], list):
                # Structure API : {"data": [...], ...}
                if 'data' not in combined_dict:
                    combined_dict = data.copy()
                    combined_dict['data'] = []
                combined_dict['data'].extend(data['data'])
            else:
                # Structure simple : merger les clés
                combined_dict.update(data)
    
    # Retourner selon le type de données combinées
    if all_data:
        return all_data
    elif combined_dict:
        return combined_dict
    
    return None


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


def chunk_file(file_path: str,
              chunk_size: int = None,
              output_dir: Optional[str] = None) -> List[str]:
    """
    Découpe un fichier CSV en chunks
    
    Args:
        file_path: Chemin du fichier à découper
        chunk_size: Taille des chunks (lignes, défaut: config)
        output_dir: Répertoire de sortie (défaut: PROCESSED_DIR)
    
    Returns:
        Liste des chemins des chunks créés
    """
    if chunk_size is None:
        chunk_size = CHUNK_SIZE
    
    if output_dir is None:
        output_dir = PROCESSED_DIR
    
    chunk_paths = []
    base_name = Path(file_path).stem
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            header = next(reader)  # Lire l'en-tête
            
            chunk_data = []
            chunk_num = 0
            
            for row in reader:
                chunk_data.append(row)
                
                if len(chunk_data) >= chunk_size:
                    # Sauvegarder chunk
                    chunk_path = os.path.join(output_dir, f"{base_name}_chunk_{chunk_num:04d}.csv")
                    with open(chunk_path, 'w', encoding='utf-8', newline='') as chunk_file:
                        writer = csv.writer(chunk_file, delimiter=';')
                        writer.writerow(header)
                        writer.writerows(chunk_data)
                    
                    chunk_paths.append(chunk_path)
                    chunk_data = []
                    chunk_num += 1
            
            # Sauvegarder dernier chunk si données restantes
            if chunk_data:
                chunk_path = os.path.join(output_dir, f"{base_name}_chunk_{chunk_num:04d}.csv")
                with open(chunk_path, 'w', encoding='utf-8', newline='') as chunk_file:
                    writer = csv.writer(chunk_file, delimiter=';')
                    writer.writerow(header)
                    writer.writerows(chunk_data)
                
                chunk_paths.append(chunk_path)
    
    except Exception as e:
        print(f"Erreur découpe fichier {file_path}: {e}")
        return []
    
    return chunk_paths


def get_file_size_mb(file_path: str) -> float:
    """
    Obtient la taille d'un fichier en MB
    
    Args:
        file_path: Chemin du fichier
    
    Returns:
        Taille en MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def find_json_files(directory: str, pattern: str = "*.json") -> List[str]:
    """
    Trouve tous les fichiers JSON dans un répertoire
    
    Args:
        directory: Répertoire à explorer
        pattern: Pattern de recherche
    
    Returns:
        Liste des chemins des fichiers JSON
    """
    json_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
    except Exception:
        pass
    
    return json_files


def find_csv_files(directory: str, pattern: str = "*.csv") -> List[str]:
    """
    Trouve tous les fichiers CSV dans un répertoire selon un pattern
    
    Args:
        directory: Répertoire à explorer
        pattern: Pattern de recherche (ex: "comptages*.csv", "*.csv")
    
    Returns:
        Liste des chemins des fichiers CSV
    """
    import fnmatch
    csv_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.csv') and fnmatch.fnmatch(file, pattern):
                    csv_files.append(os.path.join(root, file))
    except Exception:
        pass
    
    return sorted(csv_files)  # Trier pour avoir un ordre prévisible

