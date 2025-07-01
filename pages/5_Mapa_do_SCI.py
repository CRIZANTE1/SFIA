import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def get_latest_locations(df_full):
    # (Esta função não muda)
    if df_full.empty: return pd.DataFrame()
    if 'latitude' not in df_full.columns or 'longitude' not in df_full.columns: return pd.DataFrame()
    df_full['latitude'] = pd.to_numeric(df_full['latitude'].astype(str).str.replace(',', '.'), errors='coerce')
    df_full['longitude'] = pd.to_numeric(df_full['longitude'].astype(str).str.replace(',', '.'), errors='coerce')
    df_full.dropna(subset=['latitude', 'longitude'], inplace=True)
    if df_full.empty: return pd.DataFrame()
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full.dropna(subset=['data_servico'], inplace=True)
    return df_full.sort_values('data_servico').drop_duplicates(subset='numero_identificacao', keep='last')

def assign_visual_properties(df):
    """
    Cria colunas de 'size' e 'color' com base nos dados do equipamento.
    """
    # 1. Definir Cores por Tipo de Agente
    color_map = {
        'ABC': [255, 255, 0, 180],  # Amarelo translúcido
        'BC':  [0, 0, 255, 180],    # Azul translúcido
        'CO2': [128, 128, 128, 180],# Cinza translúcido
        'ÁGUA': [0, 100, 255, 180], # Azul claro translúcido
        'ESPUMA': [0, 128, 0, 180], # Verde escuro translúcido
    }
    default_color = [255, 0, 0, 180] # Vermelho padrão para tipos não mapeados

    # Aplica a cor com base no tipo_agente
    df['color'] = df['tipo_agente'].apply(lambda x: color_map.get(x, default_color))
    
    # 2. Definir Tamanho por Capacidade
    # Extrai o número da capacidade (ex: '6 kg' -> 6)
    df['capacidade_num'] = df['capacidade'].str.extract('(\d+\.?\d*)').astype(float).fillna(1)
    
    # Mapeia a capacidade para um tamanho no mapa (ex: capacidade * 10 = tamanho em metros)
    df['size'] = df['capacidade_num'] * 0.50
    
    return df

def show_map_page():
    st.title("🗺️ Mapa do Sistema de Combate a Incêndio (SCI)")
    st.info("Visualize a localização geográfica dos equipamentos de emergência.")

    equip_type = st.selectbox("Selecione o tipo de equipamento:", ["Extintores", "Mangueiras (em breve)"])
    st.markdown("---")

    if equip_type == "Extintores":
        st.header("Localização dos Extintores")
        df_history = load_sheet_data("extintores")
        
        if df_history.empty:
            st.warning("Não há dados de extintores para exibir no mapa."); return

        with st.spinner("Processando localizações..."):
            locations_df = get_latest_locations(df_history)

        if locations_df.empty:
            st.warning("Nenhum extintor com dados de geolocalização válidos."); return

        # --- MELHORIA APLICADA AQUI ---
        # Adiciona as propriedades visuais ao DataFrame
        locations_df = assign_visual_properties(locations_df)
        
        st.success(f"Exibindo a localização de **{len(locations_df)}** extintores.")
        
        # Prepara os dados para o st.map
        map_data = locations_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})
        
        # Exibe o mapa com tamanho e cor dinâmicos
        st.map(map_data, zoom=16, size='size', color='color')

        with st.expander("Ver detalhes e legenda"):
            # Legenda de cores
            st.markdown("**Legenda de Cores:**")
            st.markdown("""
                - <span style="color:yellow; font-weight:bold;">●</span> Pó Químico ABC
                - <span style="color:blue; font-weight:bold;">●</span> Pó Químico BC
                - <span style="color:grey; font-weight:bold;">●</span> Dióxido de Carbono (CO2)
                - <span style="color:cyan; font-weight:bold;">●</span> Água
                - <span style="color:green; font-weight:bold;">●</span> Espuma
            """, unsafe_allow_html=True)
            
            st.dataframe(
                locations_df[[
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
