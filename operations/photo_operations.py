# Arquivo: operations/photo_operations.py

import streamlit as st
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader

def upload_evidence_photo(photo_file, id_equipamento, photo_type="nao_conformidade"):
    """
    Faz o upload de uma foto de evidência para o Google Drive e retorna o LINK DIRETO.
    
    Args:
        photo_file: O objeto de arquivo do Streamlit (st.camera_input ou st.file_uploader).
        id_equipamento (str): O ID do equipamento para nomear o arquivo.
        photo_type (str): "nao_conformidade" ou "acao_corretiva".
    
    Returns:
        str or None: A URL direta da foto no Google Drive ou None se falhar.
    """
    if not photo_file:
        return None

    try:
        uploader = GoogleDriveUploader()
        file_name = f"FOTO_{photo_type.upper()}_ID_{id_equipamento}_{date.today().isoformat()}.jpg"
        
        photo_link = uploader.upload_image_and_get_direct_link(photo_file, novo_nome=file_name)
        
        if photo_link:
            st.success(f"Foto de evidência ({photo_type}) salva no Google Drive!")
        
        return photo_link
        
    except Exception as e:
        st.error(f"Falha ao fazer upload da foto de evidência: {e}")
        return None

