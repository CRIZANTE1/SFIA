import pandas as pd
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import TH_SHIPMENT_LOG_SHEET_NAME, EXTINGUISHER_SHIPMENT_LOG_SHEET_NAME

def log_shipment(df_selected_items, item_type, bulletin_number):
    """
    Salva o log dos itens enviados na planilha correspondente.
    """
    uploader = GoogleDriveUploader()
    today_iso = date.today().isoformat()
    current_year = date.today().year

    if item_type == 'Mangueiras':
        sheet_name = TH_SHIPMENT_LOG_SHEET_NAME
        id_column = 'id_mangueira'
    elif item_type == 'Extintores':
        sheet_name = EXTINGUISHER_SHIPMENT_LOG_SHEET_NAME
        id_column = 'numero_identificacao'
    else:
        return

    for _, row in df_selected_items.iterrows():
        data_row = [
            today_iso,
            row[id_column],
            current_year,
            bulletin_number
        ]
        uploader.append_data_to_sheet(sheet_name, data_row)

def select_extinguishers_for_maintenance(df_extinguishers, df_shipment_log):
    """
    Seleciona aproximadamente 50% dos extintores para manutenção, priorizando
    aqueles com a data de serviço mais antiga e que ainda não foram enviados este ano.
    """
    if df_extinguishers.empty:
        return pd.DataFrame()

    if 'data_servico' not in df_extinguishers.columns:
        return pd.DataFrame()
    df_extinguishers['data_servico'] = pd.to_datetime(df_extinguishers['data_servico'], errors='coerce')
    df_extinguishers = df_extinguishers.dropna(subset=['data_servico', 'numero_identificacao'])

    # 1. Pega o último registro de serviço para cada extintor único
    latest_extinguishers = df_extinguishers.sort_values('data_servico', ascending=False).drop_duplicates('numero_identificacao', keep='first')

    # 2. Filtra os extintores que já foram enviados para manutenção este ano
    current_year = date.today().year
    sent_this_year = []
    if not df_shipment_log.empty and 'ano_remessa' in df_shipment_log.columns:
        df_shipment_log['ano_remessa'] = pd.to_numeric(df_shipment_log['ano_remessa'], errors='coerce')
        if 'numero_identificacao' in df_shipment_log.columns:
            sent_this_year = df_shipment_log[df_shipment_log['ano_remessa'] == current_year]['numero_identificacao'].tolist()

    eligible = latest_extinguishers[~latest_extinguishers['numero_identificacao'].isin(sent_this_year)]
    
    if eligible.empty:
        return pd.DataFrame()

    # 3. Ordena os elegíveis pelo serviço mais antigo
    eligible = eligible.sort_values(by='data_servico', ascending=True)
    
    num_to_select = max(1, len(eligible) // 2)
        
    return eligible.head(num_to_select)
def select_hoses_for_th(df_hoses, df_shipment_log):
    """
    Seleciona aproximadamente metade das mangueiras mais antigas que
    ainda não foram enviadas para teste no ano corrente.
    """
    if df_hoses.empty:
        return pd.DataFrame()

    if 'ano_fabricacao' not in df_hoses.columns:
        return pd.DataFrame()
    df_hoses['ano_fabricacao'] = pd.to_numeric(df_hoses['ano_fabricacao'], errors='coerce')
    df_hoses = df_hoses.dropna(subset=['ano_fabricacao'])

    current_year = date.today().year
    hoses_sent_this_year = []
    
    if not df_shipment_log.empty and 'ano_remessa' in df_shipment_log.columns:
        df_shipment_log['ano_remessa'] = pd.to_numeric(df_shipment_log['ano_remessa'], errors='coerce')
        hoses_sent_this_year = df_shipment_log[df_shipment_log['ano_remessa'] == current_year]['id_mangueira'].tolist()

    eligible_hoses = df_hoses[~df_hoses['id_mangueira'].isin(hoses_sent_this_year)]
    
    if eligible_hoses.empty:
        return pd.DataFrame()
        
    eligible_hoses = eligible_hoses.sort_values(by='ano_fabricacao', ascending=True)
    
    num_to_select = max(1, len(eligible_hoses) // 2)
        
    return eligible_hoses.head(num_to_select)
    
def generate_shipment_html(df_selected_items, item_type, remetente_info, destinatario_info, bulletin_number):
    """
    Gera o HTML para um Boletim de Remessa genérico com cálculo de valor dinâmico.
    """
    today = date.today().strftime('%d/%m/%Y')
    styles = """... (Estilos CSS da DANFE, sem alterações) ..."""
    
    total_value = 0
    item_rows_html = ""

    for _, row in df_selected_items.iterrows():
        unit_value = 0 # Valor padrão
        if item_type == 'Mangueiras':
            item_id = row['id_mangueira']
            description = f"MANGUEIRA DE INCÊNDIO PARA TESTE HIDROSTÁTICO - TIPO {row.get('tipo', 'N/A')} - {row.get('diametro', 'N/A')}"
            unit_value = 3000
        
        elif item_type == 'Extintores':
            item_id = row['numero_identificacao']
            description = f"EXTINTOR DE INCÊNDIO PARA MANUTENÇÃO - TIPO {row.get('tipo_agente', 'N/A')} - {row.get('capacidade', 'N/A')}"
            
            # Lógica de Preços para Extintores
            capacidade = str(row.get('capacidade', '')).lower()
            agente = str(row.get('tipo_agente', '')).lower()

            if '50kg' in capacidade:
                unit_value = 3000.00
            elif '12kg' in capacidade:
                unit_value = 293.00
            elif 'abc' in agente:
                unit_value = 600.00
            elif 'co2' in agente:
                unit_value = 300.00
            else:
                unit_value = 150.00 # Valor padrão para outros extintores
            
        total_value += unit_value
        item_rows_html += f"""
        <tr>
            <td>{item_id}</td><td>{description}</td><td>N/A</td><td>N/A</td>
            <td>UN</td><td>1</td><td>{unit_value:,.2f}</td><td>{unit_value:,.2f}</td>
        </tr>
        """

    for _, row in df_selected_items.iterrows():
        if item_type == 'Mangueiras':
            item_id = row['id_mangueira']
            description = f"MANGUEIRA DE INCÊNDIO PARA TESTE HIDROSTÁTICO - TIPO {row.get('tipo', 'N/A')} - {row.get('diametro', 'N/A')}"
            unit_value = 3000
        elif item_type == 'Extintores':
            item_id = row['numero_identificacao']
            description = f"EXTINTOR DE INCÊNDIO PARA MANUTENÇÃO - TIPO {row.get('tipo_agente', 'N/A')} - {row.get('capacidade', 'N/A')}"
            unit_value = 300
        else:
            item_id = "N/A"
            description = "Item desconhecido"
            unit_value = 0
            
        total_value += unit_value
        item_rows_html += f"""
        <tr>
            <td>{item_id}</td>
            <td>{description}</td>
            <td>N/A</td>
            <td>N/A</td>
            <td>UN</td>
            <td>1</td>
            <td>{unit_value:,.2f}</td>
            <td>{unit_value:,.2f}</td>
        </tr>
        """

    html = f"<html><head><title>Boletim de Remessa {bulletin_number}</title>{styles}</head><body><div class='container'>"
    
    html += f"""
    <div class="header">
        <div class="logo">
            <h2 style="color: #0033a0;">V/V VIBRA</h2>
            <strong>{remetente_info.get('razao_social', 'N/A')}</strong><br>
            {remetente_info.get('endereco', 'N/A')}<br>
            {remetente_info.get('bairro', 'N/A')} - {remetente_info.get('cidade', 'N/A')} / {remetente_info.get('uf', 'N/A')}<br>
            CEP: {remetente_info.get('cep', 'N/A')} FONE: {remetente_info.get('fone', 'N/A')}
        </div>
        <div class="title-box">
            <h1>BOLETIM DE REMESSA</h1>
            <h2>Nº: {bulletin_number}</h2>
            <span><strong>NATUREZA DA OPERAÇÃO:</strong><br>Remessa de mercadoria para conserto ou reparo</span>
        </div>
    </div>
    """
    
    html += f"""
    <div class="info-section">
        <div class="title">DESTINATÁRIO / REMETENTE</div>
        <div class="content">
            <div class="field" style="width: 60%;"><span class="label">NOME / RAZÃO SOCIAL</span><span class="value">{destinatario_info.get('razao_social', 'N/A')}</span></div>
            <div class="field" style="width: 38%;"><span class="label">CNPJ / CPF</span><span class="value">{destinatario_info.get('cnpj', 'N/A')}</span></div>
            <div class="field" style="width: 100%;"><span class="label">ENDEREÇO</span><span class="value">{destinatario_info.get('endereco', 'N/A')}</span></div>
            <div class="field" style="width: 40%;"><span class="label">MUNICÍPIO</span><span class="value">{destinatario_info.get('cidade', 'N/A')}</span></div>
            <div class="field" style="width: 10%;"><span class="label">UF</span><span class="value">{destinatario_info.get('uf', 'N/A')}</span></div>
            <div class="field" style="width: 20%;"><span class="label">FONE / FAX</span><span class="value">{destinatario_info.get('fone', 'N/A')}</span></div>
            <div class="field" style="width: 28%;"><span class="label">INSCRIÇÃO ESTADUAL</span><span class="value">{destinatario_info.get('ie', 'N/A')}</span></div>
        </div>
    </div>
    """
    
    html += f"""
    <table>
        <tr><th>CÓD.</th><th>DESCRIÇÃO DO PRODUTO</th><th>NCM/SH</th><th>CFOP</th><th>UNID.</th><th>QUANT.</th><th>V. UNIT.</th><th>V. TOTAL</th></tr>
        {item_rows_html}
        <tr class="total-row">
            <td colspan="6"></td>
            <td><strong>VALOR TOTAL DOS PRODUTOS</strong></td>
            <td><strong>{total_value:,.2f}</strong></td>
        </tr>
    </table>
    """
    
    html += f"""
    <div class="footer">
        <strong>INFORMAÇÕES COMPLEMENTARES</strong><br>
        <span>Material enviado para Teste/Manutenção conforme normas aplicáveis. Responsável pela remessa: {destinatario_info.get('responsavel', 'N/A')}</span>
    </div>
    """
    
    html += "</div></body></html>"
    return html
