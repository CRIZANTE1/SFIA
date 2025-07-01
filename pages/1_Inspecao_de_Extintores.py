import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import date
import sys
import os

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
    Decodifica o QR code, que pode ser simples ou composto (separado por '#').
    Retorna o Selo INMETRO, que é o identificador principal.
    """
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        decoded_text, _, _ = detector.detectAndDecode(img)

        if not decoded_text:
            return None

        if '#' in decoded_text:
            parts = decoded_text.split('#')
            return parts[3].strip() if len(parts) >= 4 else None
        else:
            return decoded_text.strip()
    except Exception:
        return None

def find_last_record(df, search_value, column_name):
    """Função genérica para encontrar o último registro com base em um valor e coluna."""
    if df.empty or column_name not in df.columns: return None
    records = df[df[column_name].astype(str) == str(search_value)]
    if records.empty: return None
    if 'data_servico' in records.columns:
        records.loc[:, 'data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
        records.dropna(subset=['data_servico'], inplace=True)
        if records.empty: return None
        return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
    return records.iloc[0].to_dict()

# --- Estrutura Principal da Página ---
def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")
    tab_batch, tab_qr = st.tabs(["🗂️ Registro em Lote por PDF", "📱 Inspeção Rápida por QR Code"])

    # --- Aba 1: Registro em Lote por PDF ---
    with tab_batch:
        st.header("Processar Relatório de Inspeção/Manutenção")
        
        # Inicializa o estado da sessão para o fluxo em lote
        if 'batch_step' not in st.session_state:
            st.session_state.batch_step = 'start'
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = None
        if 'uploaded_pdf_file' not in st.session_state:
            st.session_state.uploaded_pdf_file = None
        if 'service_level' not in st.session_state:
            st.session_state.service_level = "Inspeção"

        st.subheader("1. Selecione o Serviço e o Relatório")
        
        # Armazena o nível de serviço no estado da sessão
        st.session_state.service_level = st.selectbox(
            "Tipo de serviço realizado:", 
            ["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"], 
            index=["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"].index(st.session_state.service_level),
            key="batch_service_level"
        )
        
        uploaded_pdf = st.file_uploader("Escolha o relatório PDF", type=["pdf"], key="batch_pdf_uploader")
        if uploaded_pdf is not None:
            # Armazena o objeto do arquivo no estado da sessão para uso posterior
            st.session_state.uploaded_pdf_file = uploaded_pdf

        # Botão para processar os dados (sem salvar no Drive)
        if st.session_state.uploaded_pdf_file and st.button("🔎 Analisar Dados do PDF com IA"):
            with st.spinner("Analisando o documento com IA..."):
                extracted_list = process_extinguisher_pdf(st.session_state.uploaded_pdf_file)
                if extracted_list:
                    processed_list = []
                    for item in extracted_list:
                        if isinstance(item, dict):
                            item['tipo_servico'] = st.session_state.service_level
                            item['link_relatorio_pdf'] = "Aguardando salvamento..." if st.session_state.service_level != "Inspeção" else "N/A"
                            item.update(calculate_next_dates(item.get('data_servico'), st.session_state.service_level, item.get('tipo_agente')))
                            item['plano_de_acao'] = generate_action_plan(item)
                            processed_list.append(item)
                    
                    st.session_state.processed_data = processed_list
                    st.session_state.batch_step = 'confirm'
                    st.rerun()
                else:
                    st.error("Não foi possível extrair dados do arquivo.")
        
        # ETAPA DE CONFIRMAÇÃO E SALVAMENTO
        if st.session_state.batch_step == 'confirm' and st.session_state.processed_data:
            st.subheader("2. Confira os Dados e Confirme o Registro")
            st.info("Verifique a tabela abaixo. Ao clicar em 'Confirmar e Salvar', o relatório PDF (se aplicável) será salvo no Google Drive e os registros serão adicionados à planilha.")
            
            st.dataframe(pd.DataFrame(st.session_state.processed_data))

            if st.button("💾 Confirmar e Salvar no Sistema", type="primary"):
                with st.spinner("Iniciando processo de salvamento..."):
                    pdf_link = None
                    if st.session_state.service_level in ["Manutenção Nível 2", "Manutenção Nível 3"]:
                        st.write("Fazendo upload do relatório PDF para o Google Drive...")
                        uploader = GoogleDriveUploader()
                        try:
                            # Garante que o buffer do arquivo seja lido desde o início
                            st.session_state.uploaded_pdf_file.seek(0)
                            pdf_name = f"Relatorio_{st.session_state.service_level.replace(' ', '_')}_{date.today().isoformat()}_{st.session_state.uploaded_pdf_file.name}"
                            pdf_link = uploader.upload_file(st.session_state.uploaded_pdf_file, novo_nome=pdf_name)
                            st.success("Relatório PDF salvo no Google Drive!")
                        except Exception as e:
                            st.error(f"Falha ao fazer upload do PDF: {e}")
                            st.stop()

                    progress_bar = st.progress(0, "Salvando registros na planilha...")
                    total_count = len(st.session_state.processed_data)
                    for i, record in enumerate(st.session_state.processed_data):
                        record['link_relatorio_pdf'] = pdf_link
                        save_inspection(record)
                        progress_bar.progress((i + 1) / total_count, f"Salvando {i+1}/{total_count}...")
                    
                    st.success(f"{total_count} registros salvos com sucesso!")
                    st.balloons()

                    # Limpa o estado para um novo ciclo
                    st.session_state.batch_step = 'start'
                    st.session_state.processed_data = None
                    st.session_state.uploaded_pdf_file = None
                    st.rerun()

    # --- Aba 2: Inspeção Rápida por QR Code ---
    with tab_qr:
        st.header("Verificação Rápida de Equipamento")
        if 'qr_step' not in st.session_state: st.session_state.qr_step = 'start'
        if 'qr_id' not in st.session_state: st.session_state.qr_id = None
        if 'last_record' not in st.session_state: st.session_state.last_record = None
        
        if st.session_state.qr_step == 'start':
            st.info("Clique no botão abaixo para ativar a câmera e escanear o QR Code do extintor.")
            if st.button("📷 Iniciar Leitura de QR Code", type="primary"):
                st.session_state.qr_step = 'scan'; st.rerun()
        
        if st.session_state.qr_step == 'scan':
            qr_image = st.camera_input("Aponte a câmera para o QR Code e tire a foto", key="qr_camera")
            if qr_image:
                with st.spinner("Processando imagem..."):
                    decoded_id = decode_qr_from_image(qr_image)
                    if decoded_id:
                        st.session_state.qr_id = decoded_id
                        df_history = load_sheet_data("extintores")
                        st.session_state.last_record = find_last_record(df_history, decoded_id, 'numero_selo_inmetro')
                        st.session_state.qr_step = 'inspect'; st.rerun()
                    else:
                        st.warning("Nenhum QR Code detectado. Tente novamente.")
        
        if st.session_state.qr_step == 'inspect':
            if st.session_state.last_record:
                last_record = st.session_state.last_record
                st.success(f"Extintor Encontrado! Selo INMETRO: **{st.session_state.qr_id}**")
                
                with st.container(border=True):
                    st.subheader("Último Registro do Equipamento")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("ID do Cilindro", last_record.get('numero_identificacao', 'N/A'))
                    col2.metric("Tipo", last_record.get('tipo_agente', 'N/A'))
                    next_insp_date = last_record.get('data_proxima_inspecao')
                    col3.metric("Próxima Inspeção", pd.to_datetime(next_insp_date).strftime('%d/%m/%Y') if pd.notna(next_insp_date) else 'N/A')

                st.subheader("Registrar Nova Inspeção (Nível 1)")
                with st.form("quick_inspection_form"):
                    status = st.radio("Status do Extintor:", ["Conforme", "Não Conforme"], horizontal=True, key="qr_status")
                    issues = []
                    if status == "Não Conforme":
                        issue_options = ["Lacre Violado", "Manômetro Fora de Faixa", "Dano Visível", "Obstrução", "Sinalização Inadequada", "Pintura Danificada"]
                        issues = st.multiselect("Selecione as não conformidades:", issue_options, key="qr_issues")
                    
                    col_form1, col_form2 = st.columns([1,1])
                    with col_form1:
                        if st.form_submit_button("✅ Registrar Inspeção", use_container_width=True, type="primary"):
                            with st.spinner("Salvando..."):
                                new_record = last_record.copy()
                                new_record.update({
                                    'tipo_servico': "Inspeção", 'data_servico': date.today().isoformat(),
                                    'inspetor_responsavel': get_user_display_name(),
                                    'aprovado_inspecao': "Sim" if status == "Conforme" else "Não",
                                    'observacoes_gerais': "Inspeção de rotina OK." if status == "Conforme" else ", ".join(issues),
                                    'link_relatorio_pdf': None
                                })
                                new_record.update(calculate_next_dates(new_record['data_servico'], new_record['tipo_servico'], new_record['tipo_agente']))
                                new_record['plano_de_acao'] = generate_action_plan(new_record)
                                
                                if save_inspection(new_record):
                                    st.success(f"Inspeção para o selo {st.session_state.qr_id} registrada!")
                                    st.balloons(); st.session_state.qr_step = 'start'; st.rerun()
                    with col_form2:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.qr_step = 'start'; st.rerun()
            else:
                st.error(f"Nenhum registro encontrado para o Selo INMETRO '{st.session_state.qr_id}'.")
                if st.button("Tentar Novamente"):
                    st.session_state.qr_step = 'start'; st.rerun()

# --- Boilerplate de Autenticação ---
if not show_login_page(): st.stop()
show_user_header(); show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    main_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
