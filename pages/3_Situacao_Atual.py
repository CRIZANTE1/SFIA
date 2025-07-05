import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os
import numpy as np
from streamlit_js_eval import streamlit_js_eval

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data, find_last_record
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 
from operations.corrective_actions import save_corrective_action
from operations.photo_operations import upload_evidence_photo

set_page_config()

# ==============================================================================
# FUNÇÃO CORRIGIDA (Versão 3 - Definitiva)
# Esta versão unifica a lógica para garantir que todas as datas sejam calculadas corretamente.
# ==============================================================================
def get_consolidated_status_df(df_full, df_locais):
    if df_full.empty: 
        return pd.DataFrame()

    df_full = df_full.copy()
    
    # 1. Preparação dos Dados: Converter datas e garantir tipos
    df_full['data_servico'] = pd.to_datetime(df_full['data_servico'], errors='coerce')
    df_full['numero_identificacao'] = df_full['numero_identificacao'].astype(str)
    df_full.dropna(subset=['data_servico', 'numero_identificacao'], inplace=True)
    
    # 2. Obter a última linha de cada equipamento para informações de status (como plano de ação, aprovação, etc.)
    # Isso é feito separadamente para não perdermos as datas históricas de manutenções importantes.
    last_records_df = df_full.sort_values('data_servico').drop_duplicates('numero_identificacao', keep='last')

    # 3. Calcular as datas de serviço mais recentes para CADA NÍVEL, usando o histórico completo
    # Usamos groupby.agg para fazer isso de forma eficiente para todos os equipamentos de uma vez.
    agg_funcs = {
        # Para a inspeção, CADA serviço conta. Portanto, pegamos a data máxima geral.
        'last_insp_date': ('data_servico', 'max'),
        # Para Nível 2 e 3, filtramos e pegamos a data máxima específica de cada tipo.
        'last_maint2_date': ('data_servico', lambda x: x[df_full.loc[x.index, 'tipo_servico'] == 'Manutenção Nível 2'].max()),
        'last_maint3_date': ('data_servico', lambda x: x[df_full.loc[x.index, 'tipo_servico'] == 'Manutenção Nível 3'].max())
    }
    date_summary_df = df_full.groupby('numero_identificacao').agg(**agg_funcs).reset_index()

    # 4. Juntar as informações de status (de last_records_df) com as datas calculadas (de date_summary_df)
    dashboard_df = pd.merge(last_records_df, date_summary_df, on='numero_identificacao')

    # 5. Calcular as PRÓXIMAS datas de vencimento com base nas datas históricas encontradas
    dashboard_df['prox_venc_inspecao'] = dashboard_df['last_insp_date'].apply(lambda d: d + relativedelta(months=1) if pd.notna(d) else pd.NaT)
    dashboard_df['prox_venc_maint2'] = dashboard_df['last_maint2_date'].apply(lambda d: d + relativedelta(months=12) if pd.notna(d) else pd.NaT)
    dashboard_df['prox_venc_maint3'] = dashboard_df['last_maint3_date'].apply(lambda d: d + relativedelta(years=5) if pd.notna(d) else pd.NaT)

    # 6. Determinar o vencimento geral (o mais próximo de hoje) e o status atual
    date_cols_for_min = ['prox_venc_inspecao', 'prox_venc_maint2', 'prox_venc_maint3']
    dashboard_df['proximo_vencimento_geral'] = dashboard_df[date_cols_for_min].min(axis=1, skipna=True)
    
    today = pd.Timestamp(date.today())
    def get_status(row):
        if row.get('plano_de_acao') == "FORA DE OPERAÇÃO (SUBSTITUÍDO)":
            return "FORA DE OPERAÇÃO"
        if pd.notna(row['proximo_vencimento_geral']) and row['proximo_vencimento_geral'] < today:
            return "VENCIDO"
        if row.get('aprovado_inspecao') == 'Não':
            return "NÃO CONFORME (Aguardando Ação)"
        return "OK"
    
    dashboard_df['status_atual'] = dashboard_df.apply(get_status, axis=1)

    # 7. Filtrar equipamentos inativos
    dashboard_df = dashboard_df[dashboard_df['status_atual'] != 'FORA DE OPERAÇÃO'].copy()
    
    # 8. Formatar as colunas de data para exibição
    for col in ['prox_venc_inspecao', 'prox_venc_maint2', 'prox_venc_maint3', 'proximo_vencimento_geral']:
        if col in dashboard_df:
            dashboard_df[col] = pd.to_datetime(dashboard_df[col], errors='coerce').dt.strftime('%d/%m/%Y')
            dashboard_df[col] = dashboard_df[col].fillna("N/A")

    # 9. Juntar com as informações de localização da aba 'locais'
    if not df_locais.empty and 'numero_identificacao' in dashboard_df.columns:
        if 'id' in df_locais.columns:
            df_locais = df_locais.rename(columns={'id': 'numero_identificacao'})
        if 'numero_identificacao' in df_locais.columns and 'local' in df_locais.columns:
            df_locais['numero_identificacao'] = df_locais['numero_identificacao'].astype(str)
            dashboard_df = pd.merge(dashboard_df, df_locais[['numero_identificacao', 'local']].drop_duplicates(subset=['numero_identificacao']), on='numero_identificacao', how='left')
            dashboard_df['status_instalacao'] = dashboard_df['local'].apply(lambda x: f"✅ {x}" if pd.notna(x) and str(x).strip() else "⚠️ Local não definido")
        else:
            dashboard_df['status_instalacao'] = "⚠️ Aba 'locais' mal formatada"
    else:
        dashboard_df['status_instalacao'] = "⚠️ Local não definido"
        
    return dashboard_df
# ==============================================================================


@st.dialog("Registrar Ação Corretiva")
def action_form(item, df_full_history, location):
    # Esta função não precisa de alterações
    st.write(f"**Equipamento ID:** `{item['numero_identificacao']}`")
    st.write(f"**Problema Identificado:** `{item['plano_de_acao']}`")
    
    acao_realizada = st.text_area("Descreva a ação corretiva realizada:")
    responsavel_acao = st.text_input("Responsável pela ação:", value=get_user_display_name())
    
    st.markdown("---")
    id_substituto = st.text_input("ID do Equipamento Substituto (Opcional)")

    st.markdown("---")
    st.write("Opcional: Anexe uma foto como evidência da ação concluída.")
    photo_evidence = None
    if st.toggle("📷 Anexar foto de evidência da correção", key=f"toggle_photo_{item['numero_identificacao']}"):
        st.write("**Opção 1: Tirar Foto Agora (Qualidade Menor)**")
        camera_photo = st.camera_input("Câmera", label_visibility="collapsed", key=f"ac_camera_{item['numero_identificacao']}")
        st.markdown("---")
        st.write("**Opção 2: Enviar da Galeria (Qualidade Alta)**")
        gallery_photo = st.file_uploader("Galeria", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key=f"ac_uploader_{item['numero_identificacao']}")
        photo_evidence = gallery_photo or camera_photo
       
    if st.button("Salvar Ação", type="primary"):
        if not acao_realizada:
            st.error("Por favor, descreva a ação realizada.")
            return

        original_record = find_last_record(df_full_history, item['numero_identificacao'], 'numero_identificacao')
        if not original_record:
            st.error(f"Erro crítico: não foi possível encontrar o último registro do ID {item['numero_identificacao']} para salvar a ação.")
            return
            
        with st.spinner("Processando ação..."):
            photo_link_evidence = upload_evidence_photo(photo_evidence, item['numero_identificacao'], "acao_corretiva")
            substitute_last_record = {}
            if id_substituto:
                substitute_last_record = find_last_record(df_full_history, id_substituto, 'numero_identificacao') or {}
                if not substitute_last_record:
                    st.info(f"Aviso: Equipamento substituto com ID '{id_substituto}' não tem histórico. Será criado um novo registro.")

            action_details = {
                'acao_realizada': acao_realizada,
                'responsavel_acao': responsavel_acao,
                'id_substituto': id_substituto or None,
                'location': location,
                'photo_link': photo_link_evidence
            }
            
            if save_corrective_action(original_record, substitute_last_record, action_details, get_user_display_name()):
                st.success("Ação corretiva registrada com sucesso!")
                st.cache_data.clear() 
                st.rerun()
            else:
                st.error("Falha ao registrar a ação.")

def show_dashboard_page():
    # Esta função não precisa de alterações
    st.title("Situação Atual dos Equipamentos de Emergência")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    tab_extinguishers, tab_hoses = st.tabs(["🔥 Extintores", "💧 Mangueiras (em breve)"])

    location = streamlit_js_eval(js_expressions="""
        new Promise(function(resolve, reject) {
            navigator.geolocation.getCurrentPosition(
                function(position) { resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }); },
                function(error) { resolve(null); }
            );
        });
    """)

    with tab_extinguishers:
        st.header("Dashboard de Extintores")
        
        df_full_history = load_sheet_data("extintores")
        try:
            df_locais = load_sheet_data("locais")
        except Exception as e:
            st.warning(f"Não foi possível carregar a aba 'locais': {e}. As informações de localização não serão exibidas.")
            df_locais = pd.DataFrame() 

        if df_full_history.empty:
            st.warning("Ainda não há registros de inspeção para exibir."); return

        with st.spinner("Analisando o status de todos os extintores..."):
            dashboard_df = get_consolidated_status_df(df_full_history, df_locais)
        
        if dashboard_df.empty:
            st.warning("Não foi possível gerar o dashboard ou não há equipamentos ativos."); return

        status_counts = dashboard_df['status_atual'].value_counts()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Total Ativo", len(dashboard_df))
        col2.metric("🟢 OK", status_counts.get("OK", 0))
        col3.metric("🔴 VENCIDO", status_counts.get("VENCIDO", 0))
        col4.metric("🟠 NÃO CONFORME", status_counts.get("NÃO CONFORME (Aguardando Ação)", 0))
        st.markdown("---")
        
        status_filter = st.multiselect("Filtrar por Status:", options=sorted(dashboard_df['status_atual'].unique()), default=sorted(dashboard_df['status_atual'].unique()))
        filtered_df = dashboard_df[dashboard_df['status_atual'].isin(status_filter)]
        
        st.subheader("Lista de Equipamentos")
        
        if filtered_df.empty:
            st.info("Nenhum item corresponde ao filtro selecionado.")
        else:
            for index, row in filtered_df.iterrows():
                status_icon = "🟢" if row['status_atual'] == 'OK' else ('🔴' if row['status_atual'] == 'VENCIDO' else '🟠')
                expander_title = f"{status_icon} **ID:** {row['numero_identificacao']} | **Tipo:** {row.get('tipo_agente', 'N/A')} | **Status:** {row['status_atual']} | **Localização:** {row.get('status_instalacao', 'N/A')}"
                
                with st.expander(expander_title):
                    st.markdown(f"**Plano de Ação Sugerido:** {row.get('plano_de_acao', 'N/A')}")
                    st.markdown("---")
                    st.subheader("Próximos Vencimentos:")
                    
                    col_venc1, col_venc2, col_venc3 = st.columns(3)
                    col_venc1.metric("Inspeção Mensal", value=row['prox_venc_inspecao'])
                    col_venc2.metric("Manutenção Nível 2", value=row['prox_venc_maint2'])
                    col_venc3.metric("Manutenção Nível 3", value=row['prox_venc_maint3'])

                    st.caption(f"Último Selo INMETRO registrado: {row.get('numero_selo_inmetro', 'N/A')}")
                    
                    if row['status_atual'] != 'OK':
                        st.markdown("---")
                        if st.button("✍️ Registrar Ação Corretiva", key=f"action_{row['numero_identificacao']}", use_container_width=True):
                            action_form(row.to_dict(), df_full_history, location)

    with tab_hoses:
        st.header("Dashboard de Mangueiras de Incêndio")
        st.info("Funcionalidade em desenvolvimento.")

# --- Boilerplate de Autenticação (sem alterações) ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_dashboard_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
