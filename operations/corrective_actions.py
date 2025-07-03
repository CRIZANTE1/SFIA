import streamlit as st
from datetime import date
import pandas as pd 
from .extinguisher_operations import save_inspection, calculate_next_dates, generate_action_plan
from gdrive.gdrive_upload import GoogleDriveUploader
from .history import load_sheet_data

def find_last_record_local(df, search_value, column_name):
    """
    Função local para encontrar o último registro. Evita importação circular.
    """
    if df.empty or column_name not in df.columns: return None
    # Usa .copy() para segurança
    records = df[df[column_name].astype(str) == str(search_value)].copy()
    if records.empty: return None
    # Usa .loc para evitar warnings
    records.loc[:, 'data_servico'] = pd.to_datetime(records['data_servico'], errors='coerce')
    records.dropna(subset=['data_servico'], inplace=True)
    if records.empty: return None
    return records.sort_values(by='data_servico', ascending=False).iloc[0].to_dict()

def save_corrective_action(original_record, action_details, user_name):
    """
    Salva a ação corretiva, lidando com a substituição de equipamentos e herdando o selo.
    """
    try:
        id_substituto = action_details.get('id_substituto')
        location = action_details.get('location')

        # --- Cenário 1: Substituição de Equipamento ---
        if id_substituto and location:
            # 1. "Aposenta" o equipamento original
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

            # --- LÓGICA DE HERANÇA DO SELO ---
            # Carrega o histórico completo para encontrar o último registro do substituto
            full_history_df = load_sheet_data("extintores")
            substitute_last_record = {}
            if not full_history_df.empty:
                substitute_last_record = find_last_record_local(full_history_df, id_substituto, 'numero_identificacao') or {}
            
            # 2. "Ativa" o equipamento substituto no novo local
            new_equip_record = {
                'numero_identificacao': id_substituto,
                'numero_selo_inmetro': substitute_last_record.get('numero_selo_inmetro'), # Herda o último selo, se existir
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
                'latitude': location['latitude'],
                'longitude': location['longitude']
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
                'latitude': original_record.get('latitude'), 
                'longitude': original_record.get('longitude'),
                'link_relatorio_pdf': None
            })
            resolved_inspection.update(calculate_next_dates(resolved_inspection['data_servico'], 'Inspeção', resolved_inspection.get('tipo_agente')))
            resolved_inspection['plano_de_acao'] = generate_action_plan(resolved_inspection)
            save_inspection(resolved_inspection)

        # Registra a ação no log
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
