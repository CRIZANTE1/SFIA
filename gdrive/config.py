import os
import json
import streamlit as st

# ID da pasta no Google Drive onde os arquivos serão salvos
GDRIVE_FOLDER_ID = "1poFC4ymPbPfZvJuSBK15ClLA3xb76vwQ" # Mantenha o seu ID

# ID da sua planilha Google
GDRIVE_SHEETS_ID = "1I7plDJVUwXCKByakjxMPKDBa7in5K4MgS5YFn9gmhW0" # Mantenha o seu ID

# --- Nomes das Abas na Planilha ---
# Certifique-se de que sua planilha tenha abas com EXATAMENTE estes nomes.
ADMIN_SHEET_NAME = "adm"
EXTINGUISHER_SHEET_NAME = "extintores"
LOG_ACTIONS = "log_acoes"


def get_credentials_dict():
    """Retorna as credenciais do serviço do Google, seja do arquivo local ou do Streamlit Cloud."""
    # O resto da função continua igual, não precisa mudar.
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
