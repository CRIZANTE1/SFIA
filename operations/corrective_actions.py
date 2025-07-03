import streamlit as st
from datetime import date
from .extinguisher_operations import save_inspection, calculate_next_dates, generate_action_plan
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import EXTINGUISHER_SHEET_NAME, GDRIVE_SHEETS_ID # Supondo que o log ficará na mesma planilha

def save_corrective_action(original_record, action_details, user_name):
    """
    Salva a ação corretiva em dois lugares:
    1. Cria um novo registro de inspeção "Conforme" na aba principal.
    2. Adiciona uma entrada no log de ações corretivas.
    """
    try:
        # --- 1. Cria um novo registro de inspeção para "resolver" o status ---
        resolved_inspection = original_record.copy()
        
        # Atualiza os dados para a nova inspeção pós-correção
        resolved_inspection.update({
            'tipo_servico': "Inspeção",
            'data_servico': date.today().isoformat(),
            'inspetor_responsavel': user_name,
            'aprovado_inspecao': "Sim",
            'observacoes_gerais': f"Ação Corretiva: {action_details['acao_realizada']}",
            'latitude': original_record.get('latitude'), # Mantém a última localização conhecida
            'longitude': original_record.get('longitude'),
            'link_relatorio_pdf': None # Ações corretivas não têm relatório PDF
        })
        
        # Recalcula datas e plano de ação para o novo status "OK"
        resolved_inspection.update(calculate_next_dates(
            resolved_inspection['data_servico'], 'Inspeção', resolved_inspection.get('tipo_agente')
        ))
        resolved_inspection['plano_de_acao'] = generate_action_plan(resolved_inspection)
        
        # Salva o novo registro de inspeção
        save_inspection(resolved_inspection)

        # --- 2. Adiciona uma linha na aba de log 'log_acoes' ---
        log_row = [
            date.today().isoformat(),
            original_record.get('numero_identificacao'),
            original_record.get('plano_de_acao'), # Problema original
            action_details['acao_realizada'],
            action_details['responsavel_acao']
        ]
        
        uploader = GoogleDriveUploader()
        uploader.append_data_to_sheet("log_acoes", log_row)
        
        return True

    except Exception as e:
        st.error(f"Erro ao salvar a ação corretiva: {e}")
        return False
