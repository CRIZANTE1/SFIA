import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os
import numpy as np
from streamlit_js_eval import streamlit_js_eval

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data, find_last_record
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 
from operations.corrective_actions import save_corrective_action
from operations.photo_operations import upload_evidence_photo


set_page_config()

def get_consolidated_status_df(df_full):
    if df_full.empty: return pd.DataFrame()
    consolidated_data = []
    df_copy = df_full.copy()
    df_copy['data_servico'] = pd.to_datetime(df_copy['data_servico'], errors='coerce')
    df_copy = df_copy.dropna(subset=['data_servico'])
    unique_ids = df_copy['numero_identificacao'].unique()

    for ext_id in unique_ids:
        ext_df = df_copy[df_copy['numero_identificacao'] == ext_id].sort_values(by='data_servico')
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
        
        today_ts = pd.Timestamp(date.today())
        status_atual, cor = "OK", "green"
        if proximo_vencimento_real < today_ts: status_atual = "VENCIDO"; cor = "red"
        elif latest_record.get('aprovado_inspecao') == 'Não': status_atual = "NÃO CONFORME (Aguardando Ação)"; cor = "orange"

        status_instalacao = "✅ Instalado" if pd.notna(latest_record.get('latitude')) and pd.notna(latest_record.get('longitude')) else "⚠️ Não Instalado"
        
        consolidated_data.append({
            'numero_identificacao': ext_id, 'numero_selo_inmetro': latest_record.get('numero_selo_inmetro'),
            'tipo_agente': latest_record.get('tipo_agente'), 'status_atual': status_atual,
            'proximo_vencimento_geral': proximo_vencimento_real.strftime('%d/%m/%Y'),
            'prox_venc_inspecao': next_insp.strftime('%d/%m/%Y') if pd.notna(next_insp) else "N/A",
            'prox_venc_maint2': next_maint2.strftime('%d/%m/%Y') if pd.notna(next_maint2) else "N/A",
            'prox_venc_maint3': next_maint3.strftime('%d/%m/%Y') if pd.notna(next_maint3) else "N/A",
            'plano_de_acao': latest_record.get('plano_de_acao'), 'cor': cor,
            'status_instalacao': status_instalacao
        })
    return pd.DataFrame(consolidated_data)
    
@st.dialog("Registrar Ação Corretiva")
def action_form(item, df_full_history, location):
    st.write(f"**Equipamento ID:** `{item['numero_identificacao']}`")
    st.write(f"**Problema Identificado:** `{item['plano_de_acao']}`")
    
    acao_realizada = st.text_area("Descreva a ação corretiva realizada:")
    responsavel_acao = st.text_input("Responsável pela ação:", value=get_user_display_name())
    
    st.markdown("---")
    id_substituto = st.text_input("ID do Equipamento Substituto (Opcional)")

    st.markdown("---")
    st.write("Opcional: Anexe uma foto como evidência da ação concluída.")
    photo_evidence = None
    if st.toggle("📷 Anexar foto de evidência da correção"):
        photo_tab1, photo_tab2 = st.tabs(["Tirar Foto Agora", "Enviar da Galeria"])
        with photo_tab1:
            camera_photo = st.camera_input("Câmera", label_visibility="collapsed", key=f"ac_camera_{item['numero_identificacao']}")
            if camera_photo:
                photo_evidence = camera_photo
        with photo_tab2:
            gallery_photo = st.file_uploader("Galeria", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key=f"ac_uploader_{item['numero_identificacao']}")
            if gallery_photo:
                photo_evidence = gallery_photo

    if st.button("Salvar Ação", type="primary"):
        # Toda a lógica de salvamento agora está dentro deste bloco
        if not acao_realizada:
            st.error("Por favor, descreva a ação realizada.")
            return

        # Validação de localização para substituição
        original_record = find_last_record(df_full_history, item['numero_identificacao'], 'numero_identificacao')
        if id_substituto and not original_record.get('latitude'):
            st.error("Erro: O equipamento original não tem localização registrada, portanto a substituição não pode ser georreferenciada.")
            return
            
        with st.spinner("Processando ação..."):
            photo_link_evidence = upload_evidence_photo(
                photo_evidence, 
                item['numero_identificacao'],
                "acao_corretiva"
            )

            substitute_last_record = {}
            if id_substituto:
                substitute_last_record = find_last_record(df_full_history, id_substituto, 'numero_identificacao') or {}
                if not substitute_last_record:
                    st.info(f"Aviso: Equipamento substituto com ID '{id_substituto}' não tem histórico. Será criado um novo registro.")

            action_details = {
                'acao_realizada': acao_realizada,
                'responsavel_acao': responsavel_acao,
                'id_substituto': id_substituto if id_substituto else None,
                'location': location, # Passa a localização do inspetor (pode ser usada se a do original falhar)
                'photo_link': photo_link_evidence
            }
            
            if save_corrective_action(original_record, substitute_last_record, action_details, get_user_display_name()):
                st.success("Ação corretiva registrada com sucesso!")
                st.rerun()
            else:
                st.error("Falha ao registrar a ação.")

def show_dashboard_page():
    st.title("Situação Atual dos Equipamentos de Emergência")
    tab_extinguishers, tab_hoses = st.tabs(["🔥 Extintores", "💧 Mangueiras (em breve)"])

    # Captura a geolocalização uma vez
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
        if df_full_history.empty:
            st.warning("Ainda não há registros para exibir."); return

        with st.spinner("Analisando o status de todos os extintores..."):
            dashboard_df = get_consolidated_status_df(df_full_history)
        if dashboard_df.empty:
            st.warning("Não foi possível gerar o dashboard."); return

        status_counts = dashboard_df['status_atual'].value_counts()
        col1, col2, col3, col4 = st.columns(4); col1.metric("✅ Total", len(dashboard_df)); col2.metric("🟢 OK", status_counts.get("OK", 0)); col3.metric("🔴 VENCIDO", status_counts.get("VENCIDO", 0)); col4.metric("🟠 NÃO CONFORME", status_counts.get("NÃO CONFORME (Aguardando Ação)", 0)); st.markdown("---")
        
        status_filter = st.multiselect("Filtrar por Status:", options=sorted(dashboard_df['status_atual'].unique()), default=sorted(dashboard_df['status_atual'].unique()))
        filtered_df = dashboard_df[dashboard_df['status_atual'].isin(status_filter)]
        
        st.subheader("Lista de Equipamentos")
        
        if filtered_df.empty:
            st.info("Nenhum item corresponde ao filtro selecionado.")
        else:
            for index, row in filtered_df.iterrows():
                status_icon = "🟢" if row['status_atual'] == 'OK' else ('🔴' if row['status_atual'] == 'VENCIDO' else '🟠')
                
                expander_title = f"{status_icon} **ID:** {row['numero_identificacao']} | **Tipo:** {row['tipo_agente']} | **Status:** {row['status_atual']} | **Localização:** {row['status_instalacao']}"
                
                with st.expander(expander_title):
                    st.markdown(f"**Plano de Ação Sugerido:** {row['plano_de_acao']}")
                    st.markdown("---")
                    st.subheader("Próximos Vencimentos:")
                    
                    col_venc1, col_venc2, col_venc3 = st.columns(3)
                    col_venc1.metric("Inspeção Mensal", value=row['prox_venc_inspecao'])
                    col_venc2.metric("Manutenção Nível 2", value=row['prox_venc_maint2'])
                    col_venc3.metric("Manutenção Nível 3", value=row['prox_venc_maint3'])

                    st.caption(f"Último Selo INMETRO registrado: {row['numero_selo_inmetro']}")
                    
                    if row['status_atual'] != 'OK':
                        st.markdown("---")
                        if st.button("✍️ Registrar Ação Corretiva", key=f"action_{row['numero_identificacao']}", use_container_width=True):
                            action_form(row.to_dict(), df_full_history, location)

    with tab_hoses:
        st.header("Dashboard de Mangueiras de Incêndio")
        st.info("Funcionalidade em desenvolvimento.")

# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_dashboard_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
