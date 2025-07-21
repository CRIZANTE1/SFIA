import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os
import numpy as np
import json
from streamlit_js_eval import streamlit_js_eval

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data, find_last_record
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 
from gdrive.config import HOSE_SHEET_NAME, SHELTER_SHEET_NAME, INSPECTIONS_SHELTER_SHEET_NAME
from reports.reports_pdf import generate_shelters_html
from operations.shelter_operations import save_shelter_action_log, save_shelter_inspection
from operations.corrective_actions import save_corrective_action
from operations.photo_operations import upload_evidence_photo



set_page_config()


def get_hose_status_df(df_hoses):
    if df_hoses.empty:
        return pd.DataFrame()
    
    # Garante que as colunas de data existam e as converte
    for col in ['data_inspecao', 'data_proximo_teste']:
        if col not in df_hoses.columns:
            df_hoses[col] = pd.NaT # Cria a coluna vazia se não existir
        df_hoses[col] = pd.to_datetime(df_hoses[col], errors='coerce')

    # Pega o registro mais recente para cada mangueira, mantendo todas as colunas
    df_hoses = df_hoses.sort_values('data_inspecao', ascending=False).drop_duplicates(subset='id_mangueira', keep='first')
    
    # Verifica o status de vencimento
    today = pd.Timestamp(date.today())
    df_hoses['status'] = np.where(df_hoses['data_proximo_teste'] < today, "🔴 VENCIDO", "🟢 OK")
    
    # Formata as datas de volta para string para exibição limpa
    df_hoses['data_inspecao'] = df_hoses['data_inspecao'].dt.strftime('%d/%m/%Y')
    df_hoses['data_proximo_teste'] = df_hoses['data_proximo_teste'].dt.strftime('%d/%m/%Y')
    
    # Define e reordena as colunas que queremos mostrar no dashboard
    display_columns = [
        'id_mangueira', 'status', 'marca', 'diametro', 'tipo',
        'comprimento', 'ano_fabricacao', 'data_inspecao',
        'data_proximo_teste', 'link_certificado_pdf', 'registrado_por'
    ]
    
    # Filtra o dataframe para conter apenas as colunas de exibição existentes
    existing_display_columns = [col for col in display_columns if col in df_hoses.columns]
    
    return df_hoses[existing_display_columns]




def get_consolidated_status_df(df_full, df_locais):
    if df_full.empty: 
        return pd.DataFrame()
    
    consolidated_data = []
    df_copy = df_full.copy()
    df_copy['data_servico'] = pd.to_datetime(df_copy['data_servico'], errors='coerce')
    df_copy = df_copy.dropna(subset=['data_servico'])
    
    unique_ids = df_copy['numero_identificacao'].unique()

    for ext_id in unique_ids:
        # 1. Pega todo o histórico do extintor específico
        ext_df = df_copy[df_copy['numero_identificacao'] == ext_id].sort_values(by='data_servico')
        if ext_df.empty: 
            continue
        
        # 2. Pega o último registro cronológico para informações gerais (plano de ação, selo, tipo, etc.)
        latest_record_info = ext_df.iloc[-1]
        
        # 3. Encontra a data MAIS RECENTE para CADA tipo de serviço, buscando em todo o histórico do extintor
        last_insp_date = ext_df['data_servico'].max()
        last_maint2_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 2']['data_servico'].max()
        # Busca a data do último ensaio hidrostático em todo o histórico, não apenas no último registro
        last_maint3_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 3']['data_servico'].max()
        
        # 4. Calcula os PRÓXIMOS vencimentos com base nas datas mais recentes de cada tipo
        next_insp = (last_insp_date + relativedelta(months=1)) if pd.notna(last_insp_date) else pd.NaT
        next_maint2 = (last_maint2_date + relativedelta(months=12)) if pd.notna(last_maint2_date) else pd.NaT
        next_maint3 = (last_maint3_date + relativedelta(years=5)) if pd.notna(last_maint3_date) else pd.NaT
        
        # 5. Determina o vencimento geral (o mais próximo de hoje)
        vencimentos = [d for d in [next_insp, next_maint2, next_maint3] if pd.notna(d)]
        if not vencimentos: 
            continue
        proximo_vencimento_real = min(vencimentos)
        
        # 6. Define o STATUS ATUAL com base em todas as condições
        today_ts = pd.Timestamp(date.today())
        status_atual = "OK"
        
        if latest_record_info.get('plano_de_acao') == "FORA DE OPERAÇÃO (SUBSTITUÍDO)":
            status_atual = "FORA DE OPERAÇÃO"
        elif latest_record_info.get('aprovado_inspecao') == 'Não': 
            status_atual = "NÃO CONFORME (Aguardando Ação)"
        elif proximo_vencimento_real < today_ts: 
            status_atual = "VENCIDO"

        if status_atual == "FORA DE OPERAÇÃO":
            continue

        consolidated_data.append({
            'numero_identificacao': ext_id,
            'numero_selo_inmetro': latest_record_info.get('numero_selo_inmetro'),
            'tipo_agente': latest_record_info.get('tipo_agente'),
            'status_atual': status_atual,
            'proximo_vencimento_geral': proximo_vencimento_real.strftime('%d/%m/%Y'),
            'prox_venc_inspecao': next_insp.strftime('%d/%m/%Y') if pd.notna(next_insp) else "N/A",
            'prox_venc_maint2': next_maint2.strftime('%d/%m/%Y') if pd.notna(next_maint2) else "N/A",
            'prox_venc_maint3': next_maint3.strftime('%d/%m/%Y') if pd.notna(next_maint3) else "N/A",
            'plano_de_acao': latest_record_info.get('plano_de_acao'),
        })

    if not consolidated_data:
        return pd.DataFrame()

    # Junta com as informações de localização no final
    dashboard_df = pd.DataFrame(consolidated_data)
    if not df_locais.empty:
        df_locais = df_locais.rename(columns={'id': 'numero_identificacao'})
        df_locais['numero_identificacao'] = df_locais['numero_identificacao'].astype(str)
        dashboard_df = pd.merge(dashboard_df, df_locais[['numero_identificacao', 'local']], on='numero_identificacao', how='left')
        dashboard_df['status_instalacao'] = dashboard_df['local'].apply(lambda x: f"✅ {x}" if pd.notna(x) and str(x).strip() != '' else "⚠️ Local não definido")
    else:
        dashboard_df['status_instalacao'] = "⚠️ Local não definido"
        
    return dashboard_df

@st.dialog("Registrar Plano de Ação para Abrigo")
def action_dialog_shelter(shelter_id, problem):
    st.write(f"**Abrigo ID:** `{shelter_id}`")
    st.write(f"**Problema Identificado:** `{problem}`")
    
    action_taken = st.text_area("Descreva a ação corretiva realizada:")
    responsible = st.text_input("Responsável pela ação:", value=get_user_display_name())
    
    st.markdown("---")
    new_inspection = st.checkbox("Realizar nova inspeção agora para regularizar o status?", value=True)
    
    if st.button("Salvar Ação", type="primary"):
        if not action_taken:
            st.error("Por favor, descreva a ação realizada.")
            return

        with st.spinner("Registrando ação..."):
            # Salva o log da ação
            log_saved = save_shelter_action_log(shelter_id, problem, action_taken, responsible)
            
            if not log_saved:
                st.error("Falha ao salvar o log da ação.")
                return

            # Se o usuário marcou, realiza uma nova inspeção "OK"
            if new_inspection:
                # Criamos um resultado de inspeção "perfeito" para regularizar
                inspection_results = {"Condições Gerais": {"Lacre": "Sim", "Sinalização": "Sim", "Acesso": "Sim"}}
                inspection_saved = save_shelter_inspection(shelter_id, "Aprovado", inspection_results, get_user_display_name())
                if not inspection_saved:
                    st.error("Log salvo, mas falha ao registrar a nova inspeção de regularização.")
                    return
            
            st.success("Plano de ação registrado com sucesso!")
            st.cache_data.clear()
            st.rerun()

@st.dialog("Registrar Ação Corretiva")
def action_form(item, df_full_history, location):
    # (Esta função permanece sem alterações)
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
        
        if gallery_photo:
            photo_evidence = gallery_photo
        else:
            photo_evidence = camera_photo
       
    if st.button("Salvar Ação", type="primary"):
        if not acao_realizada:
            st.error("Por favor, descreva a ação realizada.")
            return

        original_record = find_last_record(df_full_history, item['numero_identificacao'], 'numero_identificacao')
        if id_substituto:
            df_locais = load_sheet_data("locais")
            if not df_locais.empty:
                df_locais['id'] = df_locais['id'].astype(str)
                original_location_info = df_locais[df_locais['id'] == original_record['numero_identificacao']]
                if original_location_info.empty or pd.isna(original_location_info.iloc[0]['local']):
                     st.error("Erro: O equipamento original não tem um local definido na aba 'locais', portanto a substituição não pode ser concluída.")
                     return
            else:
                st.error("Erro: A aba 'locais' não foi encontrada ou está vazia.")
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
    # (Esta função permanece sem alterações)
    st.title("Situação Atual dos Equipamentos de Emergência")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    tab_extinguishers, tab_hoses, tab_shelters = st.tabs(["🔥 Extintores", "💧 Mangueiras", "🧯 Abrigos"])

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
        df_locais = load_sheet_data("locais") 

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
                
                expander_title = f"{status_icon} **ID:** {row['numero_identificacao']} | **Tipo:** {row['tipo_agente']} | **Status:** {row['status_atual']} | **Localização:** {row['status_instalacao']}"
                
                with st.expander(expander_title):
                    st.markdown(f"**Plano de Ação Sugerido:** {row['plano_de_acao']}")
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
        df_hoses_history = load_sheet_data(HOSE_SHEET_NAME)

        if df_hoses_history.empty:
            st.warning("Ainda não há registros de inspeção de mangueiras para exibir.")
        else:
            dashboard_df_hoses = get_hose_status_df(df_hoses_history)
            
            status_counts = dashboard_df_hoses['status'].value_counts()
            col1, col2, col3 = st.columns(3)
            col1.metric("✅ Total de Mangueiras", len(dashboard_df_hoses))
            col2.metric("🟢 OK", status_counts.get("🟢 OK", 0))
            col3.metric("🔴 VENCIDO", status_counts.get("🔴 VENCIDO", 0))
            
            st.markdown("---")
            
            st.subheader("Lista de Mangueiras")
            st.dataframe(
                dashboard_df_hoses,
                column_config={
                    "id_mangueira": "ID",
                    "status": "Status",
                    "marca": "Marca",
                    "diametro": "Diâmetro",
                    "tipo": "Tipo",
                    "comprimento": "Comprimento",
                    "ano_fabricacao": "Ano Fab.",
                    "data_inspecao": "Último Teste",
                    "data_proximo_teste": "Próximo Teste",
                    "registrado_por": "Registrado Por",
                    "link_certificado_pdf": st.column_config.LinkColumn(
                        "Certificado",
                        display_text="🔗 Ver PDF"
                    )
                },
                hide_index=True,
                use_container_width=True
            )

    with tab_shelters:
        st.header("Dashboard de Status dos Abrigos de Emergência")
        df_inspections_history = load_sheet_data(INSPECTIONS_SHELTER_SHEET_NAME)

        if df_inspections_history.empty:
            st.warning("Nenhuma inspeção de abrigo registrada.")
        else:
            dashboard_df_shelters = get_shelter_status_df(df_inspections_history)
            status_counts = dashboard_df_shelters['status_dashboard'].value_counts()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ Total de Abrigos", len(dashboard_df_shelters))
            col2.metric("🟢 OK", status_counts.get("🟢 OK", 0))
            col3.metric("🟠 Com Pendências", status_counts.get("🟠 COM PENDÊNCIAS", 0))
            col4.metric("🔴 Vencido", status_counts.get("🔴 VENCIDO", 0))
            st.markdown("---")
            st.subheader("Lista de Abrigos e Status")

            for _, row in dashboard_df_shelters.iterrows():
                status = row['status_dashboard']
                expander_title = f"{status} | **ID:** {row['id_abrigo']} | **Próx. Inspeção:** {row['data_proxima_inspecao']}"
                
                with st.expander(expander_title):
                    st.write(f"**Última inspeção:** {row['data_inspecao']} por **{row['inspetor']}**")
                    st.write(f"**Resultado da última inspeção:** {row['status_geral']}")
                    
                    # Botão para registrar ação, visível apenas se não estiver OK
                    if status != "🟢 OK":
                        if st.button("✍️ Registrar Plano de Ação", key=f"action_{row['id_abrigo']}", use_container_width=True):
                            action_dialog_shelter(row['id_abrigo'], row['status_geral'])

                    # Carregar detalhes da inspeção para mostrar os itens
                    full_record = load_sheet_data(INSPECTIONS_SHELTER_SHEET_NAME)
                    detail_row = full_record[(full_record['id_abrigo'] == row['id_abrigo']) & (pd.to_datetime(full_record['data_inspecao']).dt.strftime('%d/%m/%Y') == row['data_inspecao'])]
                    if not detail_row.empty:
                        try:
                            results_dict = json.loads(detail_row.iloc[0]['resultados_json'])
                            results_df = pd.DataFrame.from_dict(results_dict, orient='index')
                            st.table(results_df)
                        except (json.JSONDecodeError, TypeError):
                            st.error("Não foi possível carregar os detalhes desta inspeção.")



# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_dashboard_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
