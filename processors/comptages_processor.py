"""
Processeur CRITIQUE pour les données Batch Comptages Routiers (6.2 GB)
Gère la découpe en chunks et traitement EC2 si nécessaire
"""

from typing import List, Dict, Any
from processors.base_processor import BaseProcessor
from processors.utils.file_utils import load_csv, get_file_size_mb, chunk_file
from processors.utils.validators import (
    validate_date_iso, validate_geojson, normalize_traffic_status
)
from processors.utils.aggregators import (
    group_by_field, calculate_mean_value, get_mode_value,
    calculate_top_n, calculate_max_value
)
from processors.utils.geo_utils import (
    calculate_line_length, get_arrondissement_from_coordinates,
    extract_center_point
)
from processors.utils.zone_analysis import (
    get_zone_from_coordinates, extract_zone_from_libelle,
    get_quadrant_from_coordinates,
    group_by_zone, calculate_zone_metrics, identify_high_traffic_zones
)
from processors.utils.traffic_calculations import (
    calculate_lost_time, detect_congestion_alerts
)
from models.traffic_metrics import TrafficMetrics, TrafficGlobal
from config import MAX_FILE_SIZE_MB, EC2_CHUNK_SIZE


class ComptagesProcessor(BaseProcessor):
    """Processeur pour les comptages routiers permanents"""
    
    def __init__(self, config=None, use_ec2=False):
        """
        Args:
            config: Configuration
            use_ec2: Forcer utilisation EC2 même si fichier petit
        """
        super().__init__(config)
        self.use_ec2 = use_ec2
    
    def validate_and_clean(self, data: Any) -> List[Dict]:
        """
        Validation et nettoyage des comptages routiers
        
        Args:
            data: Chemin fichier CSV ou liste de dicts
        
        Returns:
            Liste des enregistrements nettoyés
        """
        # Si c'est un chemin, charger
        if isinstance(data, str):
            records = load_csv(data)
        else:
            records = data
        
        cleaned = []
        
        for record in records:
            # Valider date
            date_str = record.get("Date et heure de comptage", "")
            if not validate_date_iso(date_str):
                continue
            
            # Nettoyage valeurs
            debit = record.get("Débit horaire", "")
            taux_occupation = record.get("Taux d'occupation", "")
            
            try:
                debit_float = float(debit) if debit else None
                taux_float = float(taux_occupation) if taux_occupation else None
            except (ValueError, TypeError):
                debit_float = None
                taux_float = None
            
            # Valider GeoJSON
            geo_shape = record.get("geo_shape", "")
            if geo_shape and not validate_geojson(geo_shape):
                geo_shape = None
            
            # Normaliser état trafic
            etat_trafic = normalize_traffic_status(
                record.get("Etat trafic", "Inconnu")
            )
            
            cleaned_record = {
                "Identifiant arc": record.get("Identifiant arc", ""),
                "Libelle": record.get("Libelle", ""),
                "Date et heure de comptage": date_str,
                "Débit horaire": debit_float,
                "Taux d'occupation": taux_float,
                "Etat trafic": etat_trafic,
                "Identifiant noeud amont": record.get("Identifiant noeud amont", ""),
                "Identifiant noeud aval": record.get("Identifiant noeud aval", ""),
                "Etat arc": record.get("Etat arc", ""),
                "geo_shape": geo_shape,
                "geo_point_2d": record.get("geo_point_2d", "")
            }
            
            # Filtrer arcs invalides
            if cleaned_record["Etat arc"] != "Invalide":
                cleaned.append(cleaned_record)
        
        return cleaned
    
    def aggregate_daily(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """
        Agrégations quotidiennes par tronçon
        
        Args:
            cleaned_data: Données nettoyées
        
        Returns:
            Dict avec agrégations par tronçon
        """
        # Grouper par Identifiant arc
        by_arc = group_by_field(cleaned_data, "Identifiant arc")
        
        aggregated_by_arc = {}
        
        for arc_id, records in by_arc.items():
            if not records:
                continue
            
            # Calculer longueur tronçon (depuis premier enregistrement)
            geo_shape = records[0].get("geo_shape", "")
            longueur_metres = 0.0
            if geo_shape:
                longueur_metres = calculate_line_length(geo_shape)
            
            # Extraire geo_point avant de l'utiliser
            geo_point = records[0].get("geo_point_2d", "")
            
            # Si longueur = 0, estimer depuis coordonnées (approximation)
            if longueur_metres == 0.0 and geo_point:
                try:
                    # Estimation basique : si pas de geo_shape, utiliser longueur moyenne Paris
                    # Longueur moyenne d'un tronçon routier à Paris : ~500m
                    longueur_metres = 500.0
                except Exception:
                    pass
            libelle = records[0].get("Libelle", "")
            
            arrondissement = None
            zone_fallback = None
            
            # Priorité 1: Arrondissement depuis coordonnées
            if geo_point:
                try:
                    lat_str, lon_str = geo_point.split(", ")
                    lon = float(lon_str)
                    lat = float(lat_str)
                    arrondissement = get_arrondissement_from_coordinates(lon, lat)
                    
                    # Si pas d'arrondissement, utiliser zone géographique
                    if not arrondissement:
                        zone_fallback = get_zone_from_coordinates(lon, lat)
                except Exception:
                    pass
            
            # Priorité 2: Zone depuis libellé si pas d'arrondissement
            if not arrondissement and libelle:
                zone_from_libelle = extract_zone_from_libelle(libelle)
                if zone_from_libelle:
                    zone_fallback = zone_from_libelle
            
            # Priorité 3: Si toujours pas de zone et qu'on a des coordonnées, utiliser quadrant
            if not zone_fallback and geo_point:
                try:
                    lat_str, lon_str = geo_point.split(", ")
                    lon = float(lon_str)
                    lat = float(lat_str)
                    quadrant = get_quadrant_from_coordinates(lon, lat)
                    if quadrant and quadrant != "Unknown":
                        zone_fallback = quadrant
                except Exception:
                    pass
            
            # Gérer arrondissement None (MongoDB n'accepte pas les clés None)
            if arrondissement is None:
                arrondissement = "Unknown"
            
            # Toujours avoir une zone_fallback (même si "Unknown")
            if not zone_fallback:
                zone_fallback = "Unknown"
            
            # Agrégations
            debit_moyen = calculate_mean_value(records, "Débit horaire") or 0.0
            debit_total = sum(r.get("Débit horaire", 0) or 0 for r in records)
            debit_max = calculate_max_value(records, "Débit horaire") or 0.0
            taux_moyen = calculate_mean_value(records, "Taux d'occupation") or 0.0
            etat_dominant = get_mode_value(records, "Etat trafic") or "Inconnu"
            
            # Pic horaire (simplifié - prendre max débit)
            pic_record = max(records, key=lambda r: r.get("Débit horaire", 0) or 0)
            heure_pic = pic_record.get("Date et heure de comptage", "")
            
            aggregated_by_arc[arc_id] = {
                "identifiant_arc": arc_id,
                "libelle": records[0].get("Libelle", ""),
                "debit_horaire_moyen": debit_moyen,
                "debit_journalier_total": debit_total,
                "debit_max": debit_max,
                "taux_occupation_moyen": taux_moyen,
                "etat_trafic_dominant": etat_dominant,
                "heure_pic": heure_pic,
                "longueur_metres": longueur_metres,
                "arrondissement": arrondissement,
                "zone_fallback": zone_fallback,  # Zone géographique si arrondissement Unknown
                "geo_point_2d": geo_point,
                "records_count": len(records)
            }
        
        # Agrégation globale
        total_vehicules = sum(a["debit_journalier_total"] for a in aggregated_by_arc.values())
        nombre_troncons = len(aggregated_by_arc)
        moyenne_debit_troncon = total_vehicules / nombre_troncons if nombre_troncons > 0 else 0.0
        
        return {
            "by_arc": aggregated_by_arc,
            "global": {
                "total_vehicules_jour": total_vehicules,
                "nombre_troncons": nombre_troncons,
                "moyenne_debit_par_troncon": moyenne_debit_troncon
            }
        }
    
    def calculate_indicators(self, aggregated_data: Dict) -> Dict[str, Any]:
        """
        Calculs d'indicateurs : temps perdu, alertes, top 10
        
        Args:
            aggregated_data: Données agrégées
        
        Returns:
            Dict avec indicateurs et métriques
        """
        by_arc = aggregated_data.get("by_arc", {})
        metrics = []
        
        # Calculer temps perdu pour chaque tronçon
        for arc_id, arc_data in by_arc.items():
            debit = arc_data.get("debit_horaire_moyen", 0.0)
            taux_occ = arc_data.get("taux_occupation_moyen", 0.0)
            longueur = arc_data.get("longueur_metres", 0.0)
            
            # Calcul temps perdu
            # Utiliser une longueur par défaut si non disponible (500m = moyenne Paris)
            longueur_effective = longueur if longueur > 0 else 500.0
            
            # Calculer temps perdu par véhicule
            temps_perdu_par_vehicule, _ = calculate_lost_time(
                debit if debit > 0 else 1.0,  # Éviter division par 0 dans calculate_lost_time
                taux_occ, 
                longueur_effective
            )
            
            # Temps perdu total = temps perdu par véhicule × nombre moyen de véhicules/heure × 24h
            # Ou directement: temps perdu par véhicule × débit journalier / 24
            debit_journalier = arc_data.get("debit_journalier_total", 0.0)
            if debit_journalier > 0 and temps_perdu_par_vehicule > 0:
                # Débit journalier = somme de toutes les heures de la journée
                # Temps perdu total = (temps perdu par véhicule) × (débit moyen horaire) × 24h
                # = temps_perdu_par_vehicule × (debit_journalier / 24) × 24
                # = temps_perdu_par_vehicule × debit_journalier
                temps_perdu_total = temps_perdu_par_vehicule * debit_journalier
            else:
                temps_perdu_total = 0.0
            
            # Détecter congestion
            congestion_alerte = taux_occ >= self.config.TAUX_OCCUPATION_SEUIL_CONGESTION
            
            # Gérer arrondissement None (MongoDB n'accepte pas les clés None)
            arrondissement = arc_data.get("arrondissement")
            zone_fallback = arc_data.get("zone_fallback")
            if arrondissement is None:
                arrondissement = "Unknown"
            
            metric = TrafficMetrics(
                date="",  # Sera rempli dans main
                identifiant_arc=arc_id,
                libelle=arc_data.get("libelle", ""),
                debit_horaire_moyen=debit,
                debit_journalier_total=arc_data.get("debit_journalier_total", 0.0),
                debit_max=arc_data.get("debit_max", 0.0),
                taux_occupation_moyen=taux_occ,
                etat_trafic_dominant=arc_data.get("etat_trafic_dominant", "Inconnu"),
                heure_pic=arc_data.get("heure_pic", ""),
                temps_perdu_minutes=temps_perdu_par_vehicule,  # Temps perdu par véhicule
                temps_perdu_total_minutes=temps_perdu_total,  # Temps perdu total (tous véhicules)
                congestion_alerte=congestion_alerte,
                arrondissement=arrondissement,
                geo_point_2d=arc_data.get("geo_point_2d")
            )
            
            # Ajouter zone_fallback au dict métrique (toujours présent)
            metric_dict = metric.to_dict()
            metric_dict["zone_fallback"] = zone_fallback  # Toujours ajouter, même si "Unknown"
            metrics.append(metric_dict)
        
        # Top 10 tronçons fréquentés
        top_10_troncons = sorted(
            metrics,
            key=lambda x: x.get("debit_journalier_total", 0),
            reverse=True
        )[:10]
        
        # Top 10 zones congestionnées (par temps perdu total)
        top_10_zones = sorted(
            metrics,
            key=lambda x: x.get("temps_perdu_total_minutes", 0),
            reverse=True
        )[:10]
        
        # S'assurer que toutes les zones congestionnées ont zone_fallback
        for zone in top_10_zones:
            if "zone_fallback" not in zone or not zone.get("zone_fallback"):
                # Si arrondissement connu
                arr = zone.get("arrondissement", "Unknown")
                if arr != "Unknown":
                    zone["zone_fallback"] = f"Arrondissement {arr}"
                else:
                    # Détecter depuis coordonnées
                    geo_point = zone.get("geo_point_2d")
                    if geo_point:
                        try:
                            lat_str, lon_str = geo_point.split(", ")
                            lon = float(lon_str)
                            lat = float(lat_str)
                            # Essayer plusieurs méthodes
                            zone_detectee = get_zone_from_coordinates(lon, lat)
                            if zone_detectee and zone_detectee != "Unknown":
                                zone["zone_fallback"] = zone_detectee
                            else:
                                quadrant = get_quadrant_from_coordinates(lon, lat)
                                if quadrant and quadrant != "Unknown":
                                    zone["zone_fallback"] = quadrant
                                else:
                                    # Dernier recours : utiliser le libellé
                                    libelle = zone.get("libelle", "")
                                    zone_from_libelle = extract_zone_from_libelle(libelle)
                                    zone["zone_fallback"] = zone_from_libelle if zone_from_libelle else "Unknown"
                        except Exception:
                            zone["zone_fallback"] = "Unknown"
                    else:
                        zone["zone_fallback"] = "Unknown"
        
        # Analyse par zones géographiques (pour zones sans arrondissement)
        zones_grouped = group_by_zone(metrics)
        zones_metrics = calculate_zone_metrics(zones_grouped)
        top_zones_affluence = identify_high_traffic_zones(zones_metrics, top_n=10)
        
        # Alertes congestion
        # Filtrer : exclure les alertes avec débit = 0 (pas de sens logique)
        alertes = [
            m for m in metrics 
            if m.get("congestion_alerte", False) 
            and m.get("debit_journalier_total", 0) > 0  # Ignorer débit = 0
        ]
        
        # S'assurer que toutes les alertes ont zone_fallback
        for alerte in alertes:
            if "zone_fallback" not in alerte:
                # Si pas de zone_fallback mais arrondissement connu, utiliser arrondissement comme zone
                arr = alerte.get("arrondissement", "Unknown")
                if arr != "Unknown":
                    alerte["zone_fallback"] = f"Arrondissement {arr}"
                else:
                    # Essayer de déterminer zone depuis coordonnées
                    geo_point = alerte.get("geo_point_2d")
                    if geo_point:
                        try:
                            lat_str, lon_str = geo_point.split(", ")
                            lon = float(lon_str)
                            lat = float(lat_str)
                            zone = get_zone_from_coordinates(lon, lat)
                            if zone and zone != "Unknown":
                                alerte["zone_fallback"] = zone
                            else:
                                quadrant = get_quadrant_from_coordinates(lon, lat)
                                alerte["zone_fallback"] = quadrant if quadrant else "Unknown"
                        except Exception:
                            alerte["zone_fallback"] = "Unknown"
                    else:
                        alerte["zone_fallback"] = "Unknown"
        
        # Trier par temps perdu total (zones les plus impactées en premier)
        alertes = sorted(
            alertes,
            key=lambda x: x.get("temps_perdu_total_minutes", 0),
            reverse=True
        )
        
        # Métriques globales
        global_metrics = TrafficGlobal(
            date="",  # Sera rempli
            total_vehicules_jour=aggregated_data.get("global", {}).get("total_vehicules_jour", 0.0),
            moyenne_debit_par_troncon=aggregated_data.get("global", {}).get("moyenne_debit_par_troncon", 0.0),
            nombre_troncons_satures=len(alertes),
            taux_disponibilite_capteurs=100.0,  # À calculer avec détection défaillances
            temps_perdu_total_paris=sum(m.get("temps_perdu_total_minutes", 0) for m in metrics)
        )
        
        return {
            "metrics": metrics,
            "top_10_troncons": top_10_troncons,
            "top_10_zones_congestionnees": top_10_zones,
            "top_zones_affluence": top_zones_affluence,  # Analyse par zones (avec/sans arrondissement)
            "alertes_congestion": alertes,
            "global_metrics": global_metrics.to_dict()
        }
    
    def process_large_file(self, file_path: str) -> Dict[str, Any]:
        """
        Traite un gros fichier avec découpe en chunks (simulation EC2)
        
        Args:
            file_path: Chemin du fichier CSV
        
        Returns:
            Résultats agrégés (même structure que process())
        """
        file_size_mb = get_file_size_mb(file_path)
        
        if file_size_mb > MAX_FILE_SIZE_MB or self.use_ec2:
            # Découper en chunks
            print(f"Fichier volumineux ({file_size_mb:.2f} MB) - Découpe en chunks...")
            chunks = chunk_file(file_path, chunk_size=EC2_CHUNK_SIZE)
            print(f"  → {len(chunks)} chunks créés")
            
            # Traiter chaque chunk
            all_metrics = []
            all_top_10 = []
            all_top_zones = []
            all_alertes = []
            total_vehicules = 0.0
            total_temps_perdu = 0.0
            total_troncons = 0
            total_chunks_treated = 0
            
            for i, chunk_path in enumerate(chunks):
                print(f"  → Traitement chunk {i+1}/{len(chunks)}...")
                try:
                    chunk_data = load_csv(chunk_path)
                    cleaned = self.validate_and_clean(chunk_data)
                    aggregated = self.aggregate_daily(cleaned)
                    indicators = self.calculate_indicators(aggregated)
                    
                    # Accumuler les résultats
                    all_metrics.extend(indicators.get("metrics", []))
                    all_top_10.extend(indicators.get("top_10_troncons", []))
                    all_top_zones.extend(indicators.get("top_10_zones_congestionnees", []))
                    all_alertes.extend(indicators.get("alertes_congestion", []))
                    
                    # Accumuler totaux globaux
                    global_m = indicators.get("global_metrics", {})
                    total_vehicules += global_m.get("total_vehicules_jour", 0.0)
                    total_temps_perdu += global_m.get("temps_perdu_total_paris", 0.0)
                    total_troncons += len(indicators.get("metrics", []))
                    total_chunks_treated += 1
                except Exception as e:
                    print(f"    ⚠ Erreur traitement chunk {i+1}: {e}")
                    continue
            
            print(f"  ✓ {total_chunks_treated}/{len(chunks)} chunks traités avec succès")
            
            # Ré-agréger tous les chunks
            # Top 10 final tronçons (tous chunks confondus)
            top_10_final = sorted(
                all_top_10,
                key=lambda x: x.get("debit_journalier_total", 0),
                reverse=True
            )[:10]
            
            # Top 10 final zones (tous chunks confondus)
            top_10_zones_final = sorted(
                all_top_zones,
                key=lambda x: x.get("temps_perdu_total_minutes", 0),
                reverse=True
            )[:10]
            
            # S'assurer que toutes les zones congestionnées ont zone_fallback
            for zone in top_10_zones_final:
                if "zone_fallback" not in zone or not zone.get("zone_fallback"):
                    arr = zone.get("arrondissement", "Unknown")
                    if arr != "Unknown":
                        zone["zone_fallback"] = f"Arrondissement {arr}"
                    else:
                        geo_point = zone.get("geo_point_2d")
                        if geo_point:
                            try:
                                lat_str, lon_str = geo_point.split(", ")
                                lon = float(lon_str)
                                lat = float(lat_str)
                                zone_detectee = get_zone_from_coordinates(lon, lat)
                                if zone_detectee and zone_detectee != "Unknown":
                                    zone["zone_fallback"] = zone_detectee
                                else:
                                    quadrant = get_quadrant_from_coordinates(lon, lat)
                                    zone["zone_fallback"] = quadrant if quadrant else "Unknown"
                            except Exception:
                                zone["zone_fallback"] = "Unknown"
                        else:
                            zone["zone_fallback"] = "Unknown"
            
            # Analyse par zones géographiques (pour tous les chunks)
            zones_grouped = group_by_zone(all_metrics)
            zones_metrics = calculate_zone_metrics(zones_grouped)
            top_zones_affluence_final = identify_high_traffic_zones(zones_metrics, top_n=10)
            
            # Filtrer et nettoyer les alertes (exclure débit = 0, s'assurer zone_fallback présent)
            alertes_filtrees = []
            for alerte in all_alertes:
                # Exclure débit = 0
                if alerte.get("debit_journalier_total", 0) <= 0:
                    continue
                
                # S'assurer que zone_fallback est présent
                if "zone_fallback" not in alerte:
                    arr = alerte.get("arrondissement", "Unknown")
                    if arr != "Unknown":
                        alerte["zone_fallback"] = f"Arrondissement {arr}"
                    else:
                        geo_point = alerte.get("geo_point_2d")
                        if geo_point:
                            try:
                                lat_str, lon_str = geo_point.split(", ")
                                lon = float(lon_str)
                                lat = float(lat_str)
                                zone = get_zone_from_coordinates(lon, lat)
                                if zone and zone != "Unknown":
                                    alerte["zone_fallback"] = zone
                                else:
                                    quadrant = get_quadrant_from_coordinates(lon, lat)
                                    alerte["zone_fallback"] = quadrant if quadrant else "Unknown"
                            except Exception:
                                alerte["zone_fallback"] = "Unknown"
                        else:
                            alerte["zone_fallback"] = "Unknown"
                
                alertes_filtrees.append(alerte)
            
            # Trier par temps perdu total
            alertes_filtrees = sorted(
                alertes_filtrees,
                key=lambda x: x.get("temps_perdu_total_minutes", 0),
                reverse=True
            )
            
            # Métriques globales agrégées
            moyenne_debit = total_vehicules / total_troncons if total_troncons > 0 else 0.0
            nombre_satures = len([m for m in all_metrics if m.get("congestion_alerte", False)])
            
            # Calculer les vrais totaux depuis all_metrics
            debit_total_reel = sum(m.get("debit_journalier_total", 0) for m in all_metrics)
            taux_occupation_moyen = sum(m.get("taux_occupation_moyen", 0) for m in all_metrics) / len(all_metrics) if all_metrics else 0
            temps_perdu_total_heures = sum(m.get("temps_perdu_total_minutes", 0) for m in all_metrics) / 60.0
            
            global_metrics = {
                "date": "",  # Sera rempli par export_results
                "nombre_troncons_actifs": len(set(m.get("identifiant_arc") for m in all_metrics if m.get("identifiant_arc"))),
                "debit_journalier_total": debit_total_reel,
                "taux_occupation_moyen": taux_occupation_moyen,
                "nombre_troncons_satures": nombre_satures,
                "taux_disponibilite_capteurs": 100.0,
                "temps_perdu_total_heures": temps_perdu_total_heures,
                "repartition_etat_trafic": {}  # À calculer si besoin
            }
            
            # Retourner structure compatible avec process()
            return {
                "cleaned_data": None,  # Non disponible après chunks
                "aggregated_data": None,
                "indicators": {
                    "metrics": all_metrics,
                    "top_10_troncons": top_10_final,
                    "top_10_zones_congestionnees": top_10_zones_final,
                    "top_zones_affluence": top_zones_affluence_final,  # Analyse par zones (avec/sans arrondissement)
                    "alertes_congestion": alertes_filtrees[:20],  # Limiter à 20 (filtrées et nettoyées)
                    "global_metrics": global_metrics
                },
                "success": True,
                "errors": []
            }
        else:
            # Traitement normal
            return self.process(load_csv(file_path))

