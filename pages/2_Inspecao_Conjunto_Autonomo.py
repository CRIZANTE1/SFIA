import streamlit as st
import pandas as pd
import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.scba_operations import save_scba_inspection, save_scba_visual_inspection
from gdrive.gdrive_upload import GoogleDriveUploader
from AI.api_Operation import PDFQA
from utils.prompts import get_scba_inspection_prompt, get_air_quality_prompt 
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user, get_user_display_name
from operations.demo_page import show_demo_page
from config.page_config import set_page_config
from operations.history import load_sheet_data
from gdrive.config import SCBA_SHEET_NAME, SCBA_VISUAL_INSPECTIONS_SHEET_NAME


set_page_config()
pdf_qa = PDFQA()

def show_scba_inspection_page():
    st.title("💨 Inspeção de Conjuntos Autônomos (SCBA)")

    tab_test_scba, tab_quality_air, tab3 = st.tabs([
        "Teste de Equipamentos (Posi3)",
        "Laudo de Qualidade do Ar",
        "Inspeção Visual Periódica"
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


    with tab3:
        st.header("Realizar Inspeção Periódica de SCBA")
        st.info("Esta inspeção inclui a verificação visual dos componentes e os testes funcionais de vedação e alarme.")
        
        df_scba = load_sheet_data(SCBA_SHEET_NAME)
        if not df_scba.empty:
            equipment_list = df_scba.dropna(subset=['numero_serie_equipamento'])['numero_serie_equipamento'].unique().tolist()
        else:
            equipment_list = []

        if not equipment_list:
            st.warning("Nenhum equipamento SCBA cadastrado. Registre um teste na primeira aba para começar.")
        else:
            options = ["Selecione um equipamento..."] + sorted(equipment_list)
            selected_scba_id = st.selectbox("Selecione o Equipamento para Inspecionar", options, key="scba_visual_select")

            if selected_scba_id != "Selecione um equipamento...":
                # Define os itens do checklist
                cilindro_items = ["Integridade Cilindro", "Registro e Valvulas", "Manômetro do Cilindro", "Pressão Manômetro", "Mangueiras e Conexões", "Correias/ Tirantes e Alças"]
                mascara_items = ["Integridade da Máscara", "Visor ou Lente", "Borrachas de Vedação", "Conector da válvula de Inalação", "Correias/ Tirantes", "Fivelas e Alças", "Válvula de Exalação"]

                with st.form(key=f"visual_insp_{selected_scba_id}", clear_on_submit=True):
                    results = {"Cilindro": {}, "Mascara": {}, "Testes Funcionais": {}}
                    has_issues = False

                    st.subheader("Testes Funcionais")
                    
                    teste_estanqueidade = st.radio("1. Teste de Estanqueidade (Vedação Alta Pressão)", ["Aprovado", "Reprovado"], horizontal=True, help="Queda de pressão < 10 bar em 1 minuto?")
                    results["Testes Funcionais"]["Estanqueidade Alta Pressão"] = teste_estanqueidade
                    if teste_estanqueidade == "Reprovado": has_issues = True
                    
                    teste_alarme = st.radio("2. Teste do Alarme Sonoro de Baixa Pressão", ["Aprovado", "Reprovado"], horizontal=True, help="Alarme soou entre 50-55 bar?")
                    results["Testes Funcionais"]["Alarme de Baixa Pressão"] = teste_alarme
                    if teste_alarme == "Reprovado": has_issues = True

                    teste_vedacao_mascara = st.radio("3. Teste de Vedação da Peça Facial (Pressão Negativa)", ["Aprovado", "Reprovado"], horizontal=True, help="Máscara colou no rosto sem vazamentos?")
                    results["Testes Funcionais"]["Vedação da Máscara"] = teste_vedacao_mascara
                    if teste_vedacao_mascara == "Reprovado": has_issues = True

                    st.markdown("---")

                    st.subheader("Inspeção Visual dos Componentes")

                    st.markdown("**Item 1.0 - Cilindro de Ar**")
                    for item in cilindro_items:
                        cols = st.columns([3, 2])
                        with cols[0]: st.write(item)
                        with cols[1]:
                            status = st.radio("Status", ["C", "N/C", "N/A"], key=f"cil_{item}", horizontal=True, label_visibility="collapsed")
                            results["Cilindro"][item] = status
                            if status == "N/C": has_issues = True
                    results["Cilindro"]["Observações"] = st.text_area("Observações - Cilindro de Ar", key="obs_cilindro")

                    st.markdown("**Item 2.0 - Máscara Facial**")
                    for item in mascara_items:
                        cols = st.columns([3, 2])
                        with cols[0]: st.write(item)
                        with cols[1]:
                            status = st.radio("Status", ["C", "N/C", "N/A"], key=f"masc_{item}", horizontal=True, label_visibility="collapsed")
                            results["Mascara"][item] = status
                            if status == "N/C": has_issues = True
                    results["Mascara"]["Observações"] = st.text_area("Observações - Máscara Facial", key="obs_mascara")
                    
                    submitted = st.form_submit_button("✅ Salvar Inspeção Completa", type="primary", use_container_width=True)

                    if submitted:
                        overall_status = "Reprovado com Pendências" if has_issues else "Aprovado"
                        with st.spinner("Salvando inspeção..."):
                            if save_scba_visual_inspection(selected_scba_id, overall_status, results, get_user_display_name()):
                                st.success(f"Inspeção periódica para o SCBA '{selected_scba_id}' salva com sucesso!")
                                st.cache_data.clear()
                            else:
                                st.error("Ocorreu um erro ao salvar a inspeção.")




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
