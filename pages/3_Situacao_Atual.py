import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import sys
import os
import numpy as np
import json
from streamlit_js_eval import streamlit_js_eval

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data, find_last_record
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 
from gdrive.config import HOSE_SHEET_NAME, SHELTER_SHEET_NAME, INSPECTIONS_SHELTER_SHEET_NAME, LOG_SHELTER_SHEET_NAME, SCBA_SHEET_NAME
from reports.reports_pdf import generate_shelters_html
from operations.shelter_operations import save_shelter_action_log, save_shelter_inspection
from operations.corrective_actions import save_corrective_action
from reports.reports_pdf import generate_shelters_html 
from operations.photo_operations import upload_evidence_photo



set_page_config()

def get_scba_status_df(df_scba_history):
    if df_scba_history.empty:
        return pd.DataFrame(), "N/A"

    equipment_tests = df_scba_history.dropna(subset=['data_teste']).copy()
    air_quality_reports = df_scba_history.dropna(subset=['data_qualidade_ar']).copy()

    air_status_geral = "⚠️ Pendente"
    if not air_quality_reports.empty:
        air_quality_reports['data_qualidade_ar'] = pd.to_datetime(air_quality_reports['data_qualidade_ar'], errors='coerce')
        last_air_report = air_quality_reports.sort_values('data_qualidade_ar', ascending=False).iloc[0]
        qa_status = last_air_report['status_qualidade_ar']
        qa_date = last_air_report['data_qualidade_ar'].strftime('%d/%m/%Y')
        air_status_geral = f"{'🟢' if qa_status == 'Aprovado' else '🔴'} {qa_status} (Laudo de {qa_date})"

    if equipment_tests.empty:
        return pd.DataFrame(), air_status_geral
        
    equipment_tests['data_validade'] = pd.to_datetime(equipment_tests['data_validade'], errors='coerce')
    latest_tests = equipment_tests.sort_values('data_teste', ascending=False).drop_duplicates(subset='numero_serie_equipamento', keep='first')
    
    today = pd.Timestamp(date.today())
    latest_tests['status_equipamento'] = np.where(latest_tests['data_validade'] < today, '🔴 VENCIDO', '🟢 OK')
    
    latest_tests['data_validade'] = latest_tests['data_validade'].dt.strftime('%d/%m/%Y').fillna('N/A')

    display_df = latest_tests[['numero_serie_equipamento', 'status_equipamento', 'data_validade', 'link_relatorio_pdf']]
    
    return display_df, air_status_geral
    
def get_hose_status_df(df_hoses):
    if df_hoses.empty:
        return pd.DataFrame()
    
    for col in ['data_inspecao', 'data_proximo_teste']:
        if col not in df_hoses.columns:
            df_hoses[col] = pd.NaT
        df_hoses[col] = pd.to_datetime(df_hoses[col], errors='coerce')

    df_hoses = df_hoses.sort_values('data_inspecao', ascending=False).drop_duplicates(subset='id_mangueira', keep='first').copy()
    
    today = pd.Timestamp(date.today())
    df_hoses['status'] = np.where(df_hoses['data_proximo_teste'] < today, "🔴 VENCIDO", "🟢 OK")
    
    df_hoses['data_inspecao'] = df_hoses['data_inspecao'].dt.strftime('%d/%m/%Y')
    df_hoses['data_proximo_teste'] = df_hoses['data_proximo_teste'].dt.strftime('%d/%m/%Y')
    
    display_columns = [
        'id_mangueira', 'status', 'marca', 'diametro', 'tipo',
        'comprimento', 'ano_fabricacao', 'data_inspecao',
        'data_proximo_teste', 'link_certificado_pdf', 'registrado_por'
    ]
    
    existing_display_columns = [col for col in display_columns if col in df_hoses.columns]
    
    return df_hoses[existing_display_columns]



def get_shelter_status_df(df_shelters_registered, df_inspections):
    if df_shelters_registered.empty:
        return pd.DataFrame()

    latest_inspections_list = []
    if not df_inspections.empty:
        df_inspections['data_inspecao'] = pd.to_datetime(df_inspections['data_inspecao'], errors='coerce').dt.date

        for shelter_id in df_shelters_registered['id_abrigo'].unique():
            shelter_inspections = df_inspections[df_inspections['id_abrigo'] == shelter_id].copy()
            if not shelter_inspections.empty:
                shelter_inspections = shelter_inspections.sort_values(by='data_inspecao', ascending=False)
                
                # LÓGICA DE DESEMPATE: Se houver várias inspeções no dia mais recente,
                # priorize a que NÃO é "Reprovado com Pendências".
                latest_date = shelter_inspections['data_inspecao'].iloc[0]
                inspections_on_latest_date = shelter_inspections[shelter_inspections['data_inspecao'] == latest_date]
                
                approved_on_latest = inspections_on_latest_date[inspections_on_latest_date['status_geral'] != 'Reprovado com Pendências']
                
                if not approved_on_latest.empty:
                    latest_inspections_list.append(approved_on_latest.iloc[0])
                else:
                    latest_inspections_list.append(inspections_on_latest_date.iloc[0])

    latest_inspections = pd.DataFrame(latest_inspections_list)

    if not latest_inspections.empty:
        dashboard_df = pd.merge(df_shelters_registered[['id_abrigo', 'cliente']], latest_inspections, on='id_abrigo', how='left')
    else:

        dashboard_df = df_shelters_registered.copy()
        for col in ['data_inspecao', 'data_proxima_inspecao', 'status_geral', 'inspetor', 'resultados_json']:
            dashboard_df[col] = None

    today = pd.to_datetime(date.today()).date()
    dashboard_df['data_proxima_inspecao'] = pd.to_datetime(dashboard_df['data_proxima_inspecao'], errors='coerce').dt.date

    conditions = [
        (dashboard_df['data_inspecao'].isna()),
        (dashboard_df['data_proxima_inspecao'] < today),
        (dashboard_df['status_geral'] == 'Reprovado com Pendências')
    ]
    choices = ['🔵 PENDENTE (Nova Inspeção)', '🔴 VENCIDO', '🟠 COM PENDÊNCIAS']
    dashboard_df['status_dashboard'] = np.select(conditions, choices, default='🟢 OK')

    dashboard_df['data_inspecao_str'] = dashboard_df['data_inspecao'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else 'N/A')
    dashboard_df['data_proxima_inspecao_str'] = dashboard_df['data_proxima_inspecao'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else 'N/A')
    dashboard_df['inspetor'] = dashboard_df['inspetor'].fillna('N/A')
    dashboard_df['resultados_json'] = dashboard_df['resultados_json'].fillna('{}')

    display_columns = ['id_abrigo', 'status_dashboard', 'data_inspecao_str', 'data_proxima_inspecao_str', 'status_geral', 'inspetor', 'resultados_json']
    existing_columns = [col for col in display_columns if col in dashboard_df.columns]
    
    return dashboard_df[existing_columns]


def get_consolidated_status_df(df_full, df_locais):
    if df_full.empty: 
        return pd.DataFrame()
    
    consolidated_data = []
    df_copy = df_full.copy()
    df_copy['data_servico'] = pd.to_datetime(df_copy['data_servico'], errors='coerce')
    df_copy = df_copy.dropna(subset=['data_servico'])
    
    unique_ids = df_copy['numero_identificacao'].unique()

    for ext_id in unique_ids:
        ext_df = df_copy[df_copy['numero_identificacao'] == ext_id].sort_values(by='data_servico')
        if ext_df.empty: 
            continue
        
        latest_record_info = ext_df.iloc[-1]
        
        last_insp_date = ext_df['data_servico'].max()
        last_maint2_date = ext_df[ext_df['tipo_servico'] == 'Manutenção Nível 2']['data_servico'].max()
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
    
    if st.button("Salvar Ação e Regularizar Status", type="primary"):
        if not action_taken:
            st.error("Por favor, descreva a ação realizada.")
            return

        with st.spinner("Registrando ação e regularizando status..."):
            log_saved = save_shelter_action_log(shelter_id, problem, action_taken, responsible)
            
            if not log_saved:
                st.error("Falha ao salvar o log da ação. O status não foi atualizado.")
                return

            
            df_shelters = load_sheet_data(SHELTER_SHEET_NAME)
            shelter_inventory_row = df_shelters[df_shelters['id_abrigo'] == shelter_id]
            
            if shelter_inventory_row.empty:
                st.error(f"Não foi possível encontrar o inventário original para o abrigo {shelter_id}. A regularização falhou.")
                return

            try:
                items_dict = json.loads(shelter_inventory_row.iloc[0]['itens_json'])
                
                inspection_results = {item: {"status": "OK", "observacao": "Regularizado via ação corretiva"} for item in items_dict}
                
                inspection_results["Condições Gerais"] = {
                    "Lacre": "Sim", "Sinalização": "Sim", "Acesso": "Sim"
                }
                
            except (json.JSONDecodeError, TypeError):
                st.error(f"O inventário do abrigo {shelter_id} está corrompido na planilha. A regularização falhou.")
                return

            inspection_saved = save_shelter_inspection(
                shelter_id=shelter_id,
                overall_status="Aprovado",
                inspection_results=inspection_results,
                inspector_name=get_user_display_name()
            )
            
            if inspection_saved:
                st.success("Plano de ação registrado e status do abrigo regularizado com sucesso!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Log salvo, mas falha ao registrar a nova inspeção de regularização. O status pode continuar pendente.")


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
    st.title("Situação Atual dos Equipamentos de Emergência")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()

    tab_extinguishers, tab_hoses, tab_shelters, tab_scba = st.tabs(["🔥 Extintores", "💧 Mangueiras", "🧯 Abrigos", "💨 C. Autônomo"])

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
        
        df_shelters_registered = load_sheet_data(SHELTER_SHEET_NAME)
        df_inspections_history = load_sheet_data(INSPECTIONS_SHELTER_SHEET_NAME)
        df_action_log = load_sheet_data(LOG_SHELTER_SHEET_NAME)

        if df_shelters_registered.empty:
            st.warning("Nenhum abrigo de emergência cadastrado.")
        else:
            st.info("Aqui está o status de todos os abrigos. Gere um relatório de status completo para impressão ou registre ações corretivas.")
            if st.button("📄 Gerar Relatório de Status em PDF", type="primary"):
                report_html = generate_shelters_html(df_shelters_registered, df_inspections_history, df_action_log)
                js_code = f"""
                    const reportHtml = {json.dumps(report_html)};
                    const printWindow = window.open('', '_blank');
                    if (printWindow) {{
                        printWindow.document.write(reportHtml);
                        printWindow.document.close();
                        printWindow.focus();
                        setTimeout(() => {{ printWindow.print(); printWindow.close(); }}, 500);
                    }} else {{
                        alert('Por favor, desabilite o bloqueador de pop-ups para este site.');
                    }}
                """
                streamlit_js_eval(js_expressions=js_code, key="print_shelters_js")
                st.success("Relatório de status enviado para impressão!")
            st.markdown("---")

            dashboard_df_shelters = get_shelter_status_df(df_shelters_registered, df_inspections_history)
            
            status_counts = dashboard_df_shelters['status_dashboard'].value_counts()
            ok_count = status_counts.get("🟢 OK", 0) + status_counts.get("🟢 OK (Ação Realizada)", 0)
            pending_count = status_counts.get("🟠 COM PENDÊNCIAS", 0) + status_counts.get("🔵 PENDENTE (Nova Inspeção)", 0)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ Total de Abrigos", len(dashboard_df_shelters))
            col2.metric("🟢 OK", ok_count)
            col3.metric("🟠 Pendentes", pending_count)
            col4.metric("🔴 Vencido", status_counts.get("🔴 VENCIDO", 0))
            st.markdown("---")
            
            st.subheader("Lista de Abrigos e Status")
            for _, row in dashboard_df_shelters.iterrows():
                status = row['status_dashboard']
                prox_inspecao_str = row['data_proxima_inspecao_str']
                expander_title = f"{status} | **ID:** {row['id_abrigo']} | **Próx. Inspeção:** {prox_inspecao_str}"
                
                with st.expander(expander_title):
                    data_inspecao_str = row['data_inspecao_str']
                    st.write(f"**Última inspeção:** {data_inspecao_str} por **{row['inspetor']}**")
                    st.write(f"**Resultado da última inspeção:** {row.get('status_geral', 'N/A')}")
                    
                    if status not in ["🟢 OK", "🟢 OK (Ação Realizada)"]:
                        problem_description = status.replace("🔴 ", "").replace("🟠 ", "").replace("🔵 ", "")
                        if st.button("✍️ Registrar Ação", key=f"action_{row['id_abrigo']}", use_container_width=True):
                            action_dialog_shelter(row['id_abrigo'], problem_description)
                    
                    st.markdown("---")
                    st.write("**Detalhes da Última Inspeção:**")

                    try:
                        results_dict = json.loads(row['resultados_json'])
                        
                        if results_dict:                
                            general_conditions = results_dict.pop('Condições Gerais', {})
                           
                            if results_dict: 
                                st.write("**Itens do Inventário:**")
                                items_df = pd.DataFrame.from_dict(results_dict, orient='index')
                                st.table(items_df)
                            
                            if general_conditions:
                                st.write("**Condições Gerais do Abrigo:**")
                                cols = st.columns(len(general_conditions))
                                for i, (key, value) in enumerate(general_conditions.items()):
                                    with cols[i]:
                                        st.metric(label=key, value=value)
                            
                        else:
                            st.info("Nenhum detalhe de inspeção disponível.")
                            
                    except (json.JSONDecodeError, TypeError):
                        st.error("Não foi possível carregar os detalhes desta inspeção (formato inválido).")

    with tab_scba:
            st.header("Dashboard de Status dos Conjuntos Autônomos")
            df_scba_history = load_sheet_data(SCBA_SHEET_NAME)
    
            if df_scba_history.empty:
                st.warning("Nenhum registro de conjunto autônomo encontrado.")
            else:
                dashboard_df_scba, air_status = get_scba_status_df(df_scba_history)
                
                status_counts = dashboard_df_scba['status_equipamento'].value_counts()
                col1, col2, col3 = st.columns(3)
                col1.metric("✅ Total de Equipamentos", len(dashboard_df_scba))
                col2.metric("🟢 Equipamentos OK", status_counts.get("🟢 OK", 0))
                col3.metric("🌬️ Qualidade do Ar", air_status, help="Status baseado no último laudo de qualidade do ar registrado. Afeta todos os equipamentos.")
                
                st.markdown("---")
                st.subheader("Lista de Equipamentos")
                st.dataframe(
                    dashboard_df_scba,
                    column_config={
                        "numero_serie_equipamento": "Nº de Série",
                        "status_equipamento": "Status do Equipamento",
                        "data_validade": "Validade do Teste",
                        "link_relatorio_pdf": st.column_config.LinkColumn(
                            "Relatório (PDF)",
                            display_text="🔗 Ver PDF"
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )

# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_dashboard_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
