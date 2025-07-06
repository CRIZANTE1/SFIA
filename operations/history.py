import streamlit as st
import pandas as pd
import sys
import os

# Garante que o app encontre a pasta gdrive
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import EXTINGUISHER_SHEET_NAME

@st.cache_data(ttl=600)
def load_sheet_data(sheet_name):
    """
    Carrega dados de uma aba específica do Google Sheets e os converte em um DataFrame do Pandas.
    Esta é uma função de utilidade central.
    """
    try:
        uploader = GoogleDriveUploader()
        data = uploader.get_data_from_sheet(sheet_name)
        
        if not data or len(data) < 2:
            st.warning(f"A planilha '{sheet_name}' está vazia ou não contém cabeçalhos.")
            return pd.DataFrame()
            
        headers = data[0]
        rows = data[1:]
        
        # Garante que todas as linhas tenham o mesmo número de colunas do cabeçalho
        num_columns = len(headers)
        cleaned_rows = []
        for row in rows:
            # Completa a linha com 'None' se ela for mais curta que o cabeçalho
            row.extend([None] * (num_columns - len(row)))
            cleaned_rows.append(row[:num_columns])

        df = pd.DataFrame(cleaned_rows, columns=headers)
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha '{sheet_name}': {e}")
        return pd.DataFrame()
        

def find_last_record(df, search_value, column_name):
    """
    Encontra o último registro cronológico de um equipamento
    e TAMBÉM as datas de vencimento mais recentes de todo o seu histórico.
    """
    if df.empty or column_name not in df.columns:
        return None

    records = df[df[column_name].astype(str) == str(search_value)]
    if records.empty:
        return None

    records = records.copy()
    

    records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
    records['data_proxima_manutencao_2_nivel'] = pd.to_datetime(records['data_proxima_manutencao_2_nivel'], errors='coerce')
    records['data_proxima_manutencao_3_nivel'] = pd.to_datetime(records['data_proxima_manutencao_3_nivel'], errors='coerce')
    records['data_ultimo_ensaio_hidrostatico'] = pd.to_datetime(records['data_ultimo_ensaio_hidrostatico'], errors='coerce')


    records.dropna(subset=['data_servico'], inplace=True)

    if records.empty:
        return None


    latest_record_dict = records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()
    last_valid_n2_date = records['data_proxima_manutencao_2_nivel'].max()
    last_valid_n3_date = records['data_proxima_manutencao_3_nivel'].max()
    last_valid_hydro_date = records['data_ultimo_ensaio_hidrostatico'].max()
    latest_record_dict['data_proxima_manutencao_2_nivel'] = last_valid_n2_date
    latest_record_dict['data_proxima_manutencao_3_nivel'] = last_valid_n3_date
    latest_record_dict['data_ultimo_ensaio_hidrostatico'] = last_valid_hydro_date

    return latest_record_dict
