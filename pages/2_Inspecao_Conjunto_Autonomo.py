import streamlit as st
import pandas as pd
import sys
import os
from datetime import date

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.scba_operations import save_scba_inspection
from gdrive.gdrive_upload import GoogleDriveUploader
from AI.api_Operation import PDFQA
from utils.prompts import get_scba_inspection_prompt
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config

set_page_config()
pdf_qa = PDFQA()

def show_scba_inspection_page():
    st.title("💨 Inspeção de Conjuntos Autônomos (SCBA)")
    
    st.session_state.setdefault('scba_step', 'start')
    st.session_state.setdefault('scba_processed_data', None)
    st.session_state.setdefault('scba_uploaded_pdf', None)

    st.subheader("1. Faça o Upload do Relatório de Teste Posi3")
    st.info("O sistema analisará o PDF, extrairá os dados de todos os equipamentos listados e preparará os registros para salvamento.")
    
    uploaded_pdf = st.file_uploader("Escolha o relatório PDF", type=["pdf"], key="scba_pdf_uploader")
    if uploaded_pdf:
        st.session_state.scba_uploaded_pdf = uploaded_pdf
    
    if st.session_state.scba_uploaded_pdf and st.button("🔎 Analisar Relatório com IA"):
        with st.spinner("Analisando o documento com IA..."):
            prompt = get_scba_inspection_prompt()
            extracted_data = pdf_qa.extract_structured_data(st.session_state.scba_uploaded_pdf, prompt)
            
            if extracted_data and "scbas" in extracted_data and isinstance(extracted_data["scbas"], list):
                st.session_state.scba_processed_data = extracted_data["scbas"]
                st.session_state.scba_step = 'confirm'
                st.rerun()
            else:
                st.error("A IA não conseguiu extrair os dados no formato esperado. Verifique o documento.")
                st.json(extracted_data)
    
    if st.session_state.scba_step == 'confirm' and st.session_state.scba_processed_data:
        st.subheader("2. Confira os Dados Extraídos e Salve no Sistema")
        st.dataframe(pd.DataFrame(st.session_state.scba_processed_data))
        
        if st.button("💾 Confirmar e Salvar Registros", type="primary", use_container_width=True):
            with st.spinner("Salvando registros..."):
                uploader = GoogleDriveUploader()
                pdf_name = f"Relatorio_SCBA_{date.today().isoformat()}_{st.session_state.scba_uploaded_pdf.name}"
                pdf_link = uploader.upload_file(st.session_state.scba_uploaded_pdf, novo_nome=pdf_name)
                
                if not pdf_link:
                    st.error("Falha ao fazer o upload do relatório. Os dados não foram salvos.")
                    st.stop()
                
                total_count = len(st.session_state.scba_processed_data)
                progress_bar = st.progress(0, "Salvando...")
                
                for i, record in enumerate(st.session_state.scba_processed_data):
                    save_scba_inspection(record=record, pdf_link=pdf_link, user_name=get_user_display_name())
                    progress_bar.progress((i + 1) / total_count)
                
                st.success(f"{total_count} registros de SCBA salvos com sucesso!")
                #st.balloons()
                
                st.session_state.scba_step = 'start'
                st.session_state.scba_processed_data = None
                st.session_state.scba_uploaded_pdf = None
                st.cache_data.clear()
                st.rerun()

# --- Boilerplate de Autenticação ---
if not show_login_page(): 
    st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_scba_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
