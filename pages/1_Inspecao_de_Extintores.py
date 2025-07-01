import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import date
import sys
import os

# Importa o novo componente de geolocalização
from streamlit_js_eval import get_geolocation

# Adiciona o diretório raiz ao path para encontrar os outros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.extinguisher_operations import (
    process_extinguisher_pdf, calculate_next_dates, save_inspection, generate_action_plan
)
from operations.history import load_sheet_data
from gdrive.gdrive_upload import GoogleDriveUploader
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page

# --- Funções para a Aba de Inspeção Rápida ---

def decode_qr_from_image(image_file):
    """
    Decodifica o QR code e retorna o ID do Equipamento e o Selo INMETRO.
    Retorna uma tupla: (id_equipamento, selo_inmetro)
    """
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        decoded_text, _, _ = detector.detectAndDecode(img)
        
        if not decoded_text:
            return None, None
        
        decoded_text = decoded_text.strip()
        if '#' in decoded_text:
            parts = decoded_text.split('#')
            if len(parts) >= 4:
                id_equipamento = parts[1].strip()
                selo_inmetro = parts[3].strip()
                return id_equipamento, selo_inmetro
            return None, None
        else:
            return decoded_text, None
    except Exception:
        return None, None

def find_last_record(df, search_value, column_name):
    """Função genérica para encontrar o último registro com base em um valor e coluna."""
    if df.empty or column_name not in df.columns: return None
    records = df[df[column_name].astype(str) == str(search_value)].copy()
    if records.empty: return None
    records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
    records = records.dropna(subset=['data_servico'])
    if records.empty: return None
    return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()

# --- Estrutura Principal da Página ---
def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")
    tab_batch, tab_qr = st.tabs(["🗂️ Registro em Lote por PDF", "📱 Inspeção Rápida por QR Code"])
    
    with tab_batch:
        st.header("Processar Relatório de Inspeção/Manutenção")
        st.session_state.setdefault('batch_step', 'start'); st.session_state.setdefault('processed_data', None); st.session_state.setdefault('uploaded_pdf_file', None); st.session_state.setdefault('service_level', "Inspeção")
        st.subheader("1. Selecione o Serviço e o Relatório")
        st.session_state.service_level = st.selectbox("Tipo de serviço:", ["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"], index=["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"].index(st.session_state.service_level), key="batch_service_level")
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
        st.session_state.setdefault('qr_step', 'start'); st.session_state.setdefault('qr_id', None)
        st.session_state.setdefault('qr_selo', None); st.session_state.setdefault('last_record', None)
        
        location = get_geolocation(timeout=20000)

        if st.session_state.qr_step == 'start':
            if st.button("📷 Iniciar Leitura", type="primary"): st.session_state.qr_step = 'scan'; st.rerun()
        
        if st.session_state.qr_step == 'scan':
            qr_image = st.camera_input("Aponte para o QR Code do Equipamento", key="qr_camera")
            if qr_image:
                with st.spinner("Processando..."):
                    decoded_id, decoded_selo = decode_qr_from_image(qr_image)
                    if decoded_id:
                        st.session_state.qr_id = decoded_id; st.session_state.qr_selo = decoded_selo
                        st.success(f"QR lido! ID Equip: **{decoded_id}** | Selo Atual: **{decoded_selo or 'N/A'}**")
                        st.session_state.last_record = find_last_record(load_sheet_data("extintores"), decoded_id, 'numero_identificacao')
                        st.session_state.qr_step = 'inspect'; st.rerun()
                    else: st.warning("QR Code não detectado.")
        
        if st.session_state.qr_step == 'inspect':
            if st.session_state.last_record:
                last_record = st.session_state.last_record
                st.success(f"Equipamento Encontrado! ID: **{st.session_state.qr_id}**")
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Último Selo Registrado", last_record.get('numero_selo_inmetro', 'N/A'))
                    col2.metric("Tipo", last_record.get('tipo_agente', 'N/A'))
                    vencimentos = [pd.to_datetime(last_record.get(d), errors='coerce') for d in ['data_proxima_inspecao', 'data_proxima_manutencao_2_nivel', 'data_proxima_manutencao_3_nivel']]
                    valid_vencimentos = [d for d in vencimentos if pd.notna(d)]; proximo_vencimento = min(valid_vencimentos) if valid_vencimentos else None
                    vencimento_str = proximo_vencimento.strftime('%d/%m/%Y') if proximo_vencimento else 'N/A'; col3.metric("Próximo Vencimento", vencimento_str)

                with st.form("quick_inspection_form"):
                    st.subheader("Registrar Nova Inspeção (Nível 1)")
                    
                    if location and location.get('coords'):
                        lat, lon = location['coords']['latitude'], location['coords']['longitude']
                        st.info(f"📍 Localização Capturada: Lat: {lat:.5f}, Lon: {lon:.5f}")
                    else:
                        st.warning("⚠️ Não foi possível obter a localização. Verifique as permissões do navegador e recarregue a página.")
                    
                    status = st.radio("Status:", ["Conforme", "Não Conforme"], horizontal=True)
                    issues = st.multiselect("Não Conformidades:", ["Lacre Violado", "Manômetro Fora de Faixa", "Dano Visível"]) if status == "Não Conforme" else []
                    
                    if st.form_submit_button("✅ Registrar Inspeção", type="primary"):
                        if not location or not location.get('coords'):
                            st.error("Erro: A geolocalização é necessária para registrar a inspeção.")
                        else:
                            with st.spinner("Salvando..."):
                                new_record = last_record.copy()
                                new_record['numero_selo_inmetro'] = st.session_state.qr_selo or last_record.get('numero_selo_inmetro')
                                observacoes = "Inspeção de rotina OK." if status == "Conforme" else ", ".join(issues)
                                temp_plan_record = {'aprovado_inspecao': "Sim" if status == "Conforme" else "Não", 'observacoes_gerais': observacoes}
                                new_record.update({
                                    'tipo_servico': "Inspeção", 'data_servico': date.today().isoformat(),
                                    'inspetor_responsavel': get_user_display_name(),
                                    'aprovado_inspecao': temp_plan_record['aprovado_inspecao'],
                                    'observacoes_gerais': observacoes,
                                    'plano_de_acao': generate_action_plan(temp_plan_record),
                                    'link_relatorio_pdf': None,
                                    'latitude': location['coords']['latitude'],
                                    'longitude': location['coords']['longitude']
                                })
                                new_record.update(calculate_next_dates(new_record['data_servico'], 'Inspeção', new_record['tipo_agente']))
                                
                                if save_inspection(new_record):
                                    st.success(f"Inspeção para o ID {st.session_state.qr_id} registrada com sucesso!"); st.balloons()
                                    st.session_state.qr_step = 'start'; st.rerun()
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
