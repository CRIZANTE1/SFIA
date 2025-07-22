import streamlit as st
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import SCBA_SHEET_NAME

def save_scba_inspection(record, pdf_link, user_name):
    """
    Salva um novo registro de inspeção de conjunto autônomo na planilha.
    """
    try:
        uploader = GoogleDriveUploader()
        
        data_row = [
            record.get('data_teste'),
            record.get('data_validade'),
            record.get('numero_serie_equipamento'),
            record.get('marca'),
            record.get('modelo'),
            record.get('numero_serie_mascara'),
            record.get('numero_serie_segundo_estagio'),
            record.get('resultado_final'),
            record.get('vazamento_mascara_resultado'),
            record.get('vazamento_mascara_valor'),
            record.get('vazamento_pressao_alta_resultado'),
            record.get('vazamento_pressao_alta_valor'),
            record.get('pressao_alarme_resultado'),
            record.get('pressao_alarme_valor'),
            pdf_link,
            user_name,
            record.get('empresa_executante'),
            record.get('responsavel_tecnico')
        ]
        
        uploader.append_data_to_sheet(SCBA_SHEET_NAME, data_row)
        return True

    except Exception as e:
        st.error(f"Erro ao salvar inspeção do SCBA {record.get('numero_serie_equipamento')}: {e}")
        return False
