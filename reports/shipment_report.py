import pandas as pd
from datetime import date
import base64
import requests
import io
from weasyprint import HTML
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import TH_SHIPMENT_LOG_SHEET_NAME, EXTINGUISHER_SHIPMENT_LOG_SHEET_NAME



def log_shipment(df_selected_items, item_type, bulletin_number):
    """Salva o log dos itens enviados na planilha correspondente."""
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
        data_row = [today_iso, row[id_column], current_year, bulletin_number]
        uploader.append_data_to_sheet(sheet_name, data_row)

def select_extinguishers_for_maintenance(df_extinguishers, df_shipment_log):
    """Seleciona ~50% dos extintores para manutenção."""
    if df_extinguishers.empty: return pd.DataFrame()
    df_extinguishers['data_servico'] = pd.to_datetime(df_extinguishers['data_servico'], errors='coerce')
    latest_extinguishers = df_extinguishers.sort_values('data_servico', ascending=False).drop_duplicates('numero_identificacao', keep='first')
    current_year = date.today().year
    sent_this_year = []
    if not df_shipment_log.empty and 'ano_remessa' in df_shipment_log.columns:
        if 'numero_identificacao' in df_shipment_log.columns:
            sent_this_year = df_shipment_log[df_shipment_log['ano_remessa'].astype(str) == str(current_year)]['numero_identificacao'].tolist()
    eligible = latest_extinguishers[~latest_extinguishers['numero_identificacao'].isin(sent_this_year)]
    if eligible.empty: return pd.DataFrame()
    eligible = eligible.sort_values(by='data_servico', ascending=True)
    num_to_select = max(1, len(eligible) // 2)
    return eligible.head(num_to_select)

def select_hoses_for_th(df_hoses, df_shipment_log):
    """Seleciona ~50% das mangueiras para teste."""
    if df_hoses.empty: return pd.DataFrame()
    if 'ano_fabricacao' not in df_hoses.columns: return pd.DataFrame()
    df_hoses['ano_fabricacao'] = pd.to_numeric(df_hoses['ano_fabricacao'], errors='coerce')
    df_hoses = df_hoses.dropna(subset=['ano_fabricacao', 'id_mangueira'])
    current_year = date.today().year
    sent_this_year = []
    if not df_shipment_log.empty and 'ano_remessa' in df_shipment_log.columns:
        if 'id_mangueira' in df_shipment_log.columns:
            sent_this_year = df_shipment_log[df_shipment_log['ano_remessa'].astype(str) == str(current_year)]['id_mangueira'].tolist()
    eligible = df_hoses[~df_hoses['id_mangueira'].isin(sent_this_year)]
    if eligible.empty: return pd.DataFrame()
    eligible = eligible.sort_values(by='ano_fabricacao', ascending=True)
    num_to_select = max(1, len(eligible) // 2)
    return eligible.head(num_to_select)

# --- Funções de Geração de HTML e PDF ---

def get_image_base64_from_drive(file_id):
    """Baixa uma imagem do Google Drive e a converte para uma string Base64."""
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            encoded_string = base64.b64encode(response.content).decode('utf-8')
            content_type = response.headers.get('Content-Type', 'image/png')
            return f"data:{content_type};base64,{encoded_string}"
        return None
    except requests.exceptions.RequestException:
        return None

def generate_pdf_from_html(html_content):
    """Converte uma string HTML em um objeto de bytes de PDF usando WeasyPrint."""
    pdf_bytes = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_bytes)
    return pdf_bytes.getvalue()

def generate_shipment_html_and_pdf(df_selected_items, item_type, remetente_info, destinatario_info, bulletin_number):
    """
    Gera o HTML para o boletim e o converte para um PDF em bytes, incluindo campos para assinatura.
    """
    today = date.today().strftime('%d/%m/%Y')
    
    logo_file_id = "1AABdw4iGBJ7tsQ7fR1WGTP5cML3Jlfx_"
    logo_base64 = get_image_base64_from_drive(logo_file_id)
    logo_html = f'<img src="{logo_base64}" alt="Logo VIBRA">' if logo_base64 else '<h2>VIBRA ENERGIA S.A</h2>'

    styles = """
    <style>
        @media print { body { -webkit-print-color-adjust: exact; } }
        body { font-family: sans-serif; font-size: 10px; margin: 0; padding: 20px; }
        .container { border: 1px solid #000; padding: 10px; }
        .header { display: flex; align-items: center; border-bottom: 1px solid #000; padding-bottom: 10px; }
        .header .logo-container { width: 30%; text-align: center; }
        .header .logo-container img { max-width: 150px; max-height: 70px; }
        .header .remetente-info { width: 40%; padding-left: 10px; }
        .header .title-box { width: 30%; border-left: 1px solid #000; text-align: center; padding-left: 10px; }
        h1, h2 { margin: 0; } .header h1 { font-size: 14px; } .header h2 { font-size: 18px; }
        .info-section { border: 1px solid #000; margin-top: 10px; }
        .info-section .title { background-color: #f2f2f2; font-weight: bold; padding: 3px; border-bottom: 1px solid #000; }
        .info-section .content { display: flex; flex-wrap: wrap; }
        .info-section .field { padding: 3px; border-right: 1px solid #ccc; flex-grow: 1; min-width: 15%; }
        .info-section .label { font-size: 8px; color: #555; display: block; }
        .info-section .value { font-size: 12px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9px; }
        table, th, td { border: 1px solid #000 !important; }
        th, td { padding: 4px; text-align: left; }
        th { background-color: #f2f2f2; text-align: center; }
        .total-row td { font-weight: bold; }
        .footer { margin-top: 20px; font-size: 9px; }
        .signatures { display: flex; justify-content: space-around; margin-top: 50px; text-align: center; }
        .signature-box { width: 45%; }
        .signature-box .line { border-top: 1px solid #000; margin-top: 40px; }
    </style>
    """
    
    total_value = 0
    item_rows_html = ""
    for _, row in df_selected_items.iterrows():
        unit_value = 0
        if item_type == 'Mangueiras':
            item_id = row['id_mangueira']
            description = f"MANGUEIRA DE INCÊNDIO P/ TESTE HIDROSTÁTICO - TIPO {row.get('tipo', 'N/A')} - {row.get('diametro', 'N/A')}"
            unit_value = 3000.00
        elif item_type == 'Extintores':
            item_id = row['numero_identificacao']
            description = f"EXTINTOR DE INCÊNDIO P/ MANUTENÇÃO - TIPO {row.get('tipo_agente', 'N/A')} - {row.get('capacidade', 'N/A')}"
            capacidade = str(row.get('capacidade', '')).lower()
            agente = str(row.get('tipo_agente', '')).lower()
            if '50kg' in capacidade: unit_value = 3000.00
            elif '12kg' in capacidade: unit_value = 293.00
            elif 'abc' in agente: unit_value = 600.00
            elif 'co2' in agente: unit_value = 300.00
            else: unit_value = 150.00
            
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

    html_string = f"""
    <html>
        <head><title>Boletim de Remessa {bulletin_number}</title>{styles}</head>
        <body><div class='container'>
            <div class="header">
                <div class="logo-container">{logo_html}</div>
                <div class="remetente-info">
                    <strong>{remetente_info.get('razao_social', 'N/A')}</strong><br>
                    {remetente_info.get('endereco', 'N/A')}<br>
                    {remetente_info.get('bairro', 'N/A')} - {remetente_info.get('cidade', 'N/A')} / {remetente_info.get('uf', 'N/A')}<br>
                    CEP: {remetente_info.get('cep', 'N/A')} FONE: {remetente_info.get('fone', 'N/A')}
                </div>
                <div class="title-box">
                    <h1>BOLETIM DE REMESSA</h1>
                    <h2>Nº: {bulletin_number}</h2>
                    <span><strong>NATUREZA DA OPERAÇÃO:</strong><br>Remessa para conserto ou reparo</span>
                </div>
            </div>
            <div class="info-section">
                <div class="title">DESTINATÁRIO</div>
                <div class="content">
                    <div class="field" style="width: 60%;"><span class="label">NOME / RAZÃO SOCIAL</span><span class="value">{destinatario_info.get('razao_social', 'N/A')}</span></div>
                    <div class="field" style="width: 38%;"><span class="label">CNPJ / CPF</span><span class="value">{destinatario_info.get('cnpj', 'N/A')}</span></div>
                    <div class="field" style="width: 100%;"><span class="label">ENDEREÇO</span><span class="value">{destinatario_info.get('endereco', 'N/A')}</span></div>
                    <div class="field" style="width: 40%;"><span class="label">MUNICÍPIO</span><span class="value">{destinatario_info.get('cidade', 'N/A')}</span></div>
                    <div class="field" style="width: 10%;"><span class="label">UF</span><span class="value">{destinatario_info.get('uf', 'N/A')}</span></div>
                    <div class="field" style="width: 48%; border-right: none;"><span class="label">FONE / FAX</span><span class="value">{destinatario_info.get('fone', 'N/A')}</span></div>
                </div>
            </div>
            <table>
                <tr><th>CÓD.</th><th>DESCRIÇÃO DO PRODUTO</th><th>NCM/SH</th><th>CFOP</th><th>UNID.</th><th>QUANT.</th><th>V. UNIT.</th><th>V. TOTAL</th></tr>
                {item_rows_html}
                <tr class="total-row">
                    <td colspan="6"></td>
                    <td><strong>VALOR TOTAL DOS PRODUTOS</strong></td>
                    <td><strong>{total_value:,.2f}</strong></td>
                </tr>
            </table>
            <div class="footer">
                <strong>INFORMAÇÕES COMPLEMENTARES</strong><br>
                <span>Material enviado para Teste/Manutenção conforme normas aplicáveis.</span>
            </div>
            <div class="signatures">
                <div class="signature-box">
                    <div class="line"></div>
                    <span>{destinatario_info.get('responsavel', 'N/A')}</span><br>
                    <span style="font-size: 8px;">(Remetente - VIBRA ENERGIA)</span>
                </div>
                <div class="signature-box">
                    <div class="line"></div>
                    <span style="font-size: 8px;">Nome / CPF do Recebedor</span><br>
                    <span style="font-size: 8px;">(Destinatário)</span>
                </div>
            </div>
        </div></body>
    </html>
    """
    
    return generate_pdf_from_html(html_string)
