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
    Calcula as próximas datas de serviço, preservando as datas existentes que não são afetadas.
    
    Args:
        service_date_str (str): A data do serviço que está sendo realizado.
        service_level (str): O nível do serviço ('Inspeção', 'Manutenção Nível 2', etc.).
        existing_dates (dict, optional): Um dicionário com as datas de vencimento atuais do equipamento.
    
    Returns:
        dict: Um dicionário com todas as datas de vencimento atualizadas.
    """
    if not service_date_str:
        return {}
        
    try:
        service_date = pd.to_datetime(service_date_str).date()
    except (ValueError, TypeError):
        return {} 

    dates = existing_dates.copy() if existing_dates else {
        'data_proxima_inspecao': None,
        'data_proxima_manutencao_2_nivel': None,
        'data_proxima_manutencao_3_nivel': None,
        'data_ultimo_ensaio_hidrostatico': None,
    }

    if service_level == "Inspeção":
        # Uma inspeção sempre define a próxima inspeção mensal
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1)).isoformat()
    
    elif service_level == "Manutenção Nível 2":
        # Uma manutenção Nível 2 também conta como uma inspeção
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1)).isoformat()
        dates['data_proxima_manutencao_2_nivel'] = (service_date + relativedelta(months=12)).isoformat()

    elif service_level == "Manutenção Nível 3":
        # Uma manutenção Nível 3 (Ensaio Hidrostático) zera TODOS os contadores
        dates['data_proxima_inspecao'] = (service_date + relativedelta(months=1)).isoformat()
        dates['data_proxima_manutencao_2_nivel'] = (service_date + relativedelta(months=12)).isoformat()
        dates['data_proxima_manutencao_3_nivel'] = (service_date + relativedelta(years=5)).isoformat()
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
    """Salva os dados de UMA inspeção no Google Sheets, garantindo a serialização correta dos dados."""
    
    # Função auxiliar para converter valores para tipos JSON-safe (string ou None)
    def to_safe_string(value):
        if pd.isna(value) or value is None:
            return None  # Deixa a célula vazia na planilha
        if isinstance(value, (pd.Timestamp, date)):
            return value.strftime('%Y-%m-%d') # Converte data/timestamp para string
        return str(value) # Converte qualquer outra coisa para string

    # Monta a linha de dados, aplicando a conversão em cada item
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
        to_safe_string(data.get('latitude')),
        to_safe_string(data.get('longitude')),
        to_safe_string(data.get('link_foto_nao_conformidade'))
    ]
    
    try:
        uploader = GoogleDriveUploader()
        uploader.append_data_to_sheet(EXTINGUISHER_SHEET_NAME, data_row)
        return True
    except Exception as e:
        # Mostra um erro mais detalhado para o usuário
        st.error(f"Erro ao salvar dados do equipamento {data.get('numero_identificacao')}: {e}")
        return False
