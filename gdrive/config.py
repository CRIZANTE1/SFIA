import os
import json
import streamlit as st

GDRIVE_FOLDER_ID = "1poFC4ymPbPfZvJuSBK15ClLA3xb76vwQ"

GDRIVE_SHEETS_ID = "1I7plDJVUwXCKByakjxMPKDBa7in5K4MgS5YFn9gmhW0" 

ADMIN_SHEET_NAME = "adm"
EXTINGUISHER_SHEET_NAME = "extintores"
LOG_ACTIONS = "log_acoes"
HOSE_SHEET_NAME = "mangueiras"
SHELTER_SHEET_NAME = "abrigos"
INSPECTIONS_SHELTER_SHEET_NAME = "inspecoes_abrigos"
LOG_SHELTER_SHEET_NAME = "log_abrigos"
SCBA_SHEET_NAME = "conjuntos_autonomos"
SCBA_VISUAL_INSPECTIONS_SHEET_NAME = "inspecoes_scba"
LOG_SCBA_SHEET_NAME = "log_scba"

def get_credentials_dict():
    """Retorna as credenciais do serviço do Google, seja do arquivo local ou do Streamlit Cloud."""
    if st.runtime.exists():
        try:
            return {
                "type": st.secrets.connections.gsheets.type,
                "project_id": st.secrets.connections.gsheets.project_id,
                "private_key_id": st.secrets.connections.gsheets.private_key_id,
                "private_key": st.secrets.connections.gsheets.private_key,
                "client_email": st.secrets.connections.gsheets.client_email,
                "client_id": st.secrets.connections.gsheets.client_id,
                "auth_uri": st.secrets.connections.gsheets.auth_uri,
                "token_uri": st.secrets.connections.gsheets.token_uri,
                "auth_provider_x509_cert_url": st.secrets.connections.gsheets.auth_provider_x509_cert_url,
                "client_x509_cert_url": st.secrets.connections.gsheets.client_x509_cert_url,
                "universe_domain": st.secrets.connections.gsheets.universe_domain
            }
        except Exception as e:
            st.error("Erro ao carregar credenciais do Google do Streamlit Secrets. Certifique-se de que as credenciais estão configuradas corretamente em [connections.gsheets].")
            raise e
    else:
        credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
        try:
            with open(credentials_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar credenciais do arquivo local: {str(e)}")
            raise e
