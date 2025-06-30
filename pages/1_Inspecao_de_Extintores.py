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
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page

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

        # Verifica se o QR code é composto (contém '#')
        if '#' in decoded_text:
            parts = decoded_text.split('#')
            # Assumindo que o Selo INMETRO é o 4º elemento (índice 3)
            if len(parts) >= 4:
                return parts[3].strip()  # .strip() para remover espaços em branco
            else:
                st.error(f"Formato de QR Code composto inválido: {decoded_text}")
                return None
        else:
            # Se não tiver '#', assume que o dado inteiro é o selo
            return decoded_text.strip()

    except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")
        return None

def find_last_record(df, search_value, column_name):
    """Função genérica para encontrar o último registro com base em um valor e coluna."""
    if df.empty or column_name not in df.columns: return None
    # Converte ambos para string para garantir a comparação correta
    records = df[df[column_name].astype(str) == str(search_value)]
    if records.empty: return None
    if 'data_servico' in records.columns:
        records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
        records.dropna(subset=['data_servico'], inplace=True)
        if records.empty: return None
        return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
    return records.iloc[0].to_dict()

def main_inspection_page():
    st.title("Gerenciamento de Inspeções de Extintores")
    tab_batch, tab_qr = st.tabs(["Registro em Lote por PDF", "Inspeção Rápida por QR Code"])

    with tab_batch:
        # Código da aba de lote não muda
        st.header("Processar Relatório de Inspeção/Manutenção")
        if 'processed_data' not in st.session_state: st.session_state.processed_data = None
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
                            item.update(calculate_next_dates(item.get('data_servico'), service_level, item.get('tipo_agente')))
                            item['plano_de_acao'] = generate_action_plan(item)
                            processed_list.append(item)
                        st.session_state.processed_data = processed_list
                        st.success(f"{len(processed_list)} extintores encontrados!")
                    else:
                        st.error("Não foi possível extrair dados do arquivo.")
                        st.session_state.processed_data = None
        if st.session_state.processed_data:
            st.subheader("2. Confira e Salve os Dados")
            df = pd.DataFrame(st.session_state.processed_data)
            st.dataframe(df)
            if st.button("💾 Salvar Dados no Sistema", type="primary", key="batch_save_button"):
                progress_bar = st.progress(0, "Salvando...")
                total_count = len(st.session_state.processed_data)
                for i, record in enumerate(st.session_state.processed_data):
                    save_inspection(record)
                    progress_bar.progress((i + 1) / total_count, f"Salvando {i+1}/{total_count}...")
                st.success(f"{total_count} registros salvos!")
                st.balloons()
                st.session_state.processed_data = None
                st.rerun()

    with tab_qr:
        st.header("Verificação Rápida de Equipamento")
        if 'qr_id' not in st.session_state: st.session_state.qr_id = None
        qr_image = st.camera_input("Aponte a câmera para o QR Code (Selo INMETRO)", key="qr_camera")
        if qr_image:
            decoded_id = decode_qr_from_image(qr_image)
            if decoded_id:
                st.session_state.qr_id = decoded_id
                st.success(f"QR Code lido! Selo INMETRO: **{st.session_state.qr_id}**")
            else:
                st.warning("Nenhum QR Code detectado ou formato inválido.")
            st.rerun()
        if st.session_state.qr_id:
            df_full_history = load_sheet_data("extintores")
            last_record = find_last_record(df_full_history, st.session_state.qr_id, 'numero_selo_inmetro')
            if last_record:
                st.subheader(f"Extintor Encontrado - Selo: {st.session_state.qr_id}")
                with st.expander("Ver detalhes do último registro", expanded=True):
                    st.metric("ID do Cilindro", last_record.get('numero_identificacao', 'N/A'))
                    st.metric("Tipo", last_record.get('tipo_agente', 'N/A'))
                    st.metric("Próxima Inspeção", last_record.get('data_proxima_inspecao', 'N/A'))
                st.subheader("Registrar Nova Inspeção (Nível 1)")
                with st.form("quick_inspection_form"):
                    status = st.radio("Status do Extintor:", ["Conforme", "Não Conforme"], horizontal=True)
                    issues = []
                    if status == "Não Conforme":
                        issues = st.multiselect("Selecione as não conformidades:", ["Lacre Violado", "Manômetro Fora de Faixa", "Dano Visível", "Obstrução", "Sinalização Inadequada", "Pintura Danificada"])
                    if st.form_submit_button("Registrar Inspeção"):
                        with st.spinner("Registrando..."):
                            new_record = last_record.copy()
                            new_record['tipo_servico'] = "Inspeção"
                            new_record['data_servico'] = date.today().isoformat()
                            new_record['inspetor_responsavel'] = get_user_display_name()
                            new_record['aprovado_inspecao'] = "Sim" if status == "Conforme" else "Não"
                            new_record['observacoes_gerais'] = "Inspeção de rotina OK." if status == "Conforme" else ", ".join(issues)
                            new_record.update(calculate_next_dates(new_record['data_servico'], new_record['tipo_servico'], new_record['tipo_agente']))
                            new_record['plano_de_acao'] = generate_action_plan(new_record)
                            if save_inspection(new_record):
                                st.success(f"Inspeção para o selo {st.session_state.qr_id} registrada!")
                                st.balloons()
                                st.session_state.qr_id = None
                                st.rerun() 
            else:
                st.error(f"Nenhum registro encontrado para o Selo INMETRO '{st.session_state.qr_id}'.")
            if st.button("Ler outro QR Code"):
                st.session_state.qr_id = None
                st.rerun()

if not show_login_page(): st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    main_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
