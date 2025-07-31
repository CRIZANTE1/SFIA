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
    
def generate_shipment_html(df_selected_hoses, client_name, responsible_name, bulletin_number):
    """
    Gera o HTML para o Boletim de Remessa para Teste Hidrostático.
    """
    today = date.today().strftime('%d/%m/%Y')
    
    styles = """... (Estilos CSS para o PDF, como nos outros relatórios) ..."""
    
    html = f"<html><head><title>Boletim de Remessa {bulletin_number}</title>{styles}</head><body>"
    html += f"<div class='report-header'><h1>Boletim de Remessa para Teste Hidrostático</h1><h2>Nº {bulletin_number}</h2></div>"
    html += f"<div class='info-grid'><span><strong>Cliente:</strong> {client_name}</span><span><strong>Data de Emissão:</strong> {today}</span></div>"
    
    html += "<table><tr><th>Nº</th><th>ID da Mangueira</th><th>Marca</th><th>Diâmetro</th><th>Tipo</th><th>Ano Fabricação</th></tr>"
    for index, row in df_selected_hoses.iterrows():
        html += f"<tr><td>{index + 1}</td><td>{row['id_mangueira']}</td><td>{row.get('marca', 'N/A')}</td><td>{row.get('diametro', 'N/A')}</td><td>{row.get('tipo', 'N/A')}</td><td>{int(row.get('ano_fabricacao', 0))}</td></tr>"
    html += "</table>"
    
    html += f"<div class='footer'><p>Declaramos que as mangueiras acima foram remetidas para a realização do Teste Hidrostático conforme NBR 12779.</p>"
    html += f"<div class='signature-box'><br/><br/>_________________________<br/>{responsible_name}<br/>Responsável pela Remessa</div></div>"
    html += "</body></html>"
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
