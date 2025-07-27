import streamlit as st
import pandas as pd
import sys
import os
from config.page_config import set_page_config 

set_page_config()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page
from gdrive.config import (
    EXTINGUISHER_SHEET_NAME, HOSE_SHEET_NAME, SHELTER_SHEET_NAME,
    INSPECTIONS_SHELTER_SHEET_NAME, SCBA_SHEET_NAME, SCBA_VISUAL_INSPECTIONS_SHEET_NAME,
    LOG_ACTIONS, LOG_SHELTER_SHEET_NAME, LOG_SCBA_SHEET_NAME
)


def format_dataframe_for_display(df, is_log=False):
    """
    Prepara o DataFrame para exibição, renomeando colunas e formatando.
    """
    if df.empty:
        return df
    
    df = df.copy()

    if is_log:
        if 'data_correcao' in df.columns:
            df['data_correcao'] = pd.to_datetime(df['data_correcao'], errors='coerce').dt.strftime('%d/%m/%Y')
        
        if 'link_foto_evidencia' not in df.columns:
            df['link_foto_evidencia'] = None
        
        display_columns = {
            'data_correcao': 'Data da Correção',
            'id_equipamento': 'ID do Equipamento',
            'problema_original': 'Problema Original',
            'acao_realizada': 'Ação Realizada',
            'responsavel_acao': 'Responsável',
            'id_equipamento_substituto': 'ID do Equip. Substituto',
            'link_foto_evidencia': 'Evidência (Foto)'
        }
    else:
        # Formatação para o Histórico de Serviços
        if 'link_relatorio_pdf' not in df.columns:
            df['link_relatorio_pdf'] = None
        df['link_relatorio_pdf'] = df['link_relatorio_pdf'].fillna("N/A")
        
        display_columns = {
            'data_servico': 'Data do Serviço',
            'numero_identificacao': 'ID do Equipamento',
            'numero_selo_inmetro': 'Selo INMETRO',
            'tipo_servico': 'Tipo de Serviço',
            'tipo_agente': 'Agente Extintor',
            'capacidade': 'Capacidade',
            'aprovado_inspecao': 'Status',
            'plano_de_acao': 'Plano de Ação',
            'link_relatorio_pdf': 'Relatório (PDF)'
        }

    cols_to_display = [col for col in display_columns.keys() if col in df.columns]
    return df[cols_to_display].rename(columns=display_columns)


def show_history_page():
    st.title("Histórico e Logs do Sistema")
    st.info("Consulte o histórico de registros e ações para todos os equipamentos do sistema.")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    tab_registros, tab_logs = st.tabs(["📜 Histórico de Registros", "📖 Logs de Ações Corretivas"])

    # --- ABA 1: HISTÓRICO DE REGISTROS ---
    with tab_registros:
        st.header("Histórico de Registros por Tipo de Equipamento")
        
        # Cria sub-abas para cada tipo de equipamento
        subtab_ext, subtab_mang, subtab_abrigo_cad, subtab_abrigo_insp, subtab_scba_teste, subtab_scba_insp = st.tabs([
            "🔥 Extintores", "💧 Mangueiras", "🧯 Cadastro de Abrigos",
            "📋 Inspeções de Abrigos", "💨 Testes de SCBA", "🩺 Inspeções de SCBA"
        ])

        with subtab_ext:
            df = load_sheet_data(EXTINGUISHER_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)

        with subtab_mang:
            df = load_sheet_data(HOSE_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        with subtab_abrigo_cad:
            df = load_sheet_data(SHELTER_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)

        with subtab_abrigo_insp:
            df = load_sheet_data(INSPECTIONS_SHELTER_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)

        with subtab_scba_teste:
            df = load_sheet_data(SCBA_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)

        with subtab_scba_insp:
            df = load_sheet_data(SCBA_VISUAL_INSPECTIONS_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_logs:
        st.header("Logs de Ações Corretivas")
        
        subtab_log_ext, subtab_log_abrigo, subtab_log_scba = st.tabs([
            "🔥 Extintores", "🧯 Abrigos", "💨 C. Autônomo"
        ])

        with subtab_log_ext:
            df = load_sheet_data(LOG_ACTIONS)
            st.dataframe(df, use_container_width=True, hide_index=True)

        with subtab_log_abrigo:
            df = load_sheet_data(LOG_SHELTER_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        with subtab_log_scba:
            df = load_sheet_data(LOG_SCBA_SHEET_NAME)
            st.dataframe(df, use_container_width=True, hide_index=True)


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
