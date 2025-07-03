import streamlit as st
from datetime import date
from .extinguisher_operations import save_inspection, calculate_next_dates, generate_action_plan
from gdrive.gdrive_upload import GoogleDriveUploader

def save_corrective_action(original_record, substitute_last_record, action_details, user_name):
    """
    Salva a ação corretiva, lidando com a substituição de equipamentos.
    - original_record: Dicionário com os dados do equipamento com problema.
    - substitute_last_record: Dicionário com o último registro do equipamento substituto (pode ser um dict vazio).
    - action_details: Dicionário com os detalhes da ação preenchida pelo usuário.
    - user_name: Nome do usuário logado.
    """
    try:
        id_substituto = action_details.get('id_substituto')
        location = action_details.get('location') 

        # --- Cenário 1: Substituição de Equipamento ---
        if id_substituto:
            # 1. "Aposenta" o equipamento original, removendo sua localização
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
                'link_relatorio_pdf': None,
                'data_proxima_inspecao': None, 
                'data_proxima_manutencao_2_nivel': None, 
                'data_proxima_manutencao_3_nivel': None
            })
            save_inspection(retirement_record)

            # 2. "Ativa" o equipamento substituto no local do antigo
            new_equip_record = {
                'numero_identificacao': id_substituto,
                'numero_selo_inmetro': substitute_last_record.get('numero_selo_inmetro'),
                'tipo_agente': substitute_last_record.get('tipo_agente', original_record.get('tipo_agente')),
                'capacidade': substitute_last_record.get('capacidade', original_record.get('capacidade')),
                'marca_fabricante': substitute_last_record.get('marca_fabricante'),
                'ano_fabricacao': substitute_last_record.get('ano_fabricacao'),
                'tipo_servico': "Inspeção",
                'data_servico': date.today().isoformat(),
                'inspetor_responsavel': user_name,
                'aprovado_inspecao': "Sim",
                'observacoes_gerais': f"Instalado em substituição ao ID: {original_record.get('numero_identificacao')}",
                'link_relatorio_pdf': None,
                # CORREÇÃO: Usa a localização do equipamento ORIGINAL
                'latitude': original_record.get('latitude'),
                'longitude': original_record.get('longitude')
            }
            new_equip_record['plano_de_acao'] = generate_action_plan(new_equip_record)
            new_equip_record.update(calculate_next_dates(new_equip_record['data_servico'], 'Inspeção', new_equip_record.get('tipo_agente')))
            save_inspection(new_equip_record)

        # --- Cenário 2: Ação Corretiva Simples (sem substituição) ---
        else:
            resolved_inspection = original_record.copy()
            resolved_inspection.update({
                'tipo_servico': "Inspeção",
                'data_servico': date.today().isoformat(),
                'inspetor_responsavel': user_name,
                'aprovado_inspecao': "Sim",
                'observacoes_gerais': f"Ação Corretiva Aplicada: {action_details['acao_realizada']}",
                # Mantém a localização original, pois o equipamento não mudou de lugar
                'latitude': original_record.get('latitude'), 
                'longitude': original_record.get('longitude'),
                'link_relatorio_pdf': None
            })
            resolved_inspection.update(calculate_next_dates(resolved_inspection['data_servico'], 'Inspeção', resolved_inspection.get('tipo_agente')))
            resolved_inspection['plano_de_acao'] = generate_action_plan(resolved_inspection)
            save_inspection(resolved_inspection)

        # Registra a ação no log para ambos os cenários
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
