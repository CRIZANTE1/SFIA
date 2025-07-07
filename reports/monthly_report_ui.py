import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data

def generate_report_html(df_inspections_month, df_action_log, month, year):
    """Gera o conteúdo do relatório como uma string HTML pura."""
    
    # Estilos CSS para o relatório
    styles = """
    <style>
        body { font-family: sans-serif; }
        .report-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .inspection-item { border: 1px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 20px; page-break-inside: avoid; }
        .item-header { font-size: 1.2em; font-weight: bold; }
        .status-ok { color: green; }
        .status-fail { color: red; }
        .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
        .metric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; }
        .metric-label { font-size: 0.9em; color: #555; }
        .metric-value { font-size: 1.1em; font-weight: bold; }
        .subsection-header { font-weight: bold; margin-top: 15px; border-top: 1px dashed #ddd; padding-top: 10px; }
        .evidence-img { max-width: 300px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
    """
    
    html = f"<html><head><title>Relatório {month:02d}/{year}</title>{styles}</head><body>"
    html += f"<div class='report-header'><h1>Relatório de Inspeções de Extintores</h1><h2>Período: {month:02d}/{year}</h2></div>"

    if df_inspections_month.empty:
        html += "<p>Nenhum registro de inspeção de extintor encontrado para o período.</p>"
    else:
        if not df_action_log.empty:
            df_action_log['data_correcao_dt'] = pd.to_datetime(df_action_log['data_correcao'], errors='coerce')

        for _, inspection in df_inspections_month.iterrows():
            ext_id = inspection['numero_identificacao']
            is_ok = inspection['aprovado_inspecao'] == "Sim"
            status_class = "status-ok" if is_ok else "status-fail"
            status_text = "Conforme" if is_ok else "Não Conforme"
            icon = "✅" if is_ok else "❌"
            obs = inspection['observacoes_gerais']
            photo_nc_link = inspection.get('link_foto_nao_conformidade')
            inspection_date = pd.to_datetime(inspection['data_servico'])

            html += f"""
            <div class='inspection-item'>
                <div class='item-header {status_class}'>{icon} Equipamento ID: {ext_id}</div>
                <div class='details-grid'>
                    <div class='metric'><div class='metric-label'>Data da Inspeção</div><div class='metric-value'>{inspection_date.strftime('%d/%m/%Y')}</div></div>
                    <div class='metric'><div class='metric-label'>Status</div><div class='metric-value'>{status_text}</div></div>
                </div>
                <p><b>Observações:</b> {obs}</p>
            """

            if not is_ok:
                html += "<div class='subsection-header'>Evidência da Não Conformidade</div>"
                if pd.notna(photo_nc_link) and photo_nc_link.strip():
                    html += f"<img src='{photo_nc_link}' class='evidence-img'><br><a href='{photo_nc_link}' target='_blank'>Abrir link da foto</a>"
                else:
                    html += "<p>Nenhuma foto de não conformidade foi anexada.</p>"
                
                html += "<div class='subsection-header'>Ação Corretiva</div>"
                action_info = "<i>Ação Corretiva Pendente.</i>"
                if not df_action_log.empty:
                    action = df_action_log[(df_action_log['id_equipamento'].astype(str) == str(ext_id)) & (df_action_log['data_correcao_dt'] >= inspection_date)].sort_values(by='data_correcao_dt')
                    if not action.empty:
                        action_taken = action.iloc[0]
                        action_photo_link = action_taken.get('link_foto_evidencia')
                        action_info = f"""
                        <p><b>Ação Realizada:</b> {action_taken.get('acao_realizada', 'N/A')}</p>
                        <p><b>Responsável:</b> {action_taken.get('responsavel_acao', 'N/A')}</p>
                        <p><b>Data da Correção:</b> {pd.to_datetime(action_taken['data_correcao_dt']).strftime('%d/%m/%Y')}</p>
                        """
                        if pd.notna(action_photo_link) and action_photo_link.strip():
                            action_info += f"<img src='{action_photo_link}' class='evidence-img'><br><a href='{action_photo_link}' target='_blank'>Abrir link da evidência</a>"
                        else:
                            action_info += "<p>Nenhuma foto da ação corretiva anexada.</p>"
                html += action_info

            html += "</div>" # Fecha o inspection-item

    html += "</body></html>"
    return html

def show_monthly_report_interface():
    """Função principal que desenha a interface de geração de relatórios."""
    st.title("📄 Emissão de Relatórios Mensais")
    
    today = datetime.now()
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Selecione o Ano:", range(today.year, today.year - 5, -1), key="report_year")
    with col2:
        months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        default_month_index = today.month - 2 if today.day < 5 else today.month - 1
        selected_month_name = st.selectbox("Selecione o Mês:", months, index=default_month_index, key="report_month_name")
        
    if st.button("Gerar e Imprimir Relatório", type="primary", key="generate_report_btn"):
        year = st.session_state.report_year
        month = months.index(selected_month_name) + 1
        
        with st.spinner(f"Gerando relatório para {month:02d}/{year}..."):
            df_inspections = load_sheet_data("extintores")
            df_action_log = load_sheet_data("log_acoes")

            if not df_inspections.empty:
                df_inspections['data_servico'] = pd.to_datetime(df_inspections['data_servico'], errors='coerce')
                mask = (df_inspections['data_servico'].dt.year == year) & \
                       (df_inspections['data_servico'].dt.month == month) & \
                       (df_inspections['tipo_servico'] == 'Inspeção')
                df_inspections_month = df_inspections[mask].sort_values(by='data_servico')
            else:
                df_inspections_month = pd.DataFrame()
            
            # 1. Gera o HTML completo do relatório
            report_html = generate_report_html(df_inspections_month, df_action_log, month, year)
            
            # 2. Prepara o código JavaScript para injetar o HTML e imprimir
            #    Usamos JSON.stringify para passar a string HTML de forma segura.
            js_code = f"""
                const reportHtml = {pd.io.json.dumps(report_html)};
                const printWindow = window.open('', '_blank');
                printWindow.document.write(reportHtml);
                printWindow.document.close();
                printWindow.focus();
                setTimeout(() => {{ printWindow.print(); }}, 500); // Pequeno delay para garantir que as imagens carreguem
            """
            
            # 3. Executa o JavaScript
            streamlit_js_eval(js_expressions=js_code, key="print_report_js")
