import json
import pandas as pd
import base64
import requests

def generate_shelters_html(df_shelters_registered, df_inspections, df_action_log):
    """
    Gera um relatório de status completo para os abrigos, destacando as pendências
    na última inspeção.
    """
    styles = """
    <style>
        @media print { body { -webkit-print-color-adjust: exact; } }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #333; }
        .report-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .shelter-container { border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 20px; page-break-inside: avoid; }
        .shelter-title { font-size: 1.5em; font-weight: bold; color: #0068c9; }
        .shelter-info { display: flex; justify-content: space-between; font-size: 1.1em; color: #555; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .subsection-title { font-weight: bold; margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f0f2f6; }
        .status-ok { color: green; }
        /* Destaque para pendências */
        .status-fail { color: red; font-weight: bold; background-color: #ffe5e5; }
        .log-entry { margin-left: 10px; padding-left: 10px; border-left: 2px solid #eee; }
    </style>
    """
    html = f"<html><head><title>Relatório de Status de Abrigos</title>{styles}</head><body>"
    html += "<div class='report-header'><h1>Relatório de Status de Abrigos de Emergência</h1></div>"

    latest_inspections = pd.DataFrame()
    if not df_inspections.empty:
        df_inspections['data_inspecao_dt'] = pd.to_datetime(df_inspections['data_inspecao'])
        latest_inspections = df_inspections.sort_values('data_inspecao_dt', ascending=False).drop_duplicates('id_abrigo', keep='first')

    for _, shelter in df_shelters_registered.iterrows():
        shelter_id = shelter['id_abrigo']
        shelter_local = shelter.get('local', 'N/A')
        shelter_client = shelter.get('cliente', 'N/A')

        html += f"<div class='shelter-container'>"
        html += f"<div class='shelter-title'>Abrigo ID: {shelter_id}</div>"
        html += f"<div class='shelter-info'><span><strong>Local:</strong> {shelter_local}</span><span><strong>Cliente:</strong> {shelter_client}</span></div>"
        
        html += "<div class='subsection-title'>Resultado da Última Inspeção</div>"
        
        last_inspection = latest_inspections[latest_inspections['id_abrigo'] == shelter_id]
        
        if not last_inspection.empty:
            inspection_details = last_inspection.iloc[0]
            inspection_date = pd.to_datetime(inspection_details['data_inspecao']).strftime('%d/%m/%Y')
            status_geral = inspection_details['status_geral']
            
            # Adiciona destaque de cor ao status geral se houver pendências
            status_class_geral = "status-fail" if status_geral == "Reprovado com Pendências" else "status-ok"
            html += f"<p><strong>Data da Inspeção:</strong> {inspection_date} | <strong>Status Geral:</strong> <span class='{status_class_geral}'>{status_geral}</span></p>"
            
            try:
                results = json.loads(inspection_details['resultados_json'])
                html += "<table><tr><th>Item</th><th>Status</th><th>Observação</th></tr>"
                
                # Itera sobre todas as categorias (Cilindro, Mascara, Testes Funcionais, etc.)
                for category, items in results.items():
                    # Adiciona uma linha de cabeçalho para a categoria, se houver mais de uma
                    if len(results) > 1:
                        html += f"<tr><th colspan='3' style='background-color: #e9ecef;'>{category}</th></tr>"
                    
                    for item, details in items.items():
                        # Lógica para determinar o status e a classe CSS
                        item_status = details.get('status', 'N/A') if isinstance(details, dict) else details
                        is_ok = str(item_status).upper() in ["C", "APROVADO", "SIM", "OK"]
                        status_class = "status-ok" if is_ok else "status-fail"
                        
                        observacao = details.get('observacao', '') if isinstance(details, dict) else ''

                        # Gera a linha da tabela com o destaque de cor se não estiver OK
                        html += f"<tr class='{status_class}'><td class='{status_class}'>{item}</td><td class='{status_class}'>{item_status}</td><td class='{status_class}'>{observacao}</td></tr>"

                html += "</table>"
            except (json.JSONDecodeError, TypeError):
                html += "<p>Erro ao ler os detalhes da inspeção.</p>"
        else:
            html += "<p>Nenhuma inspeção registrada para este abrigo.</p>"

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
