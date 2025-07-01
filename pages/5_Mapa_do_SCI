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
    Retorna um DataFrame com id, lat, lon e informações adicionais para o tooltip.
    """
    if df_full.empty or 'latitude' not in df_full.columns or 'longitude' not in df_full.columns:
        return pd.DataFrame()

    # Garante que as colunas de coordenadas sejam numéricas, tratando erros
    df_full['latitude'] = pd.to_numeric(df_full['latitude'], errors='coerce')
    df_full['longitude'] = pd.to_numeric(df_full['longitude'], errors='coerce')
    
    # Remove linhas onde a localização não é válida
    df_full.dropna(subset=['latitude', 'longitude'], inplace=True)

    if df_full.empty:
        return pd.DataFrame()
        
    # Garante que a data do serviço seja do tipo datetime para ordenação
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full.dropna(subset=['data_servico'], inplace=True)

    # Pega o registro mais recente (última localização conhecida) para cada equipamento
    latest_locations_df = df_full.sort_values('data_servico').drop_duplicates(
        subset='numero_identificacao', 
        keep='last'
    )
    
    return latest_locations_df

def show_map_page():
    st.title("🗺️ Mapa do Sistema de Combate a Incêndio (SCI)")
    st.info("Visualize a localização geográfica dos equipamentos de emergência.")

    # --- Seletor de Tipo de Equipamento ---
    equip_type = st.selectbox(
        "Selecione o tipo de equipamento para visualizar:",
        ["Extintores", "Mangueiras (em breve)"]
    )
    
    st.markdown("---")

    # --- Lógica para Extintores ---
    if equip_type == "Extintores":
        st.header("Localização dos Extintores")
        
        # Carrega todos os dados históricos
        df_history = load_sheet_data("extintores")
        
        if df_history.empty:
            st.warning("Não há dados de extintores para exibir no mapa.")
            return

        with st.spinner("Processando localizações..."):
            # Obtém a localização mais recente de cada extintor
            locations_df = get_latest_locations(df_history)

        if locations_df.empty:
            st.warning("Nenhum extintor com dados de geolocalização válidos foi encontrado.")
            return

        st.success(f"Exibindo a localização de **{len(locations_df)}** extintores.")
        
        # Prepara os dados para o st.map
        # O st.map precisa especificamente de colunas chamadas 'lat' e 'lon'
        map_data = locations_df[['latitude', 'longitude']].copy()
        map_data.rename(columns={'latitude': 'lat', 'longitude': 'lon'}, inplace=True)

        # Exibe o mapa
        st.map(map_data, zoom=15) # Ajuste o zoom conforme necessário

        # Exibe uma tabela com detalhes para referência
        with st.expander("Ver detalhes dos equipamentos no mapa"):
            st.dataframe(
                locations_df[[
                    'numero_identificacao', 
                    'numero_selo_inmetro', 
                    'tipo_agente', 
                    'latitude', 
                    'longitude'
                ]].rename(columns={
                    'numero_identificacao': 'ID do Equipamento',
                    'numero_selo_inmetro': 'Último Selo',
                    'tipo_agente': 'Tipo'
                }),
                hide_index=True,
                use_container_width=True
            )

    # --- Placeholder para Mangueiras ---
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
