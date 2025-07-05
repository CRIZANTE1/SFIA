import streamlit as st
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader

def upload_evidence_photo(photo_file, id_equipamento, photo_type="nao_conformidade"):
    """
    Faz o upload de uma foto de evidência para o Google Drive e retorna o link.
    
    Args:
        photo_file: O objeto de arquivo do Streamlit (st.camera_input).
        id_equipamento (str): O ID do equipamento para nomear o arquivo.
        photo_type (str): "nao_conformidade" ou "acao_corretiva".
    
    Returns:
        str or None: A URL da foto no Google Drive ou None se falhar.
    """
    if not photo_file:
        return None

    try:
        uploader = GoogleDriveUploader()
        # Cria um nome de arquivo único e descritivo
        file_name = f"FOTO_{photo_type.upper()}_ID_{id_equipamento}_{date.today().isoformat()}.jpg"
        
        # Faz o upload e obtém o link
        photo_link = uploader.upload_file(photo_file, novo_nome=file_name)
        st.success(f"Foto de evidência ({photo_type}) salva no Google Drive!")
        return photo_link
        
    except Exception as e:
        st.error(f"Falha ao fazer upload da foto de evidência: {e}")
        return None

