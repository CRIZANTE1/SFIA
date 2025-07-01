import streamlit as st
import pandas as pd
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def get_latest_locations(df_full):
    """
    Processa o histórico completo para obter a localização mais recente de cada equipamento.
    Lida com vírgulas como separadores decimais.
    """
    if df_full.empty:
        return pd.DataFrame()

    if 'latitude' not in df_full.columns or 'longitude' not in df_full.columns:
        st.warning("As colunas 'latitude' e 'longitude' não foram encontradas na planilha.")
        return pd.DataFrame()
    
    # Garante que as colunas sejam do tipo string para poder usar .str
    df_full['latitude'] = df_full['latitude'].astype(str)
    df_full['longitude'] = df_full['longitude'].astype(str)

    # Substitui a vírgula decimal por um ponto
    df_full['latitude'] = df_full['latitude'].str.replace(',', '.', regex=False)
    df_full['longitude'] = df_full['longitude'].str.replace(',', '.', regex=False)
    
    # Força a conversão para tipo numérico
    df_full['latitude'] = pd.to_numeric(df_full['latitude'], errors='coerce')
    df_full['longitude'] = pd.to_numeric(df_full['longitude'], errors='coerce')
    
    # Remove linhas onde a localização é nula
    df_full.dropna(subset=['latitude', 'longitude'], inplace=True)

    if df_full.empty:
        return pd.DataFrame()
        
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full.dropna(subset=['data_servico'], inplace=True)

    # Pega o registro mais recente (última localização conhecida)
    latest_locations_df = df_full.sort_values('data_servico').drop_duplicates(
        subset='numero_identificacao', 
        keep='last'
    )
    
    return latest_locations_df

def show_map_page():
    st.title("🗺️ Mapa do Sistema de Combate a Incêndio (SCI)")
    st.info("Visualize a localização geográfica dos equipamentos de emergência.")

    equip_type = st.selectbox(
        "Selecione o tipo de equipamento para visualizar:",
        ["Extintores", "Mangueiras (em breve)"]
    )
    
    st.markdown("---")

    if equip_type == "Extintores":
        st.header("Localização dos Extintores")
        df_history = load_sheet_data("extintores")
        
        if df_history.empty:
            st.warning("Não há dados de extintores para exibir no mapa.")
            return

        with st.spinner("Processando localizações..."):
            locations_df = get_latest_locations(df_history)

        if locations_df.empty:
            st.warning("Nenhum extintor com dados de geolocalização válidos foi encontrado.")
            return

        st.success(f"Exibindo a localização de **{len(locations_df)}** extintores.")
                
        # 1. Prepara os dados para o st.map
        map_data = locations_df[['latitude', 'longitude']].copy()
        map_data.rename(columns={'latitude': 'lat', 'longitude': 'lon'}, inplace=True)
        
        # 2. Define o tamanho dos pontos. Você pode ajustar este valor.
        # Valores menores = pontos menores.
        tamanho_do_ponto = 0.3

        # 3. Exibe o mapa com o tamanho personalizado
        st.map(map_data, zoom=16, size=tamanho_do_ponto)

        with st.expander("Ver detalhes dos equipamentos no mapa"):
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
if not show_login_page():
    st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_map_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()

