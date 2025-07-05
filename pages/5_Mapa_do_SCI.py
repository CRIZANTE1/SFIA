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
from config.page_config import set_page_config 

set_page_config()

def get_latest_locations(df_full):
    if df_full.empty: return pd.DataFrame()
    df = df_full.copy()
    df['data_servico'] = pd.to_datetime(df['data_servico'], errors='coerce')
    df = df.dropna(subset=['data_servico'])
    latest_records_df = df.sort_values('data_servico').drop_duplicates(subset='numero_identificacao', keep='last')
    if 'latitude' not in latest_records_df.columns or 'longitude' not in latest_records_df.columns: return pd.DataFrame()
    latest_records_df['latitude'] = pd.to_numeric(latest_records_df['latitude'].astype(str).str.replace(',', '.'), errors='coerce')
    latest_records_df['longitude'] = pd.to_numeric(latest_records_df['longitude'].astype(str).str.replace(',', '.'), errors='coerce')
    return latest_records_df.dropna(subset=['latitude', 'longitude'])

def assign_visual_properties(df):
    df_copy = df.copy()
    color_map = {'ABC': [255, 255, 0, 160], 'BC': [0, 100, 255, 160], 'CO2': [128, 128, 128, 160], 'Água': [0, 255, 255, 160], 'Espuma': [0, 200, 0, 160]}
    default_color = [255, 0, 0, 180]
    def get_color(agent_type):
        agent_type_str = str(agent_type).upper()
        for key, color in color_map.items():
            if key in agent_type_str:
                return color
        return default_color
    df_copy['color'] = df_copy['tipo_agente'].apply(get_color)
    df_copy['capacidade_num'] = pd.to_numeric(df_copy['capacidade'].astype(str).str.extract(r'(\d+\.?\d*)')[0], errors='coerce').fillna(1)
    df_copy['size'] = 0.3 + (df_copy['capacidade_num'] * 0.1)
    return df_copy

def show_map_page():
    st.title("🗺️ Mapa do Sistema de Combate a Incêndio (SCI)")
    st.info("Visualize a localização, tipo (por cor) e capacidade (por tamanho) dos equipamentos.")

    equip_type = st.selectbox("Selecione o tipo de equipamento:", ["Extintores", "Mangueiras (em breve)"])
    st.markdown("---")

    if equip_type == "Extintores":
        st.header("Localização dos Extintores")
        df_history = load_sheet_data("extintores")
        
        if df_history.empty:
            st.warning("Não há dados de extintores para exibir no mapa."); return

        with st.spinner("Processando localizações..."):
            locations_df = get_latest_locations(df_history)

        if not locations_df.empty:
            locations_df = assign_visual_properties(locations_df)
            st.success(f"Exibindo a localização de **{len(locations_df)}** extintores no mapa.")
            map_data = locations_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
            st.map(map_data, zoom=16, size='size', color='color')
        else:
            st.warning("Nenhum extintor com dados de geolocalização válidos foi encontrado.")

        # --- LEGENDA DE CORES REINTRODUZIDA AQUI ---
        with st.expander("Ver detalhes dos equipamentos instalados e legenda"):
            st.markdown("**Legenda de Cores:**")
            st.markdown("""
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(255,255,0,0.8);"></span> Pó Químico ABC
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,100,255,0.8);"></span> Pó Químico BC
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(128,128,128,0.8);"></span> Dióxido de Carbono (CO2)
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,255,255,0.8);"></span> Água
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(0,200,0,0.8);"></span> Espuma
                - <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background-color:rgba(255,0,0,0.8);"></span> Outros
            """, unsafe_allow_html=True)
            st.markdown("---")
            
            # A tabela de detalhes agora mostra todos os equipamentos do histórico, não apenas os do mapa
            # É importante garantir que esta lógica seja consistente com a do dashboard
            all_latest_df_for_display = df_history.sort_values('data_servico').drop_duplicates(subset='numero_identificacao', keep='last')
            if all_latest_df_for_display.empty:
                st.info("Nenhum equipamento registrado para exibir detalhes.")
            else:
                st.dataframe(
                    all_latest_df_for_display[[
                        'numero_identificacao', 'numero_selo_inmetro', 'tipo_agente', 
                        'capacidade', 'latitude', 'longitude'
                    ]].rename(columns={
                        'numero_identificacao': 'ID do Equipamento', 'numero_selo_inmetro': 'Último Selo',
                        'tipo_agente': 'Tipo', 'capacidade': 'Capacidade'
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
