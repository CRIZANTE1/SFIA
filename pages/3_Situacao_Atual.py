import streamlit as st
import pandas as pd
from datetime import date
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from operations.extinguisher_operations import save_inspection, calculate_next_dates, generate_action_plan
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
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

        if proximo_vencimento_real < today:
            status_atual = "VENCIDO"
            cor = "red"
        elif latest_record['aprovado_inspecao'] == 'Não':
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

def show_dashboard_page():
    st.title("Situação Atual dos Equipamentos de Emergência")
    tab_extinguishers, tab_hoses = st.tabs(["🔥 Extintores", "💧 Mangueiras (em breve)"])

    with tab_extinguishers:
        st.header("Dashboard de Extintores")
        
        # Inicializa o estado do editor de dados
        if "data_editor_key" not in st.session_state:
            st.session_state["data_editor_key"] = 0

        df_full_history = load_sheet_data("extintores")
        if df_full_history.empty:
            st.warning("Ainda não há registros de inspeção para exibir.")
            return

        dashboard_df = get_consolidated_status_df(df_full_history)
        if dashboard_df.empty:
            st.warning("Não foi possível gerar o dashboard.")
            return

        # Foca nos itens que precisam de ação
        actionable_df = dashboard_df[dashboard_df['status_atual'] != 'OK'].copy()
        actionable_df['Ação Concluída'] = False # Adiciona a coluna de checkbox

        st.subheader("Painel de Ações Pendentes")
        st.info("Marque a caixa 'Ação Concluída' para os itens que foram resolvidos. Isso registrará uma nova inspeção 'Conforme' para o equipamento.")
        
        if actionable_df.empty:
            st.success("🎉 Todos os extintores estão em conformidade! Nenhuma ação pendente.")
        else:
            # Usa o data_editor para permitir a interação
            edited_df = st.data_editor(
                actionable_df,
                column_config={
                    "Ação Concluída": st.column_config.CheckboxColumn(required=True),
                    "numero_selo_inmetro": "Selo INMETRO",
                    "status_atual": "Status",
                    "plano_de_acao": "Plano de Ação",
                },
                disabled=["numero_selo_inmetro", "status_atual", "plano_de_acao", "tipo_agente", "proximo_vencimento", "numero_identificacao", "cor"],
                hide_index=True,
                use_container_width=True,
                key=f"data_editor_{st.session_state['data_editor_key']}"
            )

            # Verifica quais checkboxes foram marcados
            resolved_items = edited_df[edited_df["Ação Concluída"]]
            
            if not resolved_items.empty:
                if st.button("Confirmar Resolução dos Itens Marcados", type="primary"):
                    with st.spinner("Registrando ações corretivas..."):
                        success_count = 0
                        for index, item in resolved_items.iterrows():
                            # Busca o registro original completo para ter todos os dados
                            original_record = df_full_history[df_full_history['numero_selo_inmetro'] == item['numero_selo_inmetro']].sort_values('data_servico').iloc[-1].to_dict()
                            
                            # Cria o novo registro de inspeção "Conforme"
                            new_inspection_record = original_record.copy()
                            new_inspection_record.update({
                                'tipo_servico': "Inspeção",
                                'data_servico': date.today().isoformat(),
                                'inspetor_responsavel': get_user_display_name(),
                                'aprovado_inspecao': "Sim",
                                'observacoes_gerais': f"Ação corretiva aplicada: {item['plano_de_acao']}"
                            })
                            new_inspection_record.update(calculate_next_dates(new_inspection_record['data_servico'], 'Inspeção', new_inspection_record['tipo_agente']))
                            new_inspection_record['plano_de_acao'] = generate_action_plan(new_inspection_record)

                            if save_inspection(new_inspection_record):
                                success_count += 1
                        
                        st.success(f"{success_count} ações foram registradas com sucesso!")
                        st.info("Atualizando dashboard...")
                        # Limpa caches e incrementa a chave do editor para forçar a recarga completa
                        st.cache_data.clear()
                        st.session_state["data_editor_key"] += 1
                        st.rerun()

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
