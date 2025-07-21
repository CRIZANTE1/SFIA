import json
import pandas as pd
import base64
import requests

def generate_shelters_html(df_shelters_registered, df_inspections, df_action_log):
    """
    Gera um relatório de status completo para os abrigos, incluindo o resultado
    da última inspeção e o log de ações corretivas.
    """
    styles = """
    <style>
        @media print { body { -webkit-print-color-adjust: exact; } }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #333; }
        .report-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .shelter-container { border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 20px; page-break-inside: avoid; }
        .shelter-title { font-size: 1.5em; font-weight: bold; color: #0068c9; }
        .shelter-client { font-size: 1.1em; color: #555; margin-bottom: 15px; }
        .subsection-title { font-weight: bold; margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f0f2f6; }
        .status-ok { color: green; }
        .status-fail { color: red; font-weight: bold; }
        .log-entry { margin-left: 10px; padding-left: 10px; border-left: 2px solid #eee; }
    </style>
    """
    html = f"<html><head><title>Relatório de Status de Abrigos</title>{styles}</head><body>"
    html += "<div class='report-header'><h1>Relatório de Status de Abrigos de Emergência</h1></div>"

    # Preparar dados de inspeções mais recentes
    latest_inspections = pd.DataFrame()
    if not df_inspections.empty:
        df_inspections['data_inspecao_dt'] = pd.to_datetime(df_inspections['data_inspecao'])
        latest_inspections = df_inspections.sort_values('data_inspecao_dt', ascending=False).drop_duplicates('id_abrigo', keep='first')

    for _, shelter in df_shelters_registered.iterrows():
        shelter_id = shelter['id_abrigo']
        html += f"<div class='shelter-container'>"
        html += f"<div class='shelter-title'>Abrigo ID: {shelter_id}</div>"
        html += f"<div class='shelter-client'>Cliente: {shelter['cliente']}</div>"
        
        # --- Seção do Inventário e Última Inspeção ---
        html += "<div class='subsection-title'>Resultado da Última Inspeção</div>"
        
        last_inspection = latest_inspections[latest_inspections['id_abrigo'] == shelter_id]
        
        if not last_inspection.empty:
            inspection_details = last_inspection.iloc[0]
            inspection_date = pd.to_datetime(inspection_details['data_inspecao']).strftime('%d/%m/%Y')
            html += f"<p><strong>Data da Inspeção:</strong> {inspection_date} | <strong>Status Geral:</strong> {inspection_details['status_geral']}</p>"
            
            try:
                results = json.loads(inspection_details['resultados_json'])
                html += "<table><tr><th>Item</th><th>Status</th><th>Observação</th></tr>"
                for item, details in results.items():
                    status_class = "status-ok" if details.get('status') == 'OK' else "status-fail"
                    html += f"<tr><td>{item}</td><td class='{status_class}'>{details.get('status', 'N/A')}</td><td>{details.get('observacao', '')}</td></tr>"
                html += "</table>"
            except (json.JSONDecodeError, TypeError):
                html += "<p>Erro ao ler os detalhes da inspeção.</p>"
        else:
            html += "<p>Nenhuma inspeção registrada para este abrigo.</p>"

        # --- Seção do Log de Ações Corretivas ---
        html += "<div class='subsection-title'>Histórico de Ações Corretivas</div>"
        action_log_entries = df_action_log[df_action_log['id_abrigo'] == shelter_id] if not df_action_log.empty else pd.DataFrame()
        
        if not action_log_entries.empty:
            for _, log in action_log_entries.iterrows():
                log_date = pd.to_datetime(log['data_acao']).strftime('%d/%m/%Y')
                html += "<div class='log-entry'>"
                html += f"<p><strong>Data:</strong> {log_date} | <strong>Responsável:</strong> {log['responsavel']}</p>"
                html += f"<p><strong>Problema Original:</strong> {log['problema_original']}</p>"
                html += f"<p><strong>Ação Realizada:</strong> {log['acao_realizada']}</p>"
                html += "</div>"
        else:
            html += "<p>Nenhuma ação corretiva registrada para este abrigo.</p>"
            
        html += "</div>"

    html += "</body></html>"
    return html
