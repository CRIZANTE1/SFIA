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

def format_dataframe_for_display(df, is_log=False):
    """
    Prepara o DataFrame para exibição, renomeando colunas e formatando.
    """
    if df.empty:
        return df
    
    df = df.copy()

    if is_log:
        # Formatação específica para o Log de Ações
        df['data_correcao'] = pd.to_datetime(df['data_correcao']).dt.strftime('%d/%m/%Y')
        display_columns = {
            'data_correcao': 'Data da Correção',
            'id_equipamento': 'ID do Equipamento',
            'problema_original': 'Problema Original',
            'acao_realizada': 'Ação Realizada',
            'responsavel_acao': 'Responsável',
            'id_equipamento_substituto': 'ID do Equip. Substituto' 
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
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()
    
    # Carrega os dois DataFrames
    with st.spinner("Carregando histórico completo..."):
        df_inspections = load_sheet_data("extintores")
        df_action_log = load_sheet_data("log_acoes")

    # Seção do Histórico de Serviços
    st.header("Histórico de Serviços Realizados")
    if df_inspections.empty:
        st.warning("Ainda não há registros de inspeção no histórico.")
    else:
        df_inspections['data_servico_dt'] = pd.to_datetime(df_inspections['data_servico'], errors='coerce')
        df_inspections.dropna(subset=['data_servico_dt'], inplace=True)
        
        st.subheader("Filtrar Histórico de Serviços")
        available_years = sorted(df_inspections['data_servico_dt'].dt.year.unique(), reverse=True)
        col1, col2 = st.columns(2)
        with col1:
            selected_year = st.selectbox("Filtrar por Ano:", ["Todos os Anos"] + available_years, key="year_filter")
        with col2:
            search_id = st.text_input("Buscar por ID do Equipamento:", key="id_search")

        filtered_df = df_inspections
        if selected_year != "Todos os Anos":
            filtered_df = filtered_df[filtered_df['data_servico_dt'].dt.year == selected_year]
        if search_id:
            filtered_df = filtered_df[filtered_df['numero_identificacao'].astype(str).str.contains(search_id, na=False)]

        if filtered_df.empty:
            st.warning("Nenhum registro encontrado com os filtros selecionados.")
        else:
            display_df = format_dataframe_for_display(filtered_df, is_log=False)
            st.dataframe(display_df, column_config={"Relatório (PDF)": st.column_config.LinkColumn("Relatório (PDF)", display_text="🔗 Ver")}, hide_index=True, use_container_width=True)

    st.markdown("---")

    with st.expander("📖 Ver Log de Ações Corretivas", expanded=False):
        st.header("Log de Ações Corretivas")
        if df_action_log.empty:
            st.info("Nenhuma ação corretiva foi registrada ainda.")
        else:
            log_display_df = format_dataframe_for_display(df_action_log, is_log=True)
            st.dataframe(log_display_df, hide_index=True, use_container_width=True)


# --- Boilerplate de Autenticação ---
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
