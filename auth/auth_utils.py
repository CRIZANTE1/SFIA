# FILE: auth/auth_utils.py

import streamlit as st
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import ADMIN_SHEET_NAME
import pandas as pd

def is_oidc_available():
    """Verifica se o login OIDC está configurado e disponível"""
    try:
        return hasattr(st.user, 'is_logged_in')
    except Exception:
        return False

def is_user_logged_in():
    """Verifica se o usuário está logado"""
    try:
        return st.user.is_logged_in
    except Exception:
        return False

def get_user_display_name():
    """Retorna o nome de exibição do usuário"""
    try:
        if hasattr(st.user, 'name'):
            return st.user.name
        elif hasattr(st.user, 'email'):
            return st.user.email
        return "Usuário"
    except Exception:
        return "Usuário"

@st.cache_data(ttl=600)
def get_admin_users_by_name():
    """
    Busca a lista de NOMES de administradores da planilha Google.
    """
    try:
        st.write("1. Tentando inicializar GoogleDriveUploader...")
        uploader = GoogleDriveUploader()
        st.write(f"2. Tentando ler dados da aba: '{ADMIN_SHEET_NAME}'")
        
        admin_data = uploader.get_data_from_sheet(ADMIN_SHEET_NAME)
        st.write(f"3. Dados recebidos da planilha: {admin_data}") # Vê o que a API retornou

        if not admin_data or len(admin_data) < 2:
            st.warning(f"Aba '{ADMIN_SHEET_NAME}' não encontrada ou vazia na planilha.")
            return []
        
        df = pd.DataFrame(admin_data[1:], columns=admin_data[0])
        st.write("4. DataFrame criado com sucesso.")

        if 'Nome' in df.columns:
            admin_list = [str(name).strip() for name in df['Nome'].dropna() if name]
            st.write(f"5. Lista de administradores encontrada: {admin_list}")
            return admin_list
        else:
            st.error(f"A aba '{ADMIN_SHEET_NAME}' precisa de uma coluna chamada 'Nome'.")
            return []
    except Exception as e:
        st.error(f"Erro ao buscar lista de administradores: {e}")
        st.exception(e) # Mostra o traceback completo do erro
        return []

def is_admin_user():
    """
    Verifica se o NOME do usuário logado atualmente está na lista de administradores.
    """
    user_name = get_user_display_name()
    if not user_name or user_name == "Usuário":
        return False
    
    admin_list = get_admin_users_by_name()
    # Compara o nome do usuário com a lista de nomes de administradores
    return user_name.strip() in admin_list



