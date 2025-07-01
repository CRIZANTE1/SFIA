import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def get_latest_locations(df_full):
    if df_full.empty: return pd.DataFrame()
    if 'latitude' not in df_full.columns or 'longitude' not in df_full.columns:
        st.warning("As colunas 'latitude' e 'longitude' não foram encontradas.")
        return pd.DataFrame()
    
    df_full['latitude'] = pd.to_numeric(df_full['latitude'].astype(str).str.replace(',', '.'), errors='coerce')
    df_full['longitude'] = pd.to_numeric(df_full['longitude'].astype(str).str.replace(',', '.'), errors='coerce')
    df_full = df_full.dropna(subset=['latitude', 'longitude'])
    if df_full.empty: return pd.DataFrame()
        
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full = df_full.dropna(subset=['data_servico'])

    return df_full.sort_values('data_servico').drop_duplicates(subset='numero_identificacao', keep='last')

def assign_color_by_agent(df):
    """
    Adiciona uma coluna 'color' ao DataFrame com base no tipo de agente extintor.
    """
    color_map = {
        'ABC': [255, 255, 0, 160], 'BC': [0, 100, 255, 160],
        'CO2': [128, 128, 128, 160], 'Água': [0, 255, 255, 160],
        'Espuma': [0, 200, 0, 160],
    }
    default_color = [255, 75, 75, 160]

    conditions = [
        df['tipo_agente'].str.contains("ABC", case=False, na=False),
        df['tipo_agente'].str.contains("BC", case=False, na=False),
        df['tipo_agente'].str.contains("CO2", case=False, na=False),
        df['tipo_agente'].str.contains("Água", case=False, na=False),
        df['tipo_agente'].str.contains("Espuma", case=False, na=False),
    ]
    choices = [color_map['ABC'], color_map['BC'], color_map['CO2'], color_map['Água'], color_map['Espuma']]
    
  
    df['color'] = np.select(conditions, choices, default=default_color).tolist()
    
    return df

def show_map_page():
    st.title("🗺️ Mapa do Sistema de Combate a Incêndio (SCI)")
    st.info("Visualize a localização geográfica dos equipamentos de emergência.")

    equip_type = st.selectbox("Selecione o tipo de equipamento para visualizar:", ["Extintores", "Mangueiras (em breve)"])
    st.markdown("---")

    if equip_type == "Extintores":
        st.header("Localização dos Extintores")
        df_history = load_sheet_data("extintores")
        
        if df_history.empty:
            st.warning("Não há dados de extintores para exibir no mapa."); return

        with st.spinner("Processando localizações..."):
            locations_df = get_latest_locations(df_history)

        if locations_df.empty:
            st.warning("Nenhum extintor com dados de geolocalização válidos foi encontrado."); return
        
        locations_df = assign_color_by_agent(locations_df)

        st.success(f"Exibindo a localização de **{len(locations_df)}** extintores.")
                
        map_data = locations_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        
        st.map(map_data, zoom=16, size=0.3, color='color')

        with st.expander("Ver detalhes e legenda de cores"):
            st.markdown("##### Legenda de Cores")
            st.markdown("""
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(255,255,0,0.8);"></span> Pó Químico ABC
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,100,255,0.8);"></span> Pó Químico BC
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(128,128,128,0.8);"></span> Dióxido de Carbono (CO2)
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,255,255,0.8);"></span> Água Pressurizada
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,200,0,0.8);"></span> Espuma Mecânica
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(255,75,75,0.8);"></span> Outros
            """, unsafe_allow_html=True)
            st.markdown("---")
            
            st.dataframe(
                locations_df[[
                    'numero_identificacao', 'numero_selo_inmetro', 'tipo_agente', 
                    'latitude', 'longitude'
                ]].rename(columns={
                    'numero_identificacao': 'ID do Equipamento', 'numero_selo_inmetro': 'Último Selo',
                    'tipo_agente': 'Tipo'
                }),
                hide_index=True, use_container_width=True
            )

    elif equip_type == "Mangueiras (em breve)":
        st.header("Localização das Mangueiras")
        st.info("Esta funcionalidade está em desenvolvimento.")

# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_map_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
