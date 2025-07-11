import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import EXTINGUISHER_SHEET_NAME
from AI.api_Operation import PDFQA
from utils.prompts import get_extinguisher_inspection_prompt

uploader = GoogleDriveUploader()
pdf_qa = PDFQA()

def generate_action_plan(record):
    """
    Gera um plano de ação padronizado e mais detalhado com base no status e nas observações.
    """
    aprovado = record.get('aprovado_inspecao')
    observacoes = str(record.get('observacoes_gerais', '')).upper()

    if aprovado == "Sim":
        return "Manter em monitoramento periódico."

    if aprovado == "Não":
        action_map = {
            "PINTURA": "Programar a repintura corretiva do extintor.",
            "MANÔMETRO": "Realizar a substituição imediata do manômetro.",
            "GATILHO": "Realizar a substituição do conjunto de gatilho.",
            "VÁLVULA": "Verificar e/ou substituir o conjunto da válvula.",
            "MANGOTE": "Realizar a substituição da mangueira/mangote.",
            "MANGUEIRA": "Realizar a substituição da mangueira/mangote.",
            "RECARGA": "Enviar o extintor para o processo de recarga.",
            "RECARREGANDO": "Enviar o extintor para o processo de recarga.",
            "LACRE": "Substituir lacre e verificar motivo da violação.",
            "SINALIZAÇÃO": "Corrigir a sinalização de piso e/ou parede do equipamento.",
            "SUPORTE": "Verificar e/ou substituir o suporte de parede/piso.",
            "OBSTRUÇÃO": "Desobstruir o acesso ao equipamento e garantir visibilidade.",
            "DANO VISÍVEL": "Realizar inspeção detalhada para avaliar a integridade do casco. Se necessário, enviar para teste hidrostático.",
            "VENCIDO": "Retirar de uso e enviar para manutenção (Nível 2 ou 3) imediatamente."
        }

        # Itera sobre o mapa de ações e retorna o primeiro plano correspondente
        for keyword, plan in action_map.items():
            if keyword in observacoes:
                return plan
        
        # Se nenhuma palavra-chave for encontrada, retorna um plano de ação genérico, mas informativo.
        return f"Analisar e corrigir a não conformidade reportada: '{record.get('observacoes_gerais', '')}'"
    
    return "N/A" # Caso o status não seja 'Sim' ou 'Não'


def calculate_next_dates(service_date_str, service_level, existing_dates=None):
    """
    Calcula as próximas datas de serviço, retornando-as como strings formatadas.
    """
    if not service_date_str: return {}
        
    try:
        service_date = pd.to_datetime(service_date_str).date()
    except (ValueError, TypeError):
        return {} 

    dates = existing_dates.copy() if existing_dates else {}

    # Função auxiliar para converter datetime para string 'YYYY-MM-DD' ou None
    def to_iso_string(dt_object):
        return dt_object.isoformat() if dt_object else None

    if service_level == "Manutenção Nível 3":
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1))
        dates['data_proxima_manutencao_2_nivel'] = (service_date + relativedelta(months=12))
        dates['data_proxima_manutencao_3_nivel'] = (service_date + relativedelta(years=5))
        dates['data_ultimo_ensaio_hidrostatico'] = service_date
    
    elif service_level == "Manutenção Nível 2":
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1))
        dates['data_proxima_manutencao_2_nivel'] = (service_date + relativedelta(months=12))

    elif service_level in ["Inspeção", "Substituição"]:
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1))

    # Converte todos os valores de data no dicionário para string ou None antes de retornar
    for key, value in dates.items():
        if isinstance(value, (date, pd.Timestamp)):
            dates[key] = value.strftime('%Y-%m-%d')
        elif isinstance(value, str):
            # Garante que as strings de data já existentes também não tenham hora
            try:
                dates[key] = pd.to_datetime(value).strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                dates[key] = None # Se for uma string inválida, anula
        elif pd.isna(value):
            dates[key] = None

    return dates
    
def process_extinguisher_pdf(uploaded_file):
    """Processa um PDF de inspeção de extintor usando IA para extrair dados em lote."""
    if uploaded_file:
        prompt = get_extinguisher_inspection_prompt()
        extracted_data = pdf_qa.extract_structured_data(uploaded_file, prompt)
        if extracted_data and "extintores" in extracted_data and isinstance(extracted_data["extintores"], list):
            return extracted_data["extintores"]
        else:
            st.error("A IA não retornou os dados no formato esperado (uma lista de extintores).")
            st.json(extracted_data)
            return None
    return None



def save_inspection(data):
    """Salva os dados de UMA inspeção no Google Sheets, garantindo a serialização correta dos dados."""
    
    def to_safe_string(value):
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, (pd.Timestamp, date)):
            return value.strftime('%Y-%m-%d')
        return str(value)

    lat = data.get('latitude')
    lon = data.get('longitude')

    lat_str = str(lat).replace('.', ',') if lat is not None else None
    lon_str = str(lon).replace('.', ',') if lon is not None else None

    data_row = [
        to_safe_string(data.get('numero_identificacao')),
        to_safe_string(data.get('numero_selo_inmetro')),
        to_safe_string(data.get('tipo_agente')),
        to_safe_string(data.get('capacidade')),
        to_safe_string(data.get('marca_fabricante')),
        to_safe_string(data.get('ano_fabricacao')),
        to_safe_string(data.get('tipo_servico')),
        to_safe_string(data.get('data_servico')),
        to_safe_string(data.get('inspetor_responsavel')),
        to_safe_string(data.get('empresa_executante')),
        to_safe_string(data.get('data_proxima_inspecao')),
        to_safe_string(data.get('data_proxima_manutencao_2_nivel')),
        to_safe_string(data.get('data_proxima_manutencao_3_nivel')),
        to_safe_string(data.get('data_ultimo_ensaio_hidrostatico')),
        to_safe_string(data.get('aprovado_inspecao')),
        to_safe_string(data.get('observacoes_gerais')),
        to_safe_string(data.get('plano_de_acao')),
        to_safe_string(data.get('link_relatorio_pdf')),
        lat_str, 
        lon_str, 
        to_safe_string(data.get('link_foto_nao_conformidade'))
    ]
    
    try:
        uploader = GoogleDriveUploader()
        uploader.append_data_to_sheet(EXTINGUISHER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados do equipamento {data.get('numero_identificacao')}: {e}")
        return False


def clean_and_prepare_ia_data(ia_item):
    """
    Limpa e prepara um item extraído pela IA.
    - Converte campos de data para o formato YYYY-MM-DD.
    - Garante que campos essenciais existam.
    """
    if not isinstance(ia_item, dict):
        return None

    cleaned_item = ia_item.copy()

    # Limpa os campos de data, removendo a hora
    for key, value in cleaned_item.items():
        if 'data' in key and isinstance(value, str):
            try:
                # Converte a string para data e formata de volta para YYYY-MM-DD
                clean_date = pd.to_datetime(value).strftime('%Y-%m-%d')
                cleaned_item[key] = clean_date
            except (ValueError, TypeError):
                # Se a conversão falhar, define como None para evitar erros
                cleaned_item[key] = None
    
    return cleaned_item
