"""
Fonctions de création de graphiques réutilisables
"""

import plotly.graph_objects as go
import streamlit as st


def create_gauge_chart(value: float, title: str, max_value: float = 100):
    """
    Crée une jauge
    
    Args:
        value: Valeur à afficher
        title: Titre de la jauge
        max_value: Valeur maximale
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_value * 0.3], 'color': "lightgreen"},
                {'range': [max_value * 0.3, max_value * 0.7], 'color': "yellow"},
                {'range': [max_value * 0.7, max_value], 'color': "red"}
            ]
        }
    ))
    
    return fig


def create_kpi_card(label: str, value: str, delta: str = None):
    """
    Crée une carte KPI
    
    Args:
        label: Label du KPI
        value: Valeur principale
        delta: Variation (optionnel)
    """
    st.markdown(f"""
    <div style="
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    ">
        <h4 style="color: #666; margin: 0; font-size: 0.9rem;">{label}</h4>
        <h2 style="color: #1f77b4; margin: 0.5rem 0; font-size: 2rem;">{value}</h2>
        {f'<p style="color: green; margin: 0;">{delta}</p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

