import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def get_consolidated_status_df(df_full):
    if df_full.empty: return pd.DataFrame()
    consolidated_data = []
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce').dt.date
    df_full.dropna(subset=['data_servico'], inplace=True)
    unique_selos = df_full['numero_selo_inmetro'].unique()

    for selo_id in unique_selos:
        ext_df = df_full[df_full['numero_selo_inmetro'] == selo_id].sort_values(by='data_servico')
        if ext_df.empty: continue
        
        latest_record = ext_df.iloc[-1]
        
        last_insp_date = ext_df[ext_df['tipo_servico'] == 'Inspeção']['data_servico'].max()
        last_maint2_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 2']['data_servico'].max()
        last_maint3_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 3']['data_servico'].max()
        
        next_insp = (last_insp_date + relativedelta(months=1)) if pd.notna(last_insp_date) else pd.NaT
        next_maint2 = (last_maint2_date + relativedelta(months=12)) if pd.notna(last_maint2_date) else pd.NaT
        next_maint3 = (last_maint3_date + relativedelta(years=5)) if pd.notna(last_maint3_date) else pd.NaT
        
        vencimentos = [d for d in [next_insp, next_maint2, next_maint3] if pd.notna(d)]
        if not vencimentos: continue
        
        proximo_vencimento_real = min(vencimentos)
        
        today = date.today()
        status_atual, cor = "OK", "green"

        if proximo_vencimento_real < pd.Timestamp(today):
            status_atual = "VENCIDO"
            cor = "red"
        elif latest_record.get('aprovado_inspecao') == 'Não':
            status_atual = "NÃO CONFORME (Aguardando Ação)"
            cor = "orange"
        
        consolidated_data.append({
            'numero_selo_inmetro': selo_id,
            'numero_identificacao': latest_record.get('numero_identificacao'),
            'tipo_agente': latest_record.get('tipo_agente'),
            'status_atual': status_atual,
            'proximo_vencimento': proximo_vencimento_real.strftime('%d/%m/%Y'),
            'plano_de_acao': latest_record.get('plano_de_acao'),
            'cor': cor
        })
    return pd.DataFrame(consolidated_data)

def style_status_cell(val, color):
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
        
        color_map = pd.Series(filtered_df.cor.values, index=filtered_df.status_atual).to_dict()
        
        display_df = filtered_df.rename(columns={
            'numero_selo_inmetro': 'Selo INMETRO', 'numero_identificacao': 'ID do Cilindro', 'tipo_agente': 'Tipo',
            'status_atual': 'Status', 'proximo_vencimento': 'Próximo Vencimento',
            'plano_de_acao': 'Plano de Ação Sugerido'
        })
        
        styler = display_df.style.applymap(
            lambda val: style_status_cell(val, color_map.get(val, 'grey')),
            subset=['Status']
        )
        
        st.dataframe(
            styler.hide(subset=['cor'], axis=1),
            use_container_width=True,
            hide_index=True
        )

    with tab_hoses:
        st.header("Dashboard de Mangueiras de Incêndio")
        st.info("Funcionalidade em desenvolvimento.")



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
