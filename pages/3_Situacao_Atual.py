import streamlit as st
import pandas as pd
from datetime import date
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def determine_current_status(row):
    """
    Analisa a linha de dados de um extintor e determina seu status atual e prazo.
    Retorna uma tupla: (Status, Prazo, Cor)
    """
    today = date.today()
    status = "OK"
    prazo = "N/A"
    color = "green"

    prox_inspecao = pd.to_datetime(row.get('data_proxima_inspecao'), errors='coerce')
    prox_manut_2 = pd.to_datetime(row.get('data_proxima_manutencao_2_nivel'), errors='coerce')
    prox_manut_3 = pd.to_datetime(row.get('data_proxima_manutencao_3_nivel'), errors='coerce')

    if pd.notna(prox_inspecao) and prox_inspecao.date() < today:
        status = "VENCIDO (Inspeção)"
        prazo = prox_inspecao.strftime('%d/%m/%Y')
        color = "red"
    elif pd.notna(prox_manut_2) and prox_manut_2.date() < today:
        status = "VENCIDO (Manut. Nível 2)"
        prazo = prox_manut_2.strftime('%d/%m/%Y')
        color = "red"
    elif pd.notna(prox_manut_3) and prox_manut_3.date() < today:
        status = "VENCIDO (Manut. Nível 3)"
        prazo = prox_manut_3.strftime('%d/%m/%Y')
        color = "red"
    elif row.get('aprovado_inspecao') == 'Não':
        status = "NÃO CONFORME (Aguardando Ação)"
        if pd.notna(prox_inspecao): prazo = prox_inspecao.strftime('%d/%m/%Y')
        elif pd.notna(prox_manut_2): prazo = prox_manut_2.strftime('%d/%m/%Y')
        elif pd.notna(prox_manut_3): prazo = prox_manut_3.strftime('%d/%m/%Y')
        color = "orange"
    else:
        if pd.notna(prox_inspecao): prazo = prox_inspecao.strftime('%d/%m/%Y')
        elif pd.notna(prox_manut_2): prazo = prox_manut_2.strftime('%d/%m/%Y')
        elif pd.notna(prox_manut_3): prazo = prox_manut_3.strftime('%d/%m/%Y')

    return status, prazo, color

def style_status_column(val, color):
    """Aplica cor à célula de status."""
    return f'background-color: {color}; color: white; border-radius: 5px; padding: 5px;'

def show_dashboard_page():
    st.title("Situação Atual dos Equipamentos de Emergência")

    # --- ESTRUTURA DE ABAS ---
    tab_extinguishers, tab_hoses = st.tabs(["🔥 Extintores", "💧 Mangueiras (em breve)"])

    # --- Aba de Extintores ---
    with tab_extinguishers:
        st.header("Dashboard de Extintores")
        st.info("Este dashboard mostra o status mais recente de cada extintor, considerando os prazos de vencimento.")

        df_full = load_sheet_data("extintores")

        if df_full.empty:
            st.warning("Ainda não há registros de inspeção para exibir.")
        else:
            # Processamento para encontrar o registro mais recente de cada extintor
            df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
            df_full.dropna(subset=['data_servico'], inplace=True)
            latest_records_df = df_full.sort_values('data_servico').drop_duplicates(subset='numero_identificacao', keep='last')

            # Aplica a função para determinar o status e o prazo
            status_data = latest_records_df.apply(determine_current_status, axis=1, result_type='expand')
            latest_records_df[['status_atual', 'proximo_vencimento', 'cor']] = status_data

            # Resumo no topo
            status_counts = latest_records_df['status_atual'].value_counts()
            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Total de Extintores", len(latest_records_df))
            col2.metric("🟢 OK", status_counts.get("OK", 0))
            col3.metric("🔴 VENCIDO / NÃO CONFORME", 
                        status_counts.get("VENCIDO (Inspeção)", 0) + 
                        status_counts.get("VENCIDO (Manut. Nível 2)", 0) + 
                        status_counts.get("VENCIDO (Manut. Nível 3)", 0) + 
                        status_counts.get("NÃO CONFORME (Aguardando Ação)", 0))
            st.markdown("---")

            # Filtros
            st.subheader("Filtrar Extintores")
            status_filter = st.multiselect(
                "Filtrar por Status:",
                options=latest_records_df['status_atual'].unique(),
                default=latest_records_df['status_atual'].unique()
            )

            filtered_df = latest_records_df[latest_records_df['status_atual'].isin(status_filter)]
            
            # Tabela final
            display_df = filtered_df[[
                'numero_identificacao', 'tipo_agente', 'status_atual', 
                'proximo_vencimento', 'plano_de_acao', 'cor'
            ]].rename(columns={
                'numero_identificacao': 'ID do Extintor', 'tipo_agente': 'Tipo de Agente',
                'status_atual': 'Status Atual', 'proximo_vencimento': 'Próximo Vencimento',
                'plano_de_acao': 'Plano de Ação'
            })

            def apply_row_styling(row):
                color = row['cor']
                return [style_status_column(row['Status Atual'], color) if col == 'Status Atual' else '' for col in row.index]

            st.dataframe(
                display_df.drop(columns=['cor']).style.apply(apply_row_styling, axis=1),
                use_container_width=True
            )

    # --- Aba de Mangueiras (Placeholder) ---
    with tab_hoses:
        st.header("Dashboard de Mangueiras de Incêndio")
        st.info("Funcionalidade em desenvolvimento.")
        st.image("https://via.placeholder.com/800x400.png?text=Em+Breve:+Dashboard+de+Mangueiras", 
                 caption="Aqui você poderá visualizar o status de todas as mangueiras de incêndio.")


# --- Boilerplate de Autenticação ---
if not show_login_page():
    st.stop()

show_user_header()
show_logout_button()

if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_dashboard_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
