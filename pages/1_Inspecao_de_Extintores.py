import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import date
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.extinguisher_operations import (
    process_extinguisher_pdf, calculate_next_dates, save_inspection, generate_action_plan
)
from operations.history import load_sheet_data
from gdrive.gdrive_upload import GoogleDriveUploader
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page

def decode_qr_from_image(image_file):
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector(); decoded_text, _, _ = detector.detectAndDecode(img)
        if not decoded_text: return None
        if '#' in decoded_text: parts = decoded_text.split('#'); return parts[3].strip() if len(parts) >= 4 else None
        return decoded_text.strip()
    except: return None

def find_last_record(df, search_value, column_name):
    if df.empty or column_name not in df.columns: return None
    records = df[df[column_name].astype(str) == str(search_value)].copy() # Usa .copy() para evitar o warning
    if records.empty: return None
    if 'data_servico' in records.columns:
        records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
        # CORREÇÃO: Reatribuição em vez de inplace=True
        records = records.dropna(subset=['data_servico'])
        if records.empty: return None
        return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
    return records.iloc[0].to_dict()

def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")
    tab_batch, tab_qr = st.tabs(["🗂️ Registro em Lote por PDF", "📱 Inspeção Rápida por QR Code"])

    with tab_batch:
        # (O código da aba de lote não muda)
        st.header("Processar Relatório"); st.session_state.setdefault('batch_step', 'start'); st.session_state.setdefault('processed_data', None); st.session_state.setdefault('uploaded_pdf_file', None); st.session_state.setdefault('service_level', "Inspeção")
        st.subheader("1. Selecione o Serviço e o Relatório"); st.session_state.service_level = st.selectbox("Tipo de serviço:", ["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"], index=["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"].index(st.session_state.service_level), key="batch_service_level")
        uploaded_pdf = st.file_uploader("Escolha o relatório PDF", type=["pdf"], key="batch_pdf_uploader")
        if uploaded_pdf: st.session_state.uploaded_pdf_file = uploaded_pdf
        if st.session_state.uploaded_pdf_file and st.button("🔎 Analisar Dados do PDF com IA"):
            with st.spinner("Analisando..."):
                extracted_list = process_extinguisher_pdf(st.session_state.uploaded_pdf_file)
                if extracted_list:
                    processed_list = [ {**item, 'tipo_servico': st.session_state.service_level, 'link_relatorio_pdf': "Aguardando salvamento..." if st.session_state.service_level != "Inspeção" else "N/A", **calculate_next_dates(item.get('data_servico'), st.session_state.service_level, item.get('tipo_agente')), 'plano_de_acao': generate_action_plan(item)} for item in extracted_list if isinstance(item, dict) ]
                    st.session_state.processed_data = processed_list; st.session_state.batch_step = 'confirm'; st.rerun()
                else: st.error("Não foi possível extrair dados.")
        if st.session_state.batch_step == 'confirm' and st.session_state.processed_data:
            st.subheader("2. Confira e Confirme"); st.dataframe(pd.DataFrame(st.session_state.processed_data))
            if st.button("💾 Confirmar e Salvar no Sistema", type="primary"):
                with st.spinner("Salvando..."):
                    pdf_link = None
                    if st.session_state.service_level in ["Manutenção Nível 2", "Manutenção Nível 3"]:
                        st.session_state.uploaded_pdf_file.seek(0); uploader = GoogleDriveUploader(); pdf_name = f"Relatorio_{st.session_state.service_level.replace(' ', '_')}_{date.today().isoformat()}_{st.session_state.uploaded_pdf_file.name}"; pdf_link = uploader.upload_file(st.session_state.uploaded_pdf_file, novo_nome=pdf_name)
                    progress_bar = st.progress(0, "Salvando..."); total_count = len(st.session_state.processed_data)
                    for i, record in enumerate(st.session_state.processed_data):
                        record['link_relatorio_pdf'] = pdf_link; save_inspection(record); progress_bar.progress((i + 1) / total_count)
                    st.success("Registros salvos!"); st.balloons(); st.session_state.batch_step = 'start'; st.session_state.processed_data = None; st.session_state.uploaded_pdf_file = None; st.rerun()

    with tab_qr:
        st.header("Verificação Rápida de Equipamento")
        st.session_state.setdefault('qr_step', 'start'); st.session_state.setdefault('qr_id', None); st.session_state.setdefault('last_record', None)
        
        if st.session_state.qr_step == 'start':
            if st.button("📷 Iniciar Leitura de QR Code", type="primary"):
                st.session_state.qr_step = 'scan'; st.rerun()
        
        if st.session_state.qr_step == 'scan':
            qr_image = st.camera_input("Aponte para o QR Code (ID do Equipamento)", key="qr_camera")
            if qr_image:
                with st.spinner("Processando..."):
                    decoded_id = decode_qr_from_image(qr_image)
                    if decoded_id:
                        st.session_state.qr_id = decoded_id
                        st.session_state.last_record = find_last_record(load_sheet_data("extintores"), decoded_id, 'numero_identificacao')
                        st.session_state.qr_step = 'inspect'; st.rerun()
                    else: st.warning("QR Code não detectado.")
        
        if st.session_state.qr_step == 'inspect':
            if st.session_state.last_record:
                last_record = st.session_state.last_record
                st.success(f"Equipamento Encontrado! ID: **{st.session_state.qr_id}**")
                
                with st.container(border=True):
                    # ... (código do container com os metrics não muda)
                    col1, col2, col3 = st.columns(3); col1.metric("Último Selo", last_record.get('numero_selo_inmetro', 'N/A')); col2.metric("Tipo", last_record.get('tipo_agente', 'N/A')); 
                    vencimentos = [pd.to_datetime(last_record.get(d), errors='coerce') for d in ['data_proxima_inspecao', 'data_proxima_manutencao_2_nivel', 'data_proxima_manutencao_3_nivel']]
                    valid_vencimentos = [d for d in vencimentos if pd.notna(d)]; proximo_vencimento = min(valid_vencimentos) if valid_vencimentos else None
                    vencimento_str = proximo_vencimento.strftime('%d/%m/%Y') if proximo_vencimento else 'N/A'
                    col3.metric("Próximo Vencimento", vencimento_str)

                # --- CORREÇÃO DE LÓGICA DO FORMULÁRIO ---
                # O formulário agora é o container principal para a ação de inspeção
                with st.form("quick_inspection_form"):
                    st.subheader("Registrar Nova Inspeção (Nível 1)")
                    
                    status = st.radio("Status do Extintor:", ["Conforme", "Não Conforme"], horizontal=True, key="qr_status")
                    
                    issues = []
                    # O multiselect agora está dentro do mesmo escopo do botão
                    if status == "Não Conforme":
                        issue_options = ["Lacre Violado", "Manômetro Fora de Faixa", "Dano Visível", "Obstrução", "Sinalização Inadequada", "Pintura Danificada"]
                        issues = st.multiselect("Selecione as não conformidades:", issue_options, key="qr_issues")
                    
                    # Botões de submissão e cancelamento
                    submitted = st.form_submit_button("✅ Registrar Inspeção", type="primary")
                    if st.form_submit_button("❌ Cancelar"):
                        st.session_state.qr_step = 'start'
                        st.rerun()

                    # A lógica de salvamento só executa se o botão de registro for clicado
                    if submitted:
                        with st.spinner("Salvando..."):
                            new_record = last_record.copy()
                            new_record.update({
                                'tipo_servico': "Inspeção", 'data_servico': date.today().isoformat(),
                                'inspetor_responsavel': get_user_display_name(),
                                'aprovado_inspecao': "Sim" if status == "Conforme" else "Não",
                                'observacoes_gerais': "Inspeção de rotina OK." if status == "Conforme" else ", ".join(issues),
                                'link_relatorio_pdf': None
                            })
                            new_record.update(calculate_next_dates(new_record['data_servico'], 'Inspeção', new_record['tipo_agente']))
                            new_record['plano_de_acao'] = generate_action_plan(new_record)
                            
                            if save_inspection(new_record):
                                st.success(f"Inspeção para o ID {st.session_state.qr_id} registrada!")
                                st.balloons()
                                st.session_state.qr_step = 'start'
                                st.rerun()
            else:
                st.error(f"Nenhum registro encontrado para o ID de Equipamento '{st.session_state.qr_id}'.")
                if st.button("Tentar Novamente"): st.session_state.qr_step = 'start'; st.rerun()

# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    main_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
