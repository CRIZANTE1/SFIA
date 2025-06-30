import streamlit as st
import pandas as pd
import cv2  # Usaremos cv2 diretamente
from datetime import date
import sys
import os
import numpy as np

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.extinguisher_operations import (
    process_extinguisher_pdf, calculate_next_dates, save_inspection, generate_action_plan
)
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page

# --- FUNÇÃO ATUALIZADA PARA USAR OPENCV ---

def decode_qr_from_image(image_file):
    """Decodifica o QR code de um arquivo de imagem usando o detector do OpenCV."""
    try:
        # Converte o arquivo de imagem para um array numpy
        file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Inicializa o detector de QR Code do OpenCV
        detector = cv2.QRCodeDetector()

        # Tenta detectar e decodificar o QR Code
        # O método retorna (texto decodificado, pontos do contorno, qrcode_binário)
        decoded_text, points, _ = detector.detectAndDecode(img)

        # O detector retorna o texto decodificado se encontrar um QR code
        if decoded_text:
            return decoded_text
            
        return None
    except Exception as e:
        st.error(f"Erro ao processar a imagem com OpenCV: {e}")
        return None

def find_last_record(df, extinguisher_id):
    """Encontra o registro mais recente de um extintor no DataFrame."""
    if df.empty or 'numero_identificacao' not in df.columns:
        return None
    extinguisher_records = df[df['numero_identificacao'] == extinguisher_id]
    if extinguisher_records.empty:
        return None
    if 'data_servico' in extinguisher_records.columns:
        extinguisher_records['data_servico'] = pd.to_datetime(extinguisher_records['data_servico'], errors='coerce')
        extinguisher_records.dropna(subset=['data_servico'], inplace=True)
        if extinguisher_records.empty:
            return None
        return extinguisher_records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
    return extinguisher_records.iloc[0].to_dict()

# --- Estrutura Principal da Página (o resto do código permanece o mesmo) ---

def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")

    tab_batch, tab_qr = st.tabs(["Registro em Lote por PDF", "Inspeção Rápida por QR Code"])

    with tab_batch:
        st.header("Processar Relatório de Inspeção/Manutenção")
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = None

        st.subheader("1. Selecione o Serviço e Faça o Upload")
        service_level_options = ["Inspeção", "Manutenção Nível 2", "Manutenção Nível 3"]
        service_level = st.selectbox("Tipo de serviço realizado:", service_level_options, key="batch_service_level")
        uploaded_pdf = st.file_uploader("Escolha o relatório PDF", type=["pdf"], key="batch_pdf_uploader")

        if uploaded_pdf:
            if st.button("🔎 Processar Arquivo com IA", key="batch_process_button"):
                with st.spinner("Analisando o documento..."):
                    extracted_list = process_extinguisher_pdf(uploaded_pdf)
                    if extracted_list:
                        processed_list = []
                        for item in extracted_list:
                            item['tipo_servico'] = service_level
                            next_dates = calculate_next_dates(item.get('data_servico'), service_level, item.get('tipo_agente'))
                            item.update(next_dates)
                            item['plano_de_acao'] = generate_action_plan(item)
                            processed_list.append(item)
                        st.session_state.processed_data = processed_list
                        st.success(f"{len(processed_list)} extintores encontrados e processados!")
                    else:
                        st.error("Não foi possível extrair dados do arquivo.")
                        st.session_state.processed_data = None
        
        if st.session_state.processed_data:
            st.subheader("2. Confira e Salve os Dados")
            st.info("Verifique a tabela abaixo. Se estiver correto, clique em 'Salvar Dados'.")
            df = pd.DataFrame(st.session_state.processed_data)
            st.dataframe(df)
            if st.button("💾 Salvar Dados no Sistema", type="primary", key="batch_save_button"):
                progress_bar = st.progress(0, "Salvando...")
                total_count = len(st.session_state.processed_data)
                for i, record in enumerate(st.session_state.processed_data):
                    save_inspection(record)
                    progress_bar.progress((i + 1) / total_count, f"Salvando {i+1}/{total_count}...")
                progress_bar.empty()
                st.success(f"{total_count} registros salvos com sucesso!")
                st.balloons()
                st.session_state.processed_data = None
                st.rerun()

    with tab_qr:
        st.header("Verificação Rápida de Equipamento")
        if 'qr_id' not in st.session_state:
            st.session_state.qr_id = None

        qr_image = st.camera_input("Aponte a câmera para o QR Code", key="qr_camera")

        if qr_image:
            decoded_id = decode_qr_from_image(qr_image)
            if decoded_id:
                st.session_state.qr_id = decoded_id
                st.success(f"QR Code lido! ID do Extintor: **{st.session_state.qr_id}**")
            else:
                st.warning("Nenhum QR Code detectado. Tente novamente.")
                st.session_state.qr_id = None
            st.rerun()

        if st.session_state.qr_id:
            df_full_history = load_sheet_data("extintores")
            last_record = find_last_record(df_full_history, st.session_state.qr_id)

            if last_record:
                st.subheader(f"Extintor Encontrado: {st.session_state.qr_id}")
                with st.expander("Ver detalhes do último registro", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Tipo", last_record.get('tipo_agente', 'N/A'))
                    col2.metric("Capacidade", last_record.get('capacidade', 'N/A'))
                    col3.metric("Próxima Inspeção", last_record.get('data_proxima_inspecao', 'N/A'))
                
                st.subheader("Registrar Nova Inspeção (Nível 1)")
                with st.form("quick_inspection_form"):
                    status = st.radio("Status do Extintor:", ["Conforme", "Não Conforme"], horizontal=True)
                    issues = []
                    if status == "Não Conforme":
                        issue_options = ["Lacre Violado", "Manômetro Fora de Faixa", "Dano Visível", "Obstrução", "Sinalização Inadequada", "Pintura Danificada"]
                        issues = st.multiselect("Selecione as não conformidades:", issue_options)

                    submitted = st.form_submit_button("Registrar Inspeção")

                    if submitted:
                        with st.spinner("Registrando..."):
                            new_record = last_record.copy()
                            new_record['tipo_servico'] = "Inspeção"
                            new_record['data_servico'] = date.today().isoformat()
                            new_record['inspetor_responsavel'] = get_user_display_name()
                            new_record['aprovado_inspecao'] = "Sim" if status == "Conforme" else "Não"
                            new_record['observacoes_gerais'] = "Inspeção de rotina OK." if status == "Conforme" else ", ".join(issues)
                            next_dates = calculate_next_dates(new_record['data_servico'], new_record['tipo_servico'], new_record['tipo_agente'])
                            new_record.update(next_dates)
                            new_record['plano_de_acao'] = generate_action_plan(new_record)

                            if save_inspection(new_record):
                                st.success(f"Inspeção para {st.session_state.qr_id} registrada!")
                                st.balloons()
                                st.session_state.qr_id = None
                                st.rerun() 
                            else:
                                st.error("Falha ao registrar a inspeção.")
            else:
                st.error(f"Nenhum registro encontrado para o ID '{st.session_state.qr_id}'.")

            if st.button("Ler outro QR Code"):
                st.session_state.qr_id = None
                st.rerun()


# --- Boilerplate de Autenticação ---
if not show_login_page():
    st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    main_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
