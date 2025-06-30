# pages/3_Situacao_Atual.py

import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def get_consolidated_status_df(df_full):
    """
    Processa o histórico completo e retorna um DataFrame com o status real e consolidado
    de cada extintor, considerando todos os seus ciclos de vida.
    """
    if df_full.empty:
        return pd.DataFrame()

    consolidated_data = []
    
    # Converte colunas de data uma vez para melhor performance
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full.dropna(subset=['data_servico'], inplace=True)

    unique_ids = df_full['numero_identificacao'].unique()

    for ext_id in unique_ids:
        # Filtra todos os registros para o extintor atual
        ext_df = df_full[df_full['numero_identificacao'] == ext_id].sort_values(by='data_servico')

        # Encontra a data do último serviço para cada tipo
        last_insp_date = ext_df[ext_df['tipo_servico'] == 'Inspeção']['data_servico'].max()
        last_maint2_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 2']['data_servico'].max()
        last_maint3_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 3']['data_servico'].max()

        # Calcula os próximos vencimentos com base nas últimas datas
        next_insp = (last_insp_date + relativedelta(months=1)) if pd.notna(last_insp_date) else pd.NaT
        next_maint2 = (last_maint2_date + relativedelta(months=12)) if pd.notna(last_maint2_date) else pd.NaT
        next_maint3 = (last_maint3_date + relativedelta(years=5)) if pd.notna(last_maint3_date) else pd.NaT

        # Coleta todas as datas de vencimento futuras válidas
        vencimentos = [d for d in [next_insp, next_maint2, next_maint3] if pd.notna(d)]

        if not vencimentos:
            continue # Pula se não houver nenhuma data de vencimento

        # O próximo vencimento real é o mais próximo no tempo
        proximo_vencimento_real = min(vencimentos)
        
        # Pega os dados do registro mais recente para informações gerais
        latest_record = ext_df.iloc[-1]
        
        # Determina o status final
        today = pd.to_datetime(date.today())
        status_atual = "OK"
        cor = "green"

        if proximo_vencimento_real < today:
            status_atual = "VENCIDO"
            cor = "red"
        elif latest_record.get('aprovado_inspecao') == 'Não':
            status_atual = "NÃO CONFORME (Aguardando Ação)"
            cor = "orange"
        
        consolidated_data.append({
            'numero_identificacao': ext_id,
            'tipo_agente': latest_record.get('tipo_agente'),
            'status_atual': status_atual,
            'proximo_vencimento': proximo_vencimento_real.strftime('%d/%m/%Y'),
            'plano_de_acao': latest_record.get('plano_de_acao'),
            'cor': cor
        })

    return pd.DataFrame(consolidated_data)


def style_status_cell(val, color):
    """Aplica cor à célula de status."""
    return f'background-color: {color}; color: white; border-radius: 5px; padding: 5px; text-align: center;'

def show_dashboard_page():
    st.title("Situação Atual dos Equipamentos de Emergência")

    tab_extinguishers, tab_hoses = st.tabs(["🔥 Extintores", "💧 Mangueiras (em breve)"])

    with tab_extinguishers:
        st.header("Dashboard de Extintores")
        st.info("Este dashboard analisa todo o histórico para mostrar o status real e o vencimento mais próximo de cada extintor.")

        df_full_history = load_sheet_data("extintores")
        
        if df_full_history.empty:
            st.warning("Ainda não há registros de inspeção para exibir.")
            return

        with st.spinner("Analisando o status de todos os extintores..."):
            dashboard_df = get_consolidated_status_df(df_full_history)

        if dashboard_df.empty:
            st.warning("Não foi possível gerar o dashboard. Verifique se os dados na planilha estão corretos.")
            return

        status_counts = dashboard_df['status_atual'].value_counts()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Total de Extintores", len(dashboard_df))
        col2.metric("🟢 OK", status_counts.get("OK", 0))
        col3.metric("🔴 VENCIDO", status_counts.get("VENCIDO", 0))
        col4.metric("🟠 NÃO CONFORME", status_counts.get("NÃO CONFORME (Aguardando Ação)", 0))
        st.markdown("---")

        st.subheader("Filtrar Extintores")
        status_filter = st.multiselect(
            "Filtrar por Status:",
            options=dashboard_df['status_atual'].unique(),
            default=dashboard_df['status_atual'].unique()
        )

        filtered_df = dashboard_df[dashboard_df['status_atual'].isin(status_filter)]
        
        # Renomeia colunas para exibição final
        display_df = filtered_df.rename(columns={
            'numero_identificacao': 'ID do Extintor', 'tipo_agente': 'Tipo',
            'status_atual': 'Status', 'proximo_vencimento': 'Próximo Vencimento',
            'plano_de_acao': 'Plano de Ação Sugerido'
        })
        
        # Aplica estilização baseada na coluna 'cor'
        styler = display_df.style.apply(
            lambda row: [style_status_cell(row['Status'], row['cor']) if col == 'Status' else '' for col in row.index],
            axis=1,
            subset=['Status']
        ).hide(subset=['cor'], axis=1)

        st.dataframe(styler, use_container_width=True, hide_index=True)

    with tab_hoses:
        st.header("Dashboard de Mangueiras de Incêndio")
        st.info("Funcionalidade em desenvolvimento.")


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
