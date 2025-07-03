import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import date
import sys
import os
from streamlit_js_eval import streamlit_js_eval
from operations.history import load_sheet_data, find_last_record

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.extinguisher_operations import (
    process_extinguisher_pdf, calculate_next_dates, save_inspection, generate_action_plan
)
from operations.history import load_sheet_data
from gdrive.gdrive_upload import GoogleDriveUploader
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 

set_page_config()

def decode_qr_from_image(image_file):
    """
    Decodifica o QR code, aplicando pré-processamento para melhorar a detecção.
    Retorna o ID do Equipamento e o Selo (se houver).
    """
    try:
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return None, None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)

        # Inicializa o detector
        detector = cv2.QRCodeDetector()
        
        # Tenta decodificar a imagem processada
        decoded_text, _, _ = detector.detectAndDecode(thresh)

        # Se falhar na imagem processada, tenta na imagem original em tons de cinza
        if not decoded_text:
            decoded_text, _, _ = detector.detectAndDecode(gray)

        # Se ainda falhar, tenta na imagem colorida original como último recurso
        if not decoded_text:
            decoded_text, _, _ = detector.detectAndDecode(img)
            
        if not decoded_text:
            return None, None
        
        # Lógica de extração (permanece a mesma)
        decoded_text = decoded_text.strip()
        if '#' in decoded_text:
            parts = decoded_text.split('#')
            if len(parts) >= 4:
                id_equipamento = parts[3].strip()
                selo_inmetro = None
                return id_equipamento, selo_inmetro
            return None, None
        else:
            id_equipamento = decoded_text
            selo_inmetro = None
            return id_equipamento, selo_inmetro
            
    except Exception:
        return None, None


# --- Estrutura Principal da Página ---
def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")
    tab_batch, tab_qr = st.tabs(["🗂️ Registro em Lote por PDF", "📱 Inspeção Rápida por QR Code"])
    
    with tab_batch:
        st.header("Processar Relatório de Inspeção/Manutenção")
        st.session_state.setdefault('batch_step', 'start')
        st.session_state.setdefault('processed_data', None)
        st.session_state.setdefault('uploaded_pdf_file', None)

        st.subheader("1. Faça o Upload do Relatório")
        st.info("O sistema analisará o PDF e determinará o nível de serviço (Inspeção, Nível 2 ou Nível 3) para cada extintor automaticamente.")
        
        uploaded_pdf = st.file_uploader("Escolha o relatório PDF", type=["pdf"], key="batch_pdf_uploader")
        if uploaded_pdf: 
            st.session_state.uploaded_pdf_file = uploaded_pdf
        
        if st.session_state.uploaded_pdf_file and st.button("🔎 Analisar Dados do PDF com IA"):
            with st.spinner("Analisando o documento com IA..."):
                extracted_list = process_extinguisher_pdf(st.session_state.uploaded_pdf_file)
                if extracted_list:
                    processed_list = []
                    for item in extracted_list:
                        if isinstance(item, dict):
                            # A IA fornece o 'tipo_servico'
                            service_level = item.get('tipo_servico', 'Inspeção') # Usa 'Inspeção' como padrão
                            item['tipo_servico'] = service_level
                            item['link_relatorio_pdf'] = "Aguardando salvamento..." if service_level != "Inspeção" else "N/A"
                            item.update(calculate_next_dates(item.get('data_servico'), service_level, item.get('tipo_agente')))
                            item['plano_de_acao'] = generate_action_plan(item)
                            processed_list.append(item)
                    st.session_state.processed_data = processed_list
                    st.session_state.batch_step = 'confirm'
                    st.rerun()
                else: 
                    st.error("Não foi possível extrair dados do arquivo.")
        
        if st.session_state.batch_step == 'confirm' and st.session_state.processed_data:
            st.subheader("2. Confira os Dados e Confirme o Registro")
            st.dataframe(pd.DataFrame(st.session_state.processed_data))
            if st.button("💾 Confirmar e Salvar no Sistema", type="primary"):
                with st.spinner("Salvando..."):
                    pdf_link = None
                    # Verifica se ALGUM item no lote precisa do upload do PDF
                    if any(rec.get('tipo_servico') in ["Manutenção Nível 2", "Manutenção Nível 3"] for rec in st.session_state.processed_data):
                        st.session_state.uploaded_pdf_file.seek(0)
                        uploader = GoogleDriveUploader()
                        pdf_name = f"Relatorio_Manutencao_{date.today().isoformat()}_{st.session_state.uploaded_pdf_file.name}"
                        pdf_link = uploader.upload_file(st.session_state.uploaded_pdf_file, novo_nome=pdf_name)
                    
                    progress_bar = st.progress(0, "Salvando registros...")
                    total_count = len(st.session_state.processed_data)
                    for i, record in enumerate(st.session_state.processed_data):
                        # Adiciona o link apenas se o serviço for de manutenção
                        if record.get('tipo_servico') in ["Manutenção Nível 2", "Manutenção Nível 3"]:
                            record['link_relatorio_pdf'] = pdf_link
                        else:
                            record['link_relatorio_pdf'] = None
                        save_inspection(record)
                        progress_bar.progress((i + 1) / total_count)
                    
                    st.success("Registros salvos com sucesso!")
                    st.balloons()
                    st.session_state.batch_step = 'start'
                    st.session_state.processed_data = None
                    st.session_state.uploaded_pdf_file = None
                    st.rerun()

        # --- Aba 2: Inspeção Rápida por QR Code (com opção de digitação manual) ---
        with tab_qr:
            st.header("Verificação Rápida de Equipamento")
            st.session_state.setdefault('qr_step', 'start'); st.session_state.setdefault('qr_id', None)
            st.session_state.setdefault('qr_selo', None); st.session_state.setdefault('last_record', None)
            st.session_state.setdefault('location', None)
            
            # Pede a localização
            if st.session_state.qr_step == 'start' and st.session_state.location is None:
                with st.spinner("Aguardando permissão de localização do navegador..."):
                    loc = streamlit_js_eval(js_expressions="""
                        new Promise(function(resolve, reject) {
                            navigator.geolocation.getCurrentPosition(
                                function(position) { resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }); },
                                function(error) { resolve(null); }
                            );
                        });
                    """)
                    if loc:
                        st.session_state.location = loc
                        st.rerun()
            
            # ETAPA 1: TELA INICIAL
            if st.session_state.qr_step == 'start':
                if st.session_state.location:
                    st.success(f"📍 Localização pronta!")
                else:
                    st.error("⚠️ A geolocalização é necessária para continuar.")
    
                st.subheader("1. Identifique o Equipamento")
                
                col1, col2, col3 = st.columns([2, 0.5, 2])
                
                with col1:
                    st.info("Opção A: Leitura Rápida")
                    if st.button("📷 Escanear QR Code", type="primary", use_container_width=True, disabled=not st.session_state.location):
                        st.session_state.qr_step = 'scan'
                        st.rerun()
    
                with col2:
                    st.write("<h5 style='text-align: center; margin-top: 2.5rem;'>OU</h5>", unsafe_allow_html=True)
                
                with col3:
                    st.info("Opção B: Digitação Manual")
                    manual_id = st.text_input("Digite o ID do Equipamento", key="manual_id_input", label_visibility="collapsed", placeholder="Digite o ID aqui...")
                    if st.button("🔍 Buscar por ID", use_container_width=True, disabled=not st.session_state.location):
                        if manual_id:
                            st.session_state.qr_id = manual_id
                            st.session_state.qr_selo = None # Não há selo na digitação manual
                            st.session_state.last_record = find_last_record(load_sheet_data("extintores"), manual_id, 'numero_identificacao')
                            st.session_state.qr_step = 'inspect'
                            st.rerun()
                        else:
                            st.warning("Por favor, digite um ID para buscar.")
                
                if not st.session_state.location:
                     if st.button("🔄 Tentar Obter Localização Novamente"):
                        st.session_state.location = None
                        st.rerun()
            
            # ETAPA 2: ESCANEANDO
            if st.session_state.qr_step == 'scan':
                qr_image = st.camera_input("Aponte para o QR Code do Equipamento", key="qr_camera")
                if qr_image:
                    with st.spinner("Processando..."):
                        decoded_id, decoded_selo = decode_qr_from_image(qr_image)
                        if decoded_id:
                            st.session_state.qr_id = decoded_id; st.session_state.qr_selo = decoded_selo
                            st.success(f"QR lido! ID do Equipamento: **{decoded_id}**")
                            st.session_state.last_record = find_last_record(load_sheet_data("extintores"), decoded_id, 'numero_identificacao')
                            st.session_state.qr_step = 'inspect'; st.rerun()
                        else: st.warning("QR Code não detectado ou em formato inválido.")
                if st.button("Cancelar Leitura"):
                    st.session_state.qr_step = 'start'
                    st.rerun()
            
            # ETAPA 3: INSPEÇÃO
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
    
                    # --- LÓGICA DE FORMULÁRIO CORRIGIDA ---
                    st.subheader("Registrar Nova Inspeção (Nível 1)")
                
                    status = st.radio("Status do Equipamento:", ["Conforme", "Não Conforme"], horizontal=True, key="qr_status_radio")
                    
                    issues = []
                    if status == "Não Conforme":
                        # --- ATUALIZAÇÃO DA LISTA DE OPÇÕES AQUI ---
                        issue_options = [
                            "Lacre Violado", 
                            "Manômetro Fora de Faixa", 
                            "Dano Visível", 
                            "Obstrução", 
                            "Sinalização Inadequada", 
                            "Suporte Danificado/Faltando",  
                            "Pintura Danificada"    
                        ]
                        issues = st.multiselect(
                            "Selecione as não conformidades:", 
                            issue_options, 
                            key="qr_issues_multiselect"
                        )
                    
                    # 2. Formulário contém apenas o botão de submissão
                    with st.form("quick_inspection_form"):
                        location = st.session_state.location
                        if location: st.info(f"📍 Localização a ser registrada: Lat: {location['latitude']:.5f}, Lon: {location['longitude']:.5f}")
                        else: st.warning("⚠️ Não foi possível obter a localização.")
    
                        submitted = st.form_submit_button("✅ Confirmar e Registrar Inspeção", type="primary")
    
                        if submitted:
                            if not location:
                                st.error("Erro: A geolocalização é necessária.")
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
                                        'latitude': location['latitude'],
                                        'longitude': location['longitude']
                                    })
                                    new_record.update(calculate_next_dates(new_record['data_servico'], 'Inspeção', new_record['tipo_agente']))
                                    
                                    if save_inspection(new_record):
                                        st.success(f"Inspeção para o ID {st.session_state.qr_id} registrada!"); st.balloons()
                                        st.session_state.qr_step = 'start'; st.session_state.location = None; st.rerun()
                else:
                    st.error(f"Nenhum registro encontrado para o ID de Equipamento '{st.session_state.qr_id}'.")
                
                if st.button("Inspecionar Outro Equipamento"):
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
