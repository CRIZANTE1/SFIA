# FILE: pages/1a_Inspecao_de_Mangueiras.py

import streamlit as st
import sys
import os
from datetime import date

# Adiciona o diretório raiz ao path para encontrar os outros módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.hose_operations import save_hose_inspection
from gdrive.gdrive_upload import GoogleDriveUploader
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config

set_page_config()

def show_hose_inspection_page():
    """Exibe a interface para registrar a inspeção de mangueiras."""
    st.title("💧 Inspeção Anual de Mangueiras de Incêndio")
    st.info(
        "Esta seção é para registrar o teste hidrostático anual de mangueiras. "
        "Basta fornecer o ID da mangueira, fazer o upload do certificado PDF e registrar."
    )

    with st.form("hose_inspection_form", clear_on_submit=True):
        hose_id = st.text_input("**ID da Mangueira (Ex: 'H-01', 'Abrigo 10')**", key="hose_id")
        certificate_pdf = st.file_uploader(
            "**Faça o upload do Certificado de Teste Hidrostático (PDF)**",
            type=["pdf"],
            key="hose_pdf_uploader"
        )
        
        submitted = st.form_submit_button("💾 Registrar Inspeção", type="primary", use_container_width=True)
        
        if submitted:
            if not hose_id or not certificate_pdf:
                st.error("Por favor, preencha o ID da mangueira e anexe o certificado.")
            else:
                with st.spinner(f"Processando registro para a mangueira '{hose_id}'..."):
                    # 1. Fazer o upload do certificado para o Google Drive
                    uploader = GoogleDriveUploader()
                    pdf_name = f"Certificado_Mangueira_{hose_id}_{date.today().isoformat()}.pdf"
                    pdf_link = uploader.upload_file(certificate_pdf, novo_nome=pdf_name)
                    
                    if pdf_link:
                        # 2. Preparar os dados para salvar na planilha
                        inspection_data = {
                            'id_mangueira': hose_id,
                            'data_inspecao': date.today(),
                            'link_certificado_pdf': pdf_link,
                            'inspetor_responsavel': get_user_display_name()
                        }
                        
                        # 3. Salvar os dados na planilha
                        if save_hose_inspection(inspection_data):
                            st.success(f"Inspeção da mangueira '{hose_id}' registrada com sucesso!")
                            st.balloons()
                            st.cache_data.clear() # Limpa o cache para atualizar outros dashboards
                        else:
                            st.error("Falha ao salvar os dados na planilha.")
                    else:
                        st.error("Falha ao fazer o upload do certificado para o Google Drive.")

# --- Boilerplate de Autenticação ---
if not show_login_page(): 
    st.stop()
show_user_header()
show_logout_button()
if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_hose_inspection_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
