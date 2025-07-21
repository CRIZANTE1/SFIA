import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import HOSE_SHEET_NAME

def save_hose_inspection(data):
    """
    Salva um novo registro de inspeção de mangueira na planilha.
    Calcula automaticamente a data do próximo teste.
    """
    try:
        uploader = GoogleDriveUploader()
        
        inspection_date = data.get('data_inspecao')
        if isinstance(inspection_date, str):
            inspection_date_obj = date.fromisoformat(inspection_date)
        else:
            inspection_date_obj = inspection_date
            
        # Calcula a data do próximo teste (anual)
        next_test_date = (inspection_date_obj + relativedelta(years=1)).isoformat()
        
        # Prepara a linha de dados para ser inserida na planilha
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
        st.error(f"Erro ao salvar inspeção da mangueira {data.get('id_mangueira')}: {e}")
        return False
