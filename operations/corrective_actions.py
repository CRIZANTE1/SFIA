import streamlit as st
from datetime import date
from .extinguisher_operations import save_inspection, calculate_next_dates, generate_action_plan
from gdrive.gdrive_upload import GoogleDriveUploader

def save_corrective_action(original_record, action_details, user_name):
    """
    Salva a ação corretiva, lidando com a substituição de equipamentos.

    Se um equipamento for substituído, esta função:
    1. "Aposenta" o equipamento original, removendo sua localização e atualizando seu status.
    2. Registra a ação de substituição no log.
    3. Cria um registro inicial para o novo equipamento no local da troca.

    Se for uma ação simples (sem substituição), ela apenas:
    1. Cria uma nova inspeção "Conforme" para o equipamento.
    2. Registra a ação no log.
    """
    try:
        id_substituto = action_details.get('id_substituto')
        location = action_details.get('location')

        if id_substituto and location:
            retirement_record = original_record.copy()
            retirement_record.update({
                'tipo_servico': "Substituição",
                'data_servico': date.today().isoformat(),
                'inspetor_responsavel': user_name,
                'aprovado_inspecao': "N/A",
                'observacoes_gerais': f"Removido para ação: '{action_details['acao_realizada']}'. Substituído pelo ID: {id_substituto}",
                'plano_de_acao': "FORA DE OPERAÇÃO (SUBSTITUÍDO)",
                'latitude': None,  
                'longitude': None,
                'link_relatorio_pdf': None
            })
            # Remove datas de vencimento futuras para o equipamento aposentado
            retirement_record.update({'data_proxima_inspecao': None, 'data_proxima_manutencao_2_nivel': None, 'data_proxima_manutencao_3_nivel': None})
            save_inspection(retirement_record)

            new_equip_record = {
                'numero_identificacao': id_substituto,
                'numero_selo_inmetro': None,
                'tipo_agente': original_record.get('tipo_agente'), 
                'capacidade': original_record.get('capacidade'),
                'marca_fabricante': None, 
                'ano_fabricacao': None,
                'tipo_servico': "Inspeção",
                'data_servico': date.today().isoformat(),
                'inspetor_responsavel': user_name,
                'aprovado_inspecao': "Sim",
                'observacoes_gerais': f"Instalado em substituição ao ID: {original_record.get('numero_identificacao')}",
                'link_relatorio_pdf': None,
                'latitude': location['latitude'],
                'longitude': location['longitude']
            }
            new_equip_record['plano_de_acao'] = generate_action_plan(new_equip_record)
            new_equip_record.update(calculate_next_dates(new_equip_record['data_servico'], 'Inspeção', new_equip_record.get('tipo_agente')))
            save_inspection(new_equip_record)

        else:
            resolved_inspection = original_record.copy()
            resolved_inspection.update({
                'tipo_servico': "Inspeção",
                'data_servico': date.today().isoformat(),
                'inspetor_responsavel': user_name,
                'aprovado_inspecao': "Sim",
                'observacoes_gerais': f"Ação Corretiva Aplicada: {action_details['acao_realizada']}",
                'latitude': original_record.get('latitude'), 
                'longitude': original_record.get('longitude'),
                'link_relatorio_pdf': None
            })
            resolved_inspection.update(calculate_next_dates(resolved_inspection['data_servico'], 'Inspeção', resolved_inspection.get('tipo_agente')))
            resolved_inspection['plano_de_acao'] = generate_action_plan(resolved_inspection)
            save_inspection(resolved_inspection)

        log_row = [
            date.today().isoformat(),
            original_record.get('numero_identificacao'),
            original_record.get('plano_de_acao'), 
            action_details['acao_realizada'],
            action_details['responsavel_acao'],
            action_details.get('id_substituto')
        ]
        
        uploader = GoogleDriveUploader()
        uploader.append_data_to_sheet("log_acoes", log_row)
        
        return True

    except Exception as e:
        st.error(f"Erro ao salvar a ação corretiva: {e}")
        return False
