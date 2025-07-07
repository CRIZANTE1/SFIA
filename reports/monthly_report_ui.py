import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval
from operations.history import load_sheet_data

def _generate_extinguisher_report_content(df_inspections_month, df_action_log, month, year):
    """Gera o conteúdo do relatório de EXTINTORES."""
    
    st.header(f"Relatório de Inspeções de Extintores - {month:02d}/{year}")
    st.markdown("---")

    if df_inspections_month.empty:
        st.warning("Nenhum registro de inspeção de extintor encontrado para o período.")
        return

    # Garante que a coluna de data no log de ações esteja no formato correto para comparação
    if not df_action_log.empty:
        df_action_log['data_correcao_dt'] = pd.to_datetime(df_action_log['data_correcao'], errors='coerce')

    for index, inspection in df_inspections_month.iterrows():
        ext_id = inspection['numero_identificacao']
        status = inspection['aprovado_inspecao']
        obs = inspection['observacoes_gerais']
        photo_nc_link = inspection.get('link_foto_nao_conformidade')
        inspection_date = pd.to_datetime(inspection['data_servico'])

        status_icon = "✅" if status == "Sim" else "❌"
        
        with st.container(border=True):
            st.subheader(f"{status_icon} Equipamento ID: {ext_id}")
            col1, col2 = st.columns(2)
            col1.metric("Data da Inspeção", inspection_date.strftime('%d/%m/%Y'))
            col2.metric("Status", "Conforme" if status == "Sim" else "Não Conforme")
            
            st.text_input("Observações da Inspeção:", value=obs, disabled=True, key=f"obs_{ext_id}_{index}")
            
            if status == 'Não':
                st.markdown("---")
                st.subheader("Evidência da Não Conformidade")
                if pd.notna(photo_nc_link) and photo_nc_link.strip():
                    # Usa st.markdown para inserir a imagem, que é mais robusto
                    st.markdown(f"![Foto da Não Conformidade]({photo_nc_link})")
                else:
                    st.info("Nenhuma foto de não conformidade foi anexada.")
                
                st.markdown("---")
                st.subheader("Ação Corretiva")
                
                action = pd.DataFrame() # Inicia como DataFrame vazio
                if not df_action_log.empty:
                    action = df_action_log[
                        (df_action_log['id_equipamento'].astype(str) == str(ext_id)) &
                        (df_action_log['data_correcao_dt'] >= inspection_date)
                    ].sort_values(by='data_correcao_dt')

                if not action.empty:
                    action_taken = action.iloc[0] # Pega a primeira ação corretiva após a inspeção
                    st.success("Ação Corretiva Registrada:")
                    st.text_input("Ação Realizada:", value=action_taken.get('acao_realizada', 'N/A'), disabled=True, key=f"action_{ext_id}_{index}")
                    st.text_input("Responsável:", value=action_taken.get('responsavel_acao', 'N/A'), disabled=True, key=f"resp_{ext_id}_{index}")
                    st.text_input("Data da Correção:", value=pd.to_datetime(action_taken['data_correcao_dt']).strftime('%d/%m/%Y'), disabled=True, key=f"date_{ext_id}_{index}")
                else:
                    st.error("Ação Corretiva Pendente.")

# Em: reports/monthly_report_ui.py

def _generate_extinguisher_report_content(df_inspections_month, df_action_log, month, year):
    """Gera o conteúdo do relatório de EXTINTORES."""
    
    st.header(f"Relatório de Inspeções de Extintores - {month:02d}/{year}")
    st.markdown("---")

    if df_inspections_month.empty:
        st.warning("Nenhum registro de inspeção de extintor encontrado para o período.")
        return

    if not df_action_log.empty:
        df_action_log['data_correcao_dt'] = pd.to_datetime(df_action_log['data_correcao'], errors='coerce')

    for index, inspection in df_inspections_month.iterrows():
        ext_id = inspection['numero_identificacao']
        status = inspection['aprovado_inspecao']
        obs = inspection['observacoes_gerais']
        photo_nc_link = inspection.get('link_foto_nao_conformidade')
        inspection_date = pd.to_datetime(inspection['data_servico'])

        status_icon = "✅" if status == "Sim" else "❌"
        
        with st.container(border=True):
            st.subheader(f"{status_icon} Equipamento ID: {ext_id}")
            col1, col2 = st.columns(2)
            col1.metric("Data da Inspeção", inspection_date.strftime('%d/%m/%Y'))
            col2.metric("Status", "Conforme" if status == "Sim" else "Não Conforme")
            
            st.text_input("Observações da Inspeção:", value=obs, disabled=True, key=f"obs_{ext_id}_{index}")
            
            if status == 'Não':
                st.markdown("---")
                st.subheader("Evidência da Não Conformidade")
                if pd.notna(photo_nc_link) and photo_nc_link.strip():
                    # Tenta exibir a imagem, mas também fornece o link como fallback
                    st.image(photo_nc_link, caption="Foto da Não Conformidade", width=300)
                    st.markdown(f"**Link da Evidência:** [Abrir Foto]({photo_nc_link})") # <-- ADICIONADO AQUI
                else:
                    st.info("Nenhuma foto de não conformidade foi anexada.")
                
                st.markdown("---")
                st.subheader("Ação Corretiva")
                
                action = pd.DataFrame()
                if not df_action_log.empty:
                    action = df_action_log[
                        (df_action_log['id_equipamento'].astype(str) == str(ext_id)) &
                        (df_action_log['data_correcao_dt'] >= inspection_date)
                    ].sort_values(by='data_correcao_dt')

                if not action.empty:
                    action_taken = action.iloc[0]
                    photo_action_link = action_taken.get('link_foto_evidencia') # <-- ADICIONADO AQUI
                    
                    st.success("Ação Corretiva Registrada:")
                    st.text_input("Ação Realizada:", value=action_taken.get('acao_realizada', 'N/A'), disabled=True, key=f"action_{ext_id}_{index}")
                    st.text_input("Responsável:", value=action_taken.get('responsavel_acao', 'N/A'), disabled=True, key=f"resp_{ext_id}_{index}")
                    st.text_input("Data da Correção:", value=pd.to_datetime(action_taken['data_correcao_dt']).strftime('%d/%m/%Y'), disabled=True, key=f"date_{ext_id}_{index}")
                    
                    # Exibe o link da foto da ação corretiva
                    if pd.notna(photo_action_link) and photo_action_link.strip(): 
                        st.image(photo_action_link, caption="Foto da Ação Corretiva", width=300) 
                        st.markdown(f"**Link da Evidência da Correção:** [Abrir Foto]({photo_action_link})") 
                    else:
                        st.info("Nenhuma foto de evidência da correção foi anexada.")
                else:
                    st.error("Ação Corretiva Pendente.")
                #  _generate_hose_report_content(...) aqui.
