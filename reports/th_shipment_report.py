import pandas as pd
from datetime import date
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import TH_SHIPMENT_LOG_SHEET_NAME


def select_hoses_for_th(df_hoses, df_shipment_log):
    """
    Seleciona aproximadamente metade das mangueiras mais antigas que
    ainda não foram enviadas para teste no ano corrente.
    """
    if df_hoses.empty:
        return pd.DataFrame()

    # Garante que a coluna de fabricação seja numérica
    if 'ano_fabricacao' not in df_hoses.columns:
        return pd.DataFrame()
    df_hoses['ano_fabricacao'] = pd.to_numeric(df_hoses['ano_fabricacao'], errors='coerce')
    df_hoses = df_hoses.dropna(subset=['ano_fabricacao'])

    # Filtra mangueiras já enviadas este ano
    current_year = date.today().year
    hoses_sent_this_year = []
    
    # Lida com o log de remessas, mesmo que esteja vazio
    if not df_shipment_log.empty and 'ano_remessa' in df_shipment_log.columns:
        df_shipment_log['ano_remessa'] = pd.to_numeric(df_shipment_log['ano_remessa'], errors='coerce')
        hoses_sent_this_year = df_shipment_log[df_shipment_log['ano_remessa'] == current_year]['id_mangueira'].tolist()

    eligible_hoses = df_hoses[~df_hoses['id_mangueira'].isin(hoses_sent_this_year)]
    
    if eligible_hoses.empty:
        return pd.DataFrame()
        
    eligible_hoses = eligible_hoses.sort_values(by='ano_fabricacao', ascending=True)
    
    num_to_select = max(1, len(eligible_hoses) // 2)
        
    return eligible_hoses.head(num_to_select)
    
def generate_shipment_html(df_selected_hoses, client_info, destinatario_info, bulletin_number):
    """
    Gera o HTML para o Boletim de Remessa, inspirado em uma DANFE.
    """
    today = date.today().strftime('%d/%m/%Y')
    
    styles = """
    <style>
        @media print { body { -webkit-print-color-adjust: exact; } }
        body { font-family: sans-serif; font-size: 10px; margin: 0; padding: 20px; }
        .container { border: 1px solid #000; padding: 10px; }
        .header { display: flex; border-bottom: 1px solid #000; padding-bottom: 10px; }
        .header .logo { width: 40%; }
        .header .title-box { width: 60%; border-left: 1px solid #000; text-align: center; padding-left: 10px; }
        .header h1 { margin: 0; font-size: 14px; }
        .header h2 { margin: 5px 0; font-size: 18px; }
        .info-section { border: 1px solid #000; margin-top: 10px; }
        .info-section .title { background-color: #eee; font-weight: bold; padding: 3px; border-bottom: 1px solid #000; }
        .info-section .content { display: flex; flex-wrap: wrap; }
        .info-section .field { padding: 3px; border-right: 1px solid #ccc; flex-grow: 1; }
        .info-section .field-large { width: 100%; }
        .info-section .label { font-size: 8px; color: #555; display: block; }
        .info-section .value { font-size: 12px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9px; }
        th, td { border: 1px solid #000; padding: 4px; text-align: left; }
        th { background-color: #eee; text-align: center; }
        .total-row td { font-weight: bold; }
        .footer { margin-top: 20px; font-size: 9px; }
    </style>
    """
    
    total_value = len(df_selected_hoses) * 3000

    html = f"<html><head><title>Boletim de Remessa {bulletin_number}</title>{styles}</head><body><div class='container'>"
    
    html += f"""
    <div class="header">
        <div class="logo">
            <h2 style="color: #0033a0;">V/V VIBRA</h2>
            <strong>VIBRA ENERGIA S.A</strong><br>
            {client_info['endereco']}<br>
            {client_info['bairro']} - {client_info['cidade']} / {client_info['uf']}<br>
            CEP: {client_info['cep']} FONE: {client_info['fone']}
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
            <div class="field" style="width: 60%;"><span class="label">NOME / RAZÃO SOCIAL</span><span class="value">{destinatario_info['razao_social']}</span></div>
            <div class="field" style="width: 38%;"><span class="label">CNPJ / CPF</span><span class="value">{destinatario_info['cnpj']}</span></div>
            <div class="field" style="width: 100%;"><span class="label">ENDEREÇO</span><span class="value">{destinatario_info['endereco']}</span></div>
            <div class="field" style="width: 40%;"><span class="label">MUNICÍPIO</span><span class="value">{destinatario_info['cidade']}</span></div>
            <div class="field" style="width: 10%;"><span class="label">UF</span><span class="value">{destinatario_info['uf']}</span></div>
            <div class="field" style="width: 20%;"><span class="label">FONE / FAX</span><span class="value">{destinatario_info['fone']}</span></div>
            <div class="field" style="width: 28%;"><span class="label">INSCRIÇÃO ESTADUAL</span><span class="value">{destinatario_info['ie']}</span></div>
        </div>
    </div>
    """
    
    html += "<table><tr><th>CÓD.</th><th>DESCRIÇÃO DO PRODUTO</th><th>NCM/SH</th><th>CFOP</th><th>UNID.</th><th>QUANT.</th><th>V. UNIT.</th><th>V. TOTAL</th></tr>"
    for _, row in df_selected_hoses.iterrows():
        html += f"""
        <tr>
            <td>{row['id_mangueira']}</td>
            <td>MANGUEIRA DE INCÊNDIO PARA TESTE HIDROSTÁTICO - TIPO {row.get('tipo', 'N/A')} - {row.get('diametro', 'N/A')}</td>
            <td>59090000</td>
            <td>5915</td>
            <td>UN</td>
            <td>1</td>
            <td>3.000,00</td>
            <td>3.000,00</td>
        </tr>
        """
    html += f"""
    <tr class="total-row">
        <td colspan="6"></td>
        <td><strong>VALOR TOTAL DOS PRODUTOS</strong></td>
        <td><strong>{total_value:,.2f}</strong></td>
    </tr>
    """
    html += "</table>"
    
    html += f"""
    <div class="footer">
        <strong>INFORMAÇÕES COMPLEMENTARES</strong><br>
        <span>Material enviado para Teste Hidrostático (TH) conforme norma ABNT NBR 12779. Responsável pela remessa: {destinatario_info['responsavel']}</span>
    </div>
    """
    
    html += "</div></body></html>"
    return html

def log_th_shipment(df_selected_hoses, bulletin_number):
    """
    Salva o log das mangueiras enviadas na planilha 'log_remessas_th'.
    """
    uploader = GoogleDriveUploader()
    today_iso = date.today().isoformat()
    current_year = date.today().year
    
    for _, row in df_selected_hoses.iterrows():
        data_row = [
            today_iso,
            row['id_mangueira'],
            current_year,
            bulletin_number
        ]
        uploader.append_data_to_sheet(TH_SHIPMENT_LOG_SHEET_NAME, data_row)
