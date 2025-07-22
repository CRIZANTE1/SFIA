import streamlit as st
import pandas as pd
import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.scba_operations import save_scba_inspection
from gdrive.gdrive_upload import GoogleDriveUploader
from AI.api_Operation import PDFQA
from utils.prompts import get_scba_inspection_prompt, get_air_quality_prompt 
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config

set_page_config()
pdf_qa = PDFQA()

def show_scba_inspection_page():
    st.title("💨 Inspeção de Conjuntos Autônomos (SCBA)")

    tab_test_scba, tab_quality_air = st.tabs([
        "Teste de Equipamentos (Posi3)",
        "Laudo de Qualidade do Ar"
    ])
    with tab_test_scba:
        st.header("Registrar Teste de SCBA com IA")
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
                    
                    st.session_state.scba_step = 'start'
                    st.session_state.scba_processed_data = None
                    st.session_state.scba_uploaded_pdf = None
                    st.cache_data.clear()
                    st.rerun()



    with tab_quality_air:
        st.header("Registrar Laudo de Qualidade do Ar com IA")
        st.session_state.setdefault('airq_step', 'start')
        st.session_state.setdefault('airq_processed_data', None)
        st.session_state.setdefault('airq_uploaded_pdf', None)
        uploader = GoogleDriveUploader()

        st.subheader("1. Faça o Upload do Laudo PDF")
        st.info("A IA analisará o laudo, extrairá os dados e criará um registro para cada cilindro mencionado.")
        
        uploaded_pdf_airq = st.file_uploader("Escolha o laudo de qualidade do ar", type=["pdf"], key="airq_pdf_uploader")
        if uploaded_pdf_airq:
            st.session_state.airq_uploaded_pdf = uploaded_pdf_airq
        
        if st.session_state.airq_uploaded_pdf and st.button("🔎 Analisar Laudo de Ar com IA"):
            with st.spinner("Analisando o laudo com IA..."):
                prompt = get_air_quality_prompt()
                extracted_data = pdf_qa.extract_structured_data(st.session_state.airq_uploaded_pdf, prompt)
                if extracted_data and "laudo" in extracted_data:
                    st.session_state.airq_processed_data = extracted_data["laudo"]
                    st.session_state.airq_step = 'confirm'
                    st.rerun()
                else:
                    st.error("A IA não conseguiu extrair os dados do laudo.")
        
        if st.session_state.airq_step == 'confirm' and st.session_state.airq_processed_data:
            data = st.session_state.airq_processed_data
            st.subheader("2. Confira os Dados e Salve")
            st.metric("Resultado do Laudo", data.get('resultado_geral', 'N/A'))
            cilindros = data.get('cilindros', [])
            st.info(f"O laudo será aplicado aos seguintes cilindros: {', '.join(cilindros)}")
            
            if st.button("💾 Confirmar e Registrar Laudo", type="primary", use_container_width=True):
                with st.spinner("Processando e salvando..."):
                    pdf_name = f"Laudo_Ar_{data.get('data_ensaio')}_{st.session_state.airq_uploaded_pdf.name}"
                    pdf_link = uploader.upload_file(st.session_state.airq_uploaded_pdf, novo_nome=pdf_name)
                    
                    if pdf_link:
                        cilindros = data.get('cilindros', [])
                        if not cilindros:
                            st.error("Não é possível salvar, pois nenhum cilindro foi identificado no laudo.")
                        else:
                            for cilindro_sn in cilindros:
                                data_row = [None] * 18
                                data_row[2] = cilindro_sn # Coluna C: numero_serie_equipamento
                                
                                data_row.extend([
                                    data.get('data_ensaio'),
                                    data.get('resultado_geral'),
                                    data.get('observacoes'),
                                    pdf_link 
                                ])
                                uploader.append_data_to_sheet(SCBA_SHEET_NAME, data_row)
                            
                            st.success(f"Laudo de qualidade do ar registrado com sucesso para {len(cilindros)} cilindros!")
                            
                            st.session_state.airq_step = 'start'
                            st.session_state.airq_processed_data = None
                            st.session_state.airq_uploaded_pdf = None
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.error("Falha no upload do PDF para o Google Drive. Nenhum dado foi salvo.")


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
