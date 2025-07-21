import streamlit as st
import pandas as pd
import sys
import os
from datetime import date

# Adiciona o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports necessários para o novo fluxo
from operations.hose_operations import save_hose_inspection
from operations.shelter_operations import save_shelter_inventory 
from gdrive.gdrive_upload import GoogleDriveUploader
from AI.api_Operation import PDFQA
from utils.prompts import get_hose_inspection_prompt, get_shelter_inventory_prompt
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config

set_page_config()
pdf_qa = PDFQA()

def show_hose_and_shelter_page():
    st.title("💧 Gestão de Mangueiras e Abrigos de Incêndio")

    tab_hoses, tab_shelters = st.tabs([
        "Inspeção de Mangueiras com IA", 
        "Cadastro de Abrigos de Emergência"
    ])

    with tab_hoses:
        st.header("Registrar Teste Hidrostático de Mangueiras")
        
        st.session_state.setdefault('hose_step', 'start')
        st.session_state.setdefault('hose_processed_data', None)
        st.session_state.setdefault('hose_uploaded_pdf', None)

        st.subheader("1. Faça o Upload do Certificado de Teste")
        st.info("O sistema analisará o PDF, extrairá os dados de todas as mangueiras e preparará os registros para salvamento.")
        
        uploaded_pdf = st.file_uploader("Escolha o certificado PDF", type=["pdf"], key="hose_pdf_uploader")
        if uploaded_pdf:
            st.session_state.hose_uploaded_pdf = uploaded_pdf
        
        if st.session_state.hose_uploaded_pdf and st.button("🔎 Analisar Certificado com IA"):
            with st.spinner("Analisando o documento..."):
                prompt = get_hose_inspection_prompt()
                extracted_data = pdf_qa.extract_structured_data(st.session_state.hose_uploaded_pdf, prompt)
                
                if extracted_data and "mangueiras" in extracted_data and isinstance(extracted_data["mangueiras"], list):
                    st.session_state.hose_processed_data = extracted_data["mangueiras"]
                    st.session_state.hose_step = 'confirm'
                    st.rerun()
                else:
                    st.error("A IA não conseguiu extrair os dados no formato esperado. Verifique o documento.")
                    st.json(extracted_data)
        
        if st.session_state.hose_step == 'confirm' and st.session_state.hose_processed_data:
            # ... (código do passo de confirmação, sem alterações)
            st.subheader("2. Confira os Dados Extraídos e Salve no Sistema")
            st.dataframe(pd.DataFrame(st.session_state.hose_processed_data))
            
            if st.button("💾 Confirmar e Salvar Registros", type="primary", use_container_width=True):
                with st.spinner("Salvando registros..."):
                    uploader = GoogleDriveUploader()
                    pdf_name = f"Certificado_Mangueiras_{date.today().isoformat()}_{st.session_state.hose_uploaded_pdf.name}"
                    pdf_link = uploader.upload_file(st.session_state.hose_uploaded_pdf, novo_nome=pdf_name)
                    
                    if not pdf_link:
                        st.error("Falha ao fazer o upload do certificado. Os dados não foram salvos.")
                        st.stop()
                    
                    total_count = len(st.session_state.hose_processed_data)
                    progress_bar = st.progress(0, "Salvando...")
                    
                    for i, record in enumerate(st.session_state.hose_processed_data):
                        save_hose_inspection(record=record, pdf_link=pdf_link, user_name=get_user_display_name())
                        progress_bar.progress((i + 1) / total_count)
                    
                    st.success(f"{total_count} registros de mangueiras salvos com sucesso!")
                    st.balloons()
                    
                    st.session_state.hose_step = 'start'
                    st.session_state.hose_processed_data = None
                    st.session_state.hose_uploaded_pdf = None
                    st.cache_data.clear()
                    st.rerun()

    with tab_shelters:
        st.header("Cadastrar Abrigos de Emergência com IA")
        
        # Gerenciamento de estado para a aba de abrigos
        st.session_state.setdefault('shelter_step', 'start')
        st.session_state.setdefault('shelter_processed_data', None)
        st.session_state.setdefault('shelter_uploaded_pdf', None)

        st.subheader("1. Faça o Upload do Inventário PDF")
        st.info("O sistema analisará o PDF, extrairá os dados de todos os abrigos e preparará os registros para salvamento.")
        
        uploaded_pdf_shelter = st.file_uploader(
            "Escolha o inventário PDF", 
            type=["pdf"], 
            key="shelter_pdf_uploader"
        )
        if uploaded_pdf_shelter:
            st.session_state.shelter_uploaded_pdf = uploaded_pdf_shelter
        
        if st.session_state.shelter_uploaded_pdf and st.button("🔎 Analisar Inventário com IA", key="shelter_analyze_btn"):
            with st.spinner("Analisando o documento..."):
                prompt = get_shelter_inventory_prompt() # <-- Usando o novo prompt
                extracted_data = pdf_qa.extract_structured_data(st.session_state.shelter_uploaded_pdf, prompt)
                
                if extracted_data and "abrigos" in extracted_data and isinstance(extracted_data["abrigos"], list):
                    st.session_state.shelter_processed_data = extracted_data["abrigos"]
                    st.session_state.shelter_step = 'confirm'
                    st.rerun()
                else:
                    st.error("A IA não conseguiu extrair os dados no formato esperado. Verifique o documento.")
                    st.json(extracted_data)
        
        if st.session_state.shelter_step == 'confirm' and st.session_state.shelter_processed_data:
            st.subheader("2. Confira os Dados Extraídos e Salve no Sistema")
            
            for abrigo in st.session_state.shelter_processed_data:
                with st.expander(f"**Abrigo ID:** {abrigo.get('id_abrigo')} | **Cliente:** {abrigo.get('cliente')}"):
                    st.json(abrigo.get('itens', {}))

            if st.button("💾 Confirmar e Salvar Abrigos", type="primary", use_container_width=True):
                with st.spinner("Salvando registros dos abrigos..."):
                    total_count = len(st.session_state.shelter_processed_data)
                    progress_bar = st.progress(0, "Salvando...")
                    
                    for i, record in enumerate(st.session_state.shelter_processed_data):
                        save_shelter_inventory(
                            shelter_id=record.get('id_abrigo'),
                            client=record.get('cliente'),
                            items_dict=record.get('itens', {})
                        )
                        progress_bar.progress((i + 1) / total_count)
                    
                    st.success(f"{total_count} abrigos salvos com sucesso!")
                    st.balloons()
                    
                    # Limpar o estado para um novo upload
                    st.session_state.shelter_step = 'start'
                    st.session_state.shelter_processed_data = None
                    st.session_state.shelter_uploaded_pdf = None
                    st.cache_data.clear()
                    st.rerun()

if not show_login_page(): 
    st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_hose_and_shelter_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
