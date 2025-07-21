import streamlit as st
import json
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import SHELTER_SHEET_NAME

def save_shelter_inventory(shelter_id, client, items_dict):
    """
    Salva o inventário de um novo abrigo de emergência na planilha.
    Converte o dicionário de itens em uma string JSON para armazenamento.
    """
    try:
        uploader = GoogleDriveUploader()
        
        # Converte o dicionário de itens para uma string JSON
        items_json_string = json.dumps(items_dict, ensure_ascii=False)
        
        # Prepara a linha de dados
        data_row = [
            shelter_id,
            client,
            items_json_string
        ]
        
        uploader.append_data_to_sheet(SHELTER_SHEET_NAME, data_row)
        return True

    except Exception as e:
        st.error(f"Erro ao salvar inventário do abrigo {shelter_id}: {e}")
        return False
