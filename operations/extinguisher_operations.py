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
    """Gera um plano de ação padronizado com base no status e nas observações."""
    aprovado = record.get('aprovado_inspecao')
    observacoes = record.get('observacoes_gerais', '').upper()
    if aprovado == "Sim":
        return "Manter em monitoramento periódico."
    if aprovado == "Não":
        if "PINTURA" in observacoes: return "Programar a repintura corretiva do extintor."
        if "MANÔMETRO" in observacoes: return "Realizar a substituição imediata do manômetro."
        if "GATILHO" in observacoes: return "Realizar a substituição do conjunto de gatilho."
        if "MANGOTE" in observacoes or "MANGUEIRA" in observacoes: return "Realizar a substituição da mangueira/mangote."
        if "RECARREGANDO" in observacoes or "RECARGA" in observacoes: return "Enviar o extintor para o processo de recarga."
        if "LACRE" in observacoes: return "Substituir lacre e verificar motivo da violação."
        return f"Analisar e corrigir a não conformidade: {record.get('observacoes_gerais', '')}"
    return "N/A"

def calculate_next_dates(service_date_str, service_level, extinguisher_type):
    """
    Calcula as próximas datas de serviço com base na data e nível de serviço.
    Inspeção agora é MENSAL.
    """
    if not service_date_str: return {}
    
    try:
        service_date = date.fromisoformat(service_date_str)
    except (ValueError, TypeError):
        return {} 

    dates = {
        'data_proxima_inspecao': None,
        'data_proxima_manutencao_2_nivel': None,
        'data_proxima_manutencao_3_nivel': None,
        'data_ultimo_ensaio_hidrostatico': None,
    }

    if service_level == "Inspeção":
        # ALTERAÇÃO AQUI: Frequência de inspeção fixada em 1 mês.
        freq_inspecao_meses = 1
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=freq_inspecao_meses)).isoformat()
    
    elif service_level == "Manutenção Nível 2":
        freq_manutencao_2_meses = 12
        dates['data_proxima_manutencao_2_nivel'] = (service_date + relativedelta(months=freq_manutencao_2_meses)).isoformat()

    elif service_level == "Manutenção Nível 3":
        freq_manutencao_3_anos = 5
        dates['data_proxima_manutencao_3_nivel'] = (service_date + relativedelta(years=freq_manutencao_3_anos)).isoformat()
        dates['data_ultimo_ensaio_hidrostatico'] = service_date.isoformat()
        
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
    """Salva os dados de UMA inspeção no Google Sheets."""
    extinguisher_id = data.get('numero_identificacao', 'N/A')
    data_row = [
        data.get('numero_identificacao'), data.get('tipo_agente'), data.get('capacidade'),
        data.get('marca_fabricante'), data.get('ano_fabricacao'), data.get('tipo_servico'),
        data.get('data_servico'), data.get('inspetor_responsavel'), data.get('empresa_executante'),
        data.get('data_proxima_inspecao'), data.get('data_proxima_manutencao_2_nivel'),
        data.get('data_proxima_manutencao_3_nivel'), data.get('data_ultimo_ensaio_hidrostatico'),
        data.get('aprovado_inspecao'), data.get('observacoes_gerais'), data.get('plano_de_acao'),
    ]
    try:
        uploader.append_data_to_sheet(EXTINGUISHER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados do extintor {extinguisher_id} no Google Sheets: {e}")
        return False
