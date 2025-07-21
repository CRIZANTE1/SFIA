def generate_shelters_html(df_shelters):
    styles = """
    <style>
        @media print { body { -webkit-print-color-adjust: exact; } }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #333; }
        .report-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
        .shelter-container { border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 20px; page-break-inside: avoid; }
        .shelter-title { font-size: 1.5em; font-weight: bold; color: #0068c9; }
        .shelter-client { font-size: 1.1em; color: #555; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f0f2f6; }
    </style>
    """
    html = f"<html><head><title>Inventário de Abrigos</title>{styles}</head><body>"
    html += "<div class='report-header'><h1>Inventário de Abrigos de Emergência</h1></div>"

    for _, row in df_shelters.iterrows():
        html += f"<div class='shelter-container'>"
        html += f"<div class='shelter-title'>Abrigo ID: {row['id_abrigo']}</div>"
        html += f"<div class='shelter-client'>Cliente: {row['cliente']}</div>"
        
        try:
            items = json.loads(row['itens_json'])
            if items:
                html += "<table><tr><th>Item</th><th>Quantidade Prevista</th><th>Quantidade Conferida</th><th>Status</th></tr>"
                for item, qty in items.items():
                    html += f"<tr><td>{item}</td><td>{qty}</td><td></td><td></td></tr>"
                html += "</table>"
            else:
                html += "<p>Nenhum item inventariado.</p>"
        except (json.JSONDecodeError, TypeError):
            html += "<p>Erro ao ler o inventário de itens.</p>"
        
        html += "</div>"

    html += "</body></html>"
    return html
