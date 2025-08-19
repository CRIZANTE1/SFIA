import streamlit as st
import pandas as pd
import sys
import os
from config.page_config import set_page_config 

set_page_config()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin, can_edit, can_view, get_user_display_name 
from operations.demo_page import show_demo_page
from gdrive.config import (
    EXTINGUISHER_SHEET_NAME, HOSE_SHEET_NAME, SHELTER_SHEET_NAME,
    INSPECTIONS_SHELTER_SHEET_NAME, SCBA_SHEET_NAME, SCBA_VISUAL_INSPECTIONS_SHEET_NAME,
    LOG_ACTIONS, LOG_SHELTER_SHEET_NAME, LOG_SCBA_SHEET_NAME
)

def format_dataframe_for_display(df, sheet_name):
    """
    Prepara o DataFrame para exibição, renomeando colunas e selecionando as mais importantes.
    """
    if df.empty:
        return df
    
    df = df.copy()

    ALL_COLUMNS = {
        # Comuns
        'data_inspecao': 'Data Inspeção', 'status_geral': 'Status', 'inspetor': 'Inspetor', 'data_proxima_inspecao': 'Próx. Inspeção',
        'data_servico': 'Data Serviço', 'numero_identificacao': 'ID Equip.', 'tipo_servico': 'Tipo Serviço', 'aprovado_inspecao': 'Status',
        'plano_de_acao': 'Plano de Ação', 'link_relatorio_pdf': 'Relatório (PDF)', 'id_mangueira': 'ID Mangueira', 'data_proximo_teste': 'Próx. Teste',
        'link_certificado_pdf': 'Certificado (PDF)', 'data_teste': 'Data Teste', 'numero_serie_equipamento': 'S/N Equip.', 'resultado_final': 'Resultado',
        'id_abrigo': 'ID Abrigo', 'cliente': 'Cliente', 'local': 'Local', 'itens_json': 'Inventário (JSON)',
        # Logs
        'data_acao': 'Data Ação', 'problema_original': 'Problema', 'acao_realizada': 'Ação Realizada', 'responsavel': 'Responsável'
    }

    SHEET_VIEW_COLUMNS = {
        EXTINGUISHER_SHEET_NAME: ['data_servico', 'numero_identificacao', 'tipo_servico', 'aprovado_inspecao', 'plano_de_acao', 'link_relatorio_pdf'],
        HOSE_SHEET_NAME: ['id_mangueira', 'data_inspecao', 'data_proximo_teste', 'status', 'link_certificado_pdf'],
        SHELTER_SHEET_NAME: ['id_abrigo', 'cliente', 'local', 'itens_json'], # <-- Colunas para Cadastro de Abrigos
        INSPECTIONS_SHELTER_SHEET_NAME: ['data_inspecao', 'id_abrigo', 'status_geral', 'data_proxima_inspecao'],
        SCBA_SHEET_NAME: ['numero_serie_equipamento', 'data_teste', 'resultado_final', 'data_validade', 'status_qualidade_ar', 'link_relatorio_pdf'],
        SCBA_VISUAL_INSPECTIONS_SHEET_NAME: ['data_inspecao', 'numero_serie_equipamento', 'status_geral', 'data_proxima_inspecao'],
        LOG_ACTIONS: ['data_acao', 'id_equipamento', 'problema_original', 'acao_realizada', 'responsavel_acao'],
        LOG_SHELTER_SHEET_NAME: ['data_acao', 'id_abrigo', 'problema_original', 'acao_realizada', 'responsavel'],
        LOG_SCBA_SHEET_NAME: ['data_acao', 'numero_serie_equipamento', 'problema_original', 'acao_realizada', 'responsavel']
    }

    # Pega a lista de colunas para a planilha atual
    cols_to_show = SHEET_VIEW_COLUMNS.get(sheet_name, df.columns.tolist())
    
    # Filtra o DataFrame para mostrar apenas as colunas desejadas que realmente existem
    final_cols = [col for col in cols_to_show if col in df.columns]
    
    # Renomeia as colunas para nomes amigáveis
    renamed_df = df[final_cols].rename(columns=ALL_COLUMNS)
    
    return renamed_df

def display_formatted_dataframe(sheet_name):
    """Função helper para carregar, formatar e exibir um DataFrame com links clicáveis."""
    df = load_sheet_data(sheet_name)
    
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return
    
    df_formatted = format_dataframe_for_display(df, sheet_name)

    column_config = {}
    for col_name in df_formatted.columns:
        if "PDF" in col_name or "Certificado" in col_name:
            column_config[col_name] = st.column_config.LinkColumn(
                col_name, display_text="🔗 Ver Documento"
            )

    st.dataframe(
        df_formatted,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
    
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

        with subtabs[0]: display_formatted_dataframe(LOG_ACTIONS)
        with subtabs[1]: display_formatted_dataframe(LOG_SHELTER_SHEET_NAME)
        with subtabs[2]: display_formatted_dataframe(LOG_SCBA_SHEET_NAME)

if not show_login_page(): 
    st.stop()
show_user_header()
show_logout_button()
if can_edit():
    st.sidebar.success("✅ Acesso completo")
    show_history_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
