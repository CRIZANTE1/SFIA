import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import HOSE_SHEET_NAME

def save_hose_inspection(record, pdf_link, user_name):
    """
    Salva um novo registro de inspeção de mangueira na planilha, 
    utilizando todos os dados extraídos pela IA.
    Calcula automaticamente a data do próximo teste.
    """
    try:
        uploader = GoogleDriveUploader()
        
        inspection_date_str = record.get('data_inspecao')
        
        try:
            inspection_date_obj = pd.to_datetime(inspection_date_str).date()
        except (ValueError, TypeError):
            st.warning(f"Data de inspeção inválida para ID {record.get('id_mangueira')}: '{inspection_date_str}'. Usando data de hoje.")
            inspection_date_obj = date.today()
            
        next_test_date = (inspection_date_obj + relativedelta(years=1)).isoformat()
        
        data_row = [
            record.get('id_mangueira'),
            record.get('marca'),
            record.get('diametro'),
            record.get('tipo'),
            record.get('comprimento'),
            record.get('ano_fabricacao'),
            inspection_date_obj.isoformat(),
            next_test_date,
            record.get('resultado'),
            pdf_link,  
            user_name, 
            record.get('empresa_executante'),
            record.get('inspetor_responsavel') 
        ]
        
        uploader.append_data_to_sheet(HOSE_SHEET_NAME, data_row)
        return True

    except Exception as e:
        st.error(f"Erro ao salvar inspeção da mangueira {record.get('id_mangueira')}: {e}")
        return False
