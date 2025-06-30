# operations/extinguisher_operations.py

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
    Gera um plano de ação padronizado com base no status e nas observações.
    """
    aprovado = record.get('aprovado_inspecao')
    observacoes = record.get('observacoes_gerais', '').upper()

    if aprovado == "Sim":
        return "Manter em monitoramento periódico."

    if aprovado == "Não":
        if "PINTURA" in observacoes:
            return "Programar a repintura corretiva do extintor."
        elif "MANÔMETRO" in observacoes:
            return "Realizar a substituição imediata do manômetro."
        elif "GATILHO" in observacoes:
            return "Realizar a substituição do conjunto de gatilho."
        elif "MANGOTE" in observacoes or "MANGUEIRA" in observacoes:
            return "Realizar a substituição da mangueira/mangote."
        elif "RECARREGANDO" in observacoes or "RECARGA" in observacoes:
            return "Enviar o extintor para o processo de recarga."
        elif "LACRE" in observacoes:
            return "Substituir lacre e verificar motivo da violação."
        else:
            return f"Analisar e corrigir a não conformidade: {record.get('observacoes_gerais', '')}"
    
    return "N/A"

def calculate_next_dates(service_date_str, service_level, extinguisher_type):
    if not service_date_str: return {}
    service_date = date.fromisoformat(service_date_str)
    extinguisher_type = extinguisher_type or ""
    freq_inspecao_meses = 6 if "CO2" in extinguisher_type.upper() else 12
    freq_manutencao_2_meses = 12
    freq_manutencao_3_anos = 5
    proxima_inspecao = service_date + relativedelta(months=freq_inspecao_meses)
    proxima_manutencao_2 = service_date + relativedelta(months=freq_manutencao_2_meses)
    proxima_manutencao_3 = service_date + relativedelta(years=freq_manutencao_3_anos)
    return {
        'data_proxima_inspecao': proxima_inspecao.isoformat(),
        'data_proxima_manutencao_2_nivel': proxima_manutencao_2.isoformat(),
        'data_proxima_manutencao_3_nivel': proxima_manutencao_3.isoformat(),
        'data_ultimo_ensaio_hidrostatico': service_date.isoformat() if service_level == "Manutenção Nível 3" else None,
    }

def process_extinguisher_pdf(uploaded_file):
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