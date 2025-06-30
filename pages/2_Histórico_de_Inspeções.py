# pages/2_Historico_de_Inspecoes.py

import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# IMPORTAÇÃO CORRIGIDA AQUI:
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def make_urls_clickable(url):
    """Transforma uma URL em um link HTML clicável, se for uma URL válida."""
    if isinstance(url, str) and url.startswith('http'):
        return f'<a href="{url}" target="_blank">Abrir Foto</a>'
    return "N/A"

def show_history_page():
    st.title("Histórico de Inspeções de Extintores")
    st.info("Os dados são atualizados a cada 10 minutos. Para forçar a atualização, limpe o cache.")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner("Carregando histórico de inspeções..."):
        df_inspections = load_sheet_data("extintores")

    if df_inspections.empty:
        st.warning("Não foi possível carregar os dados do histórico ou a planilha está vazia.")
        return

    # Garante que a coluna 'URL_Foto' exista para evitar erros
    if 'URL_Foto' not in df_inspections.columns:
        df_inspections['URL_Foto'] = "N/A"
        
    # Transforma a coluna de URL em links clicáveis
    # df_inspections['URL_Foto'] = df_inspections['URL_Foto'].apply(make_urls_clickable)

    st.subheader("Buscar Inspeção por ID do Extintor")
    id_column = 'numero_identificacao'
    
    search_id = st.text_input("Digite o ID do Extintor (ex: EXT-001)", key="search_id_input")

    if search_id:
        result_df = df_inspections[df_inspections[id_column].str.contains(search_id, case=False, na=False)]
        if not result_df.empty:
            st.markdown("### Resultados da Busca")
            st.dataframe(result_df)
        else:
            st.info(f"Nenhum registro encontrado para o ID: {search_id}")

    st.markdown("---")
    st.subheader("Histórico Completo de Inspeções")
    st.dataframe(df_inspections)

# --- Boilerplate de Autenticação para a Página ---
if not show_login_page():
    st.stop()

show_user_header()
show_logout_button()

if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_history_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()