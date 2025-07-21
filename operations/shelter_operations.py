import streamlit as st
import json
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import SHELTER_SHEET_NAME, INSPECTIONS_SHELTER_SHEET_NAME, LOG_SHELTER_SHEET_NAME
from datetime import date 
from dateutil.relativedelta import relativedelta 
def save_shelter_inventory(shelter_id, client, items_dict):
    """
    Salva o inventário de um novo abrigo de emergência na planilha.
    Converte o dicionário de itens em uma string JSON para armazenamento.
    """
    try:
        uploader = GoogleDriveUploader()
        items_json_string = json.dumps(items_dict, ensure_ascii=False)
        data_row = [shelter_id, client, items_json_string]
        uploader.append_data_to_sheet(SHELTER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar inventário do abrigo {shelter_id}: {e}")
        return False

def save_shelter_inspection(shelter_id, overall_status, inspection_results, inspector_name):
    """
    Salva o resultado de uma inspeção de abrigo e calcula a próxima data de inspeção.
    """
    try:
        uploader = GoogleDriveUploader()
        today = date.today()
        next_inspection_date = (today + relativedelta(months=3)).isoformat()
        results_json_string = json.dumps(inspection_results, ensure_ascii=False)
        data_row = [
            today.isoformat(),
            shelter_id,
            overall_status,
            results_json_string,
            inspector_name,
            next_inspection_date
        ]
        uploader.append_data_to_sheet(INSPECTIONS_SHELTER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar inspeção do abrigo {shelter_id}: {e}")
        return False

def save_shelter_action_log(shelter_id, problem, action_taken, responsible):
    """
    Salva um registro de ação corretiva para um abrigo no log.
    """
    try:
        uploader = GoogleDriveUploader()
        data_row = [
            date.today().isoformat(),
            shelter_id,
            problem,
            action_taken,
            responsible
        ]
        uploader.append_data_to_sheet(LOG_SHELTER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar log de ação para o abrigo {shelter_id}: {e}")
        return False
