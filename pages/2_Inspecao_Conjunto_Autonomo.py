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
from utils.prompts import get_scba_inspection_prompt, get_air_quality_prompt 
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config

set_page_config()
pdf_qa = PDFQA()
uploader = GoogleDriveUploader() 

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
        st.header("Registrar Laudo de Qualidade do Ar e Associar a Cilindros")
        
        st.session_state.setdefault('airq_step', 'start')
        st.session_state.setdefault('airq_processed_data', None)
        st.session_state.setdefault('airq_uploaded_pdf', None)
        st.session_state.setdefault('airq_pdf_link', None)

        st.subheader("1. Faça o Upload do Laudo PDF")
        uploaded_pdf = st.file_uploader("Escolha o laudo de qualidade do ar", type=["pdf"], key="airq_pdf_uploader")
        if uploaded_pdf:
            st.session_state.airq_uploaded_pdf = uploaded_pdf
        
        if st.session_state.airq_uploaded_pdf and st.button("🔎 Analisar Laudo de Ar com IA"):
            with st.spinner("Analisando o laudo com IA..."):
                prompt = get_air_quality_prompt()
                extracted_data = pdf_qa.extract_structured_data(st.session_state.airq_uploaded_pdf, prompt)
                
                if extracted_data and "laudo" in extracted_data:
                    st.session_state.airq_processed_data = extracted_data["laudo"]
                    st.session_state.airq_step = 'confirm_and_upload'
                    st.rerun()
                else:
                    st.error("A IA não conseguiu extrair os dados do laudo.")

        if st.session_state.airq_step == 'confirm_and_upload':
            with st.spinner("Salvando PDF no Google Drive..."):
                data = st.session_state.airq_processed_data
                pdf_name = f"Laudo_Qualidade_Ar_{data.get('data_ensaio')}.pdf"
                pdf_link = uploader.upload_file(st.session_state.airq_uploaded_pdf, novo_nome=pdf_name)
                
                if pdf_link:
                    st.session_state.airq_pdf_link = pdf_link
                    st.session_state.airq_step = 'associate'
                    st.rerun()
                else:
                    st.error("Falha ao fazer o upload do laudo para o Google Drive.")
                    st.session_state.airq_step = 'start'

        if st.session_state.airq_step == 'associate':
            data = st.session_state.airq_processed_data
            st.subheader("2. Confira os Dados Extraídos")
            st.metric("Data do Ensaio", data.get('data_ensaio', 'N/A'))
            st.metric("Resultado", data.get('resultado_geral', 'N/A'))
            
            st.subheader("3. Associe o Laudo aos Cilindros")
            st.info("Selecione todos os conjuntos autônomos que são abastecidos por este compressor/fonte de ar.")
            
            try:
                df_scba = load_sheet_data(SCBA_SHEET_NAME)
                df_equipment_only = df_scba.dropna(subset=['numero_serie_equipamento'])
                
                options = df_equipment_only['numero_serie_equipamento'].tolist()
                
                selected_cylinders = st.multiselect(
                    "Selecione os Números de Série dos Equipamentos:",
                    options=options,
                    default=options 
                )

                if st.button("✅ Confirmar Associação", type="primary", use_container_width=True):
                    if not selected_cylinders:
                        st.warning("Nenhum cilindro selecionado.")
                    else:
                        with st.spinner("Atualizando registros na planilha..."):
                            update_values = [
                                data.get('data_ensaio'),
                                data.get('resultado_geral'),
                                data.get('observacoes'),
                                st.session_state.airq_pdf_link
                            ]
                            
                            header = df_scba[0]
                            col_index = header.index('numero_serie_equipamento') 
                            
                            rows_to_update = []
                            for i, row in enumerate(df_scba[1:], start=2): 
                                if row[col_index] in selected_cylinders:
                                    rows_to_update.append(i)
                            
                            update_requests = []
                            for row_num in rows_to_update:
                                range_name = f"S{row_num}:V{row_num}" 
                                uploader.update_cells(SCBA_SHEET_NAME, range_name, [update_values])
                            
                            st.success(f"{len(rows_to_update)} registros de conjuntos autônomos foram atualizados com o novo laudo de ar!")
                            
                            st.session_state.airq_step = 'start'
                            st.session_state.airq_processed_data = None
                            st.session_state.airq_uploaded_pdf = None
                            st.session_state.airq_pdf_link = None
                            st.cache_data.clear()
                            st.rerun()

            except Exception as e:
                st.error(f"Ocorreu um erro ao carregar os dados dos cilindros: {e}")
                st.exception(e)
                st.session_state.airq_step = 'start'


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
