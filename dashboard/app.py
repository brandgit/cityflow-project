"""
Dashboard Streamlit COMPLET pour CityFlow Analytics
"""

import streamlit as st
import json
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Configuration
st.set_page_config(
    page_title="CityFlow Analytics",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🚦 CityFlow Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Analyse en temps réel de la mobilité urbaine à Paris**")

# Sidebar
with st.sidebar:
    st.title("📊 Configuration")
    
    # Sélection de la date
    date = st.date_input("📅 Date", value=None)
    if date:
        date_str = date.strftime("%Y-%m-%d")
    else:
        date_str = "2025-11-04"
    
    st.info(f"Date sélectionnée: **{date_str}**")
    
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "🗺️ Navigation",
        ["🏠 Vue d'ensemble", "🚴 Vélos", "🚇 RATP", "🚗 Trafic Routier", "🚧 Chantiers"]
    )
    
    st.markdown("---")
    st.caption("CityFlow Analytics © 2025")

# Fonction de chargement
@st.cache_data
def load_metrics(metric_type, date):
    """Charge les métriques depuis JSON"""
    file_path = Path(f"output/metrics/{metric_type}_metrics_{date}.json")
    if not file_path.exists():
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Charger toutes les métriques
bikes = load_metrics("bikes", date_str)
traffic = load_metrics("traffic", date_str)
comptages = load_metrics("comptages", date_str)
chantiers = load_metrics("chantiers", date_str)

# ============================================================================
# PAGE: VUE D'ENSEMBLE
# ============================================================================
if page == "🏠 Vue d'ensemble":
    st.header("📈 Vue d'ensemble")
    
    # KPIs principaux
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if bikes:
            nb = len(bikes.get("metrics", []))
            passages = sum(m.get("total_jour", 0) for m in bikes.get("metrics", []))
            st.metric("🚴 Compteurs Vélo", nb, delta=f"{passages:,.0f} passages")
        else:
            st.metric("🚴 Compteurs Vélo", "N/A")
    
    with col2:
        if traffic:
            active = traffic.get("active_disruptions_count", 0)
            total = traffic.get("total_disruptions_count", 0)
            st.metric("🚇 Perturbations RATP", active, delta=f"{total} total")
        else:
            st.metric("🚇 Perturbations RATP", "N/A")
    
    with col3:
        if comptages:
            gm = comptages.get("global_metrics", {})
            troncons = gm.get("nombre_troncons_actifs", 0)
            debit = gm.get("debit_journalier_total", 0)
            st.metric("🚗 Tronçons", troncons, delta=f"{debit:,.0f} véhicules")
        else:
            st.metric("🚗 Tronçons", "N/A")
    
    with col4:
        if chantiers:
            nb = chantiers.get("total_chantiers_actifs", 0)
            st.metric("🚧 Chantiers", nb)
        else:
            st.metric("🚧 Chantiers", "N/A")
    
    st.markdown("---")
    
    # Graphiques principaux
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚇 Perturbations RATP par sévérité")
        if traffic:
            sev = traffic.get("disruptions_by_severity", {})
            fig = px.bar(x=list(sev.keys()), y=list(sev.values()),
                        labels={"x": "Sévérité", "y": "Nombre"},
                        color=list(sev.values()),
                        color_continuous_scale="Reds")
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Pas de données RATP")
    
    with col2:
        st.subheader("🚗 État du trafic routier")
        if comptages:
            gm = comptages.get("global_metrics", {})
            etat = gm.get("repartition_etat_trafic", {})
            if etat:
                fig = px.pie(values=list(etat.values()), names=list(etat.keys()),
                            hole=0.4, color_discrete_sequence=px.colors.sequential.RdYlGn_r)
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")
            else:
                # Jauge de taux d'occupation
                taux = gm.get("taux_occupation_moyen", 0)
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=taux,
                    title={'text': "Taux d'occupation (%)"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': "darkblue"},
                           'steps': [
                               {'range': [0, 30], 'color': "lightgreen"},
                               {'range': [30, 50], 'color': "yellow"},
                               {'range': [50, 70], 'color': "orange"},
                               {'range': [70, 100], 'color': "red"}
                           ]}
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("Pas de données de trafic")

# ============================================================================
# PAGE: VÉLOS
# ============================================================================
elif page == "🚴 Vélos":
    st.header("🚴 Compteurs Vélo Vélib'")
    
    if not bikes:
        st.error("❌ Aucune donnée vélo disponible")
    else:
        metrics_list = bikes.get("metrics", [])
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Compteurs actifs", len(metrics_list))
        with col2:
            total = sum(m.get("total_jour", 0) for m in metrics_list)
            st.metric("Total passages", f"{total:,.0f}")
        with col3:
            avg = sum(m.get("moyenne_horaire", 0) for m in metrics_list) / len(metrics_list) if metrics_list else 0
            st.metric("Moyenne horaire", f"{avg:.1f}")
        with col4:
            anomalies = len(bikes.get("anomalies", []))
            st.metric("Anomalies détectées", anomalies)
        
        st.markdown("---")
        
        # Top 10 compteurs
        st.subheader("🏆 Top 10 compteurs les plus fréquentés")
        top = bikes.get("top_counters", [])[:10]
        if top:
            df = pd.DataFrame(top)
            fig = px.bar(df, x="nom_compteur", y="total_jour",
                        labels={"nom_compteur": "Compteur", "total_jour": "Passages"},
                        color="total_jour", color_continuous_scale="Blues")
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, width="stretch")
            
            # Tableau détaillé
            with st.expander("📋 Voir le détail"):
                display_df = df[["nom_compteur", "total_jour", "moyenne_horaire", "arrondissement"]]
                display_df.columns = ["Compteur", "Total jour", "Moy. horaire", "Arrondissement"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Carte des compteurs par arrondissement
        st.markdown("---")
        st.subheader("🗺️ Répartition par arrondissement")
        arr_data = {}
        for m in metrics_list:
            arr = m.get("arrondissement", "Inconnu")
            # Filtrer les valeurs vides ou None
            if arr and arr.strip():
                arr_data[arr] = arr_data.get(arr, 0) + m.get("total_jour", 0)
        
        if arr_data:
            df_arr = pd.DataFrame(list(arr_data.items()), columns=["Arrondissement", "Passages"])
            df_arr = df_arr.sort_values("Passages", ascending=False).head(15)
            
            # Utiliser un graphique en barres au lieu de treemap (plus simple)
            fig = px.bar(df_arr, x="Arrondissement", y="Passages",
                        color="Passages", color_continuous_scale="Greens")
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, width="stretch")

# ============================================================================
# PAGE: RATP
# ============================================================================
elif page == "🚇 RATP":
    st.header("🚇 Perturbations RATP")
    
    if not traffic:
        st.error("❌ Aucune donnée RATP disponible")
    else:
        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total perturbations", traffic.get("total_disruptions_count", 0))
        with col2:
            st.metric("Perturbations actives", traffic.get("active_disruptions_count", 0))
        with col3:
            reliability = traffic.get("reliability_index", 0) * 100
            st.metric("Fiabilité", f"{reliability:.1f}%")
        
        st.markdown("---")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Par sévérité")
            sev = traffic.get("disruptions_by_severity", {})
            fig = px.pie(values=list(sev.values()), names=list(sev.keys()),
                        color_discrete_sequence=["#d62728", "#ff7f0e", "#ffbb78", "#2ca02c"])
            fig.update_layout(height=300)
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            st.subheader("🚇 Lignes les plus impactées")
            top_lignes = traffic.get("top_lignes_impactees", [])[:10]
            if top_lignes:
                df = pd.DataFrame(top_lignes)
                fig = px.bar(df, x="ligne", y="count",
                            labels={"ligne": "Ligne", "count": "Perturbations"},
                            color="count", color_continuous_scale="Reds")
                fig.update_layout(height=300)
                st.plotly_chart(fig, width="stretch")
        
        # Alertes
        st.markdown("---")
        st.subheader("⚠️ Alertes critiques")
        alerts = traffic.get("alerts", [])[:20]
        if alerts:
            st.warning(f"🚨 {len(alerts)} alertes critiques détectées")
            for i, alert in enumerate(alerts[:10], 1):
                lignes = alert.get("lignes", [])
                lignes_str = ", ".join([f"Ligne {l}" for l in lignes]) if lignes else "Réseau général"
                with st.expander(f"{i}. {lignes_str} - Priorité {alert.get('priority', 0)}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Durée:** {alert.get('duration_hours', 0):.1f}h")
                    with col2:
                        st.write(f"**ID:** {alert.get('id', 'N/A')[:20]}...")
        else:
            st.success("✅ Aucune alerte critique")

# ============================================================================
# PAGE: TRAFIC ROUTIER
# ============================================================================
elif page == "🚗 Trafic Routier":
    st.header("🚗 Trafic Routier")
    
    if not comptages:
        st.error("❌ Aucune donnée de trafic disponible")
    else:
        gm = comptages.get("global_metrics", {})
        
        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tronçons actifs", gm.get("nombre_troncons_actifs", 0))
        with col2:
            debit = gm.get("debit_journalier_total", 0)
            st.metric("Débit total", f"{debit:,.0f}")
        with col3:
            taux = gm.get("taux_occupation_moyen", 0)
            st.metric("Taux occupation", f"{taux:.1f}%")
        with col4:
            temps = gm.get("temps_perdu_total_heures", 0)
            st.metric("Temps perdu", f"{temps:,.0f}h")
        
        st.markdown("---")
        
        # Top 10 tronçons
        st.subheader("🏆 Top 10 tronçons les plus fréquentés")
        top = comptages.get("top_10_troncons", [])
        if top:
            df = pd.DataFrame(top)
            df_display = df[["libelle", "zone_fallback", "debit_journalier_total", "taux_occupation_moyen", "etat_trafic_dominant"]].copy()
            df_display.columns = ["Tronçon", "Zone", "Débit", "Taux occ. (%)", "État"]
            df_display["Débit"] = df_display["Débit"].apply(lambda x: f"{x:,.0f}")
            df_display["Taux occ. (%)"] = df_display["Taux occ. (%)"].round(1)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Zones congestionnées
        st.subheader("⚠️ Zones les plus congestionnées")
        top_zones = comptages.get("top_10_zones_congestionnees", [])[:5]
        if top_zones:
            for i, zone in enumerate(top_zones, 1):
                with st.expander(f"{i}. {zone.get('libelle', 'N/A')} - {zone.get('zone_fallback', 'Zone inconnue')}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Débit", f"{zone.get('debit_journalier_total', 0):,.0f}")
                    with col2:
                        st.metric("Taux occ.", f"{zone.get('taux_occupation_moyen', 0):.1f}%")
                    with col3:
                        st.metric("Temps perdu", f"{zone.get('temps_perdu_total_minutes', 0):,.0f} min")
                    st.info(f"**État:** {zone.get('etat_trafic_dominant', 'Inconnu')}")
        
        # Analyse par zones
        st.markdown("---")
        st.subheader("🗺️ Top zones par affluence")
        top_zones_aff = comptages.get("top_zones_affluence", [])[:10]
        if top_zones_aff:
            df = pd.DataFrame(top_zones_aff)
            # Utiliser le bon nom de colonne : total_vehicules au lieu de debit_total
            fig = px.bar(df, x="zone", y="total_vehicules",
                        labels={"zone": "Zone", "total_vehicules": "Total véhicules"},
                        color="total_vehicules", color_continuous_scale="Blues")
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, width="stretch")

# ============================================================================
# PAGE: CHANTIERS
# ============================================================================
elif page == "🚧 Chantiers":
    st.header("🚧 Chantiers Perturbants")
    
    if not chantiers:
        st.error("❌ Aucune donnée chantiers disponible")
    else:
        # KPIs
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Chantiers actifs", chantiers.get("total_chantiers_actifs", 0))
        with col2:
            surface = chantiers.get("surface_totale_impactee_m2", 0)
            st.metric("Surface impactée", f"{surface:,.0f} m²")
        
        st.markdown("---")
        
        # Impact par arrondissement
        st.subheader("📊 Impact par arrondissement")
        impact_arr = chantiers.get("impact_by_arrondissement", {})
        if impact_arr:
            top_arr = sorted(impact_arr.items(), key=lambda x: x[1], reverse=True)[:10]
            df = pd.DataFrame(top_arr, columns=["Arrondissement", "Impact (%)"])
            
            fig = px.bar(df, x="Arrondissement", y="Impact (%)",
                        color="Impact (%)", color_continuous_scale="Reds")
            fig.update_layout(height=400)
            st.plotly_chart(fig, width="stretch")
        
        # Zones critiques
        st.markdown("---")
        st.subheader("🚨 Zones critiques")
        zones_crit = chantiers.get("zones_critiques", [])
        if zones_crit:
            st.warning(f"⚠️ {len(zones_crit)} zones avec plus de 3 chantiers simultanés")
            df = pd.DataFrame(zones_crit)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Aucune zone critique détectée")

# ============================================================================
# SECTION COMMUNE : STATISTIQUES AVANCÉES
# ============================================================================
if page == "🏠 Vue d'ensemble":
    st.markdown("---")
    st.subheader("📊 Statistiques détaillées")
    
    tab1, tab2, tab3 = st.tabs(["🚴 Vélos", "🚇 RATP", "🚗 Trafic"])
    
    with tab1:
        if bikes:
            metrics_list = bikes.get("metrics", [])
            col1, col2 = st.columns(2)
            
            with col1:
                # Distribution par arrondissement
                arr_counts = {}
                for m in metrics_list:
                    arr = m.get("arrondissement", "Inconnu")
                    arr_counts[arr] = arr_counts.get(arr, 0) + 1
                
                df = pd.DataFrame(list(arr_counts.items()), columns=["Arrondissement", "Compteurs"])
                df = df.sort_values("Compteurs", ascending=False).head(10)
                fig = px.bar(df, x="Arrondissement", y="Compteurs", color="Compteurs")
                fig.update_layout(height=300, title="Compteurs par arrondissement")
                st.plotly_chart(fig, width="stretch")
            
            with col2:
                # Top 5 compteurs
                top = bikes.get("top_counters", [])[:5]
                st.write("**Top 5 compteurs:**")
                for i, c in enumerate(top, 1):
                    st.write(f"{i}. {c.get('nom_compteur', 'N/A')}: **{c.get('total_jour', 0):,.0f}** passages")
    
    with tab2:
        if traffic:
            col1, col2 = st.columns(2)
            
            with col1:
                # Lignes impactées
                top_lignes = traffic.get("top_lignes_impactees", [])[:5]
                st.write("**Lignes les plus impactées:**")
                for ligne in top_lignes:
                    st.write(f"Ligne **{ligne.get('ligne')}**: {ligne.get('count')} perturbations")
            
            with col2:
                # Alertes par priorité
                alerts = traffic.get("alerts", [])
                if alerts:
                    st.write(f"**{len(alerts)} alertes critiques**")
                    avg_duration = sum(a.get("duration_hours", 0) for a in alerts) / len(alerts)
                    st.write(f"Durée moyenne: **{avg_duration:.1f}h**")
    
    with tab3:
        if comptages:
            col1, col2 = st.columns(2)
            
            with col1:
                # Top tronçons
                top = comptages.get("top_10_troncons", [])[:5]
                st.write("**Top 5 tronçons:**")
                for i, t in enumerate(top, 1):
                    st.write(f"{i}. {t.get('libelle', 'N/A')}: **{t.get('debit_journalier_total', 0):,.0f}** véhicules")
            
            with col2:
                # Alertes congestion
                alertes = comptages.get("alertes_congestion", [])
                if alertes:
                    st.write(f"**{len(alertes)} alertes de congestion**")
                    temps_total = sum(a.get("temps_perdu_total_minutes", 0) for a in alertes[:10])
                    st.write(f"Temps perdu (top 10): **{temps_total:,.0f} min**")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🚴 Données vélo: Open Data Paris")
with col2:
    st.caption("🚇 Données RATP: API temps réel")
with col3:
    st.caption("🚗 Données trafic: Capteurs permanents")
