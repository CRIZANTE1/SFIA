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

def display_formatted_dataframe(sheet_name, is_log=False):
    """Função helper para carregar, formatar e exibir um DataFrame."""
    df = load_sheet_data(sheet_name)
    
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    
    df_formatted = format_dataframe_for_display(df, is_log)
    st.dataframe(df_formatted, use_container_width=True, hide_index=True)
    
    df = df.copy()

    log_columns = {
        'data_acao': 'Data da Ação',
        'id_abrigo': 'ID do Abrigo',
        'numero_serie_equipamento': 'S/N do Equipamento',
        'problema_original': 'Problema Original',
        'acao_realizada': 'Ação Realizada',
        'responsavel': 'Responsável',
        'data_correcao': 'Data da Correção',
        'id_equipamento': 'ID do Equipamento',
        'responsavel_acao': 'Responsável',
        'id_equipamento_substituto': 'ID do Equip. Substituto',
        'link_foto_evidencia': 'Evidência (Foto)'
    }

    service_columns = {
        # Colunas comuns
        'data_inspecao': 'Data da Inspeção',
        'status_geral': 'Status Geral',
        'inspetor': 'Inspetor',
        'data_proxima_inspecao': 'Próxima Inspeção',
        # Extintores
        'data_servico': 'Data do Serviço',
        'numero_identificacao': 'ID do Equipamento',
        'tipo_servico': 'Tipo de Serviço',
        'aprovado_inspecao': 'Status',
        'plano_de_acao': 'Plano de Ação',
        'link_relatorio_pdf': 'Relatório (PDF)',
        # Mangueiras
        'id_mangueira': 'ID da Mangueira',
        'data_proximo_teste': 'Próximo Teste',
        'link_certificado_pdf': 'Certificado (PDF)',
        # SCBA
        'data_teste': 'Data do Teste',
        'numero_serie_equipamento': 'S/N do Equipamento',
        'resultado_final': 'Resultado Final'
    }

    if is_log:
        display_columns = log_columns
    else:
        display_columns = service_columns

    cols_to_display = [col for col in display_columns.keys() if col in df.columns]
    return df[cols_to_display].rename(columns=display_columns)

def display_formatted_dataframe(sheet_name, is_log=False):
    """Função helper para carregar, converter, formatar e exibir um DataFrame."""
    data_raw = load_sheet_data(sheet_name)
    if not data_raw or len(data_raw) < 2:
        st.info("Nenhum registro encontrado.")
        return
    
    df = pd.DataFrame(data_raw[1:], columns=data_raw[0])
    df_formatted = format_dataframe_for_display(df, is_log)
    st.dataframe(df_formatted, use_container_width=True, hide_index=True)

def show_history_page():
    st.title("Histórico e Logs do Sistema")
    st.info("Consulte o histórico de registros e ações para todos os equipamentos do sistema.")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    tab_registros, tab_logs = st.tabs(["📜 Histórico de Registros", "📖 Logs de Ações Corretivas"])

    with tab_registros:
        st.header("Histórico de Registros por Tipo de Equipamento")
        subtabs = st.tabs([
            "🔥 Extintores", "💧 Mangueiras", "🧯 Cadastro de Abrigos",
            "📋 Inspeções de Abrigos", "💨 Testes de SCBA", "🩺 Inspeções de SCBA"
        ])

        with subtabs[0]: display_formatted_dataframe(EXTINGUISHER_SHEET_NAME)
        with subtabs[1]: display_formatted_dataframe(HOSE_SHEET_NAME)
        with subtabs[2]: display_formatted_dataframe(SHELTER_SHEET_NAME)
        with subtabs[3]: display_formatted_dataframe(INSPECTIONS_SHELTER_SHEET_NAME)
        with subtabs[4]: display_formatted_dataframe(SCBA_SHEET_NAME)
        with subtabs[5]: display_formatted_dataframe(SCBA_VISUAL_INSPECTIONS_SHEET_NAME)

    with tab_logs:
        st.header("Logs de Ações Corretivas")
        subtabs = st.tabs(["🔥 Extintores", "🧯 Abrigos", "💨 C. Autônomo"])

        with subtabs[0]: display_formatted_dataframe(LOG_ACTIONS, is_log=True)
        with subtabs[1]: display_formatted_dataframe(LOG_SHELTER_SHEET_NAME, is_log=True)
        with subtabs[2]: display_formatted_dataframe(LOG_SCBA_SHEET_NAME, is_log=True)

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
