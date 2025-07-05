import streamlit as st
import pandas as pd
import sys
import os

# Garante que o app encontre a pasta gdrive
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gdrive.gdrive_upload import GoogleDriveUploader

@st.cache_data(ttl=300)
def load_sheet_data(sheet_name):
    """
    Carrega dados de uma aba específica do Google Sheets e os converte em um DataFrame do Pandas.
    """
    try:
        uploader = GoogleDriveUploader()
        data = uploader.get_data_from_sheet(sheet_name)
        
        if not data or len(data) < 2:
            st.warning(f"A planilha '{sheet_name}' está vazia ou não contém cabeçalhos.")
            return pd.DataFrame()
            
        headers = data[0]
        rows = data[1:]
        
        num_columns = len(headers)
        cleaned_rows = [row[:num_columns] + [None] * (num_columns - len(row)) for row in rows]

        df = pd.DataFrame(cleaned_rows, columns=headers)
        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha '{sheet_name}': {e}")
        return pd.DataFrame()

# --- FUNÇÃO find_last_record ATUALIZADA E COMPLETA ---
def find_last_record(df, search_value, column_name):
    """
    Função aprimorada que encontra o último registro cronológico de um equipamento
    e TAMBÉM as datas mais recentes de cada tipo de serviço em seu histórico.
    
    Args:
        df (pd.DataFrame): O DataFrame de histórico completo.
        search_value (str): O valor a ser procurado (ex: ID do extintor).
        column_name (str): O nome da coluna onde procurar o valor.
        
    Returns:
        dict or None: Um dicionário contendo os dados do último registro e as
                      datas de serviço mais recentes, ou None se não houver correspondência.
    """
    if df.empty or column_name not in df.columns:
        return None

    # 1. Filtra o DataFrame para obter o histórico completo do equipamento.
    records = df[df[column_name].astype(str) == str(search_value)]

    if records.empty:
        return None

    # 2. Cria uma cópia para trabalhar de forma segura.
    records = records.copy()

    # 3. Converte 'data_servico' para datetime, tratando erros.
    records['data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
    records.dropna(subset=['data_servico'], inplace=True)

    if records.empty:
        return None

    # 4. Encontra o último registro cronológico e o converte para um dicionário.
    # Este será o nosso dicionário base.
    latest_record_dict = records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()

    # 5. Varre o histórico do equipamento para encontrar as datas mais recentes de cada serviço.
    # Uma manutenção também conta como uma inspeção para fins de vencimento.
    last_insp_date = records.loc[records['tipo_servico'].isin(['Inspeção', 'Substituição', 'Manutenção Nível 2', 'Manutenção Nível 3'])]['data_servico'].max()
    last_maint2_date = records.loc[records['tipo_servico'] == 'Manutenção Nível 2']['data_servico'].max()
    last_maint3_date = records.loc[records['tipo_servico'] == 'Manutenção Nível 3']['data_servico'].max()
    
    # 6. Adiciona essas datas de serviço mais recentes ao dicionário que será retornado.
    # Usamos chaves novas para não confundir com as colunas originais do último registro.
    latest_record_dict['latest_insp_date'] = last_insp_date
    latest_record_dict['latest_maint2_date'] = last_maint2_date
    latest_record_dict['latest_maint3_date'] = last_maint3_date
    
    # 7. Retorna o dicionário completo.
    return latest_record_dict
