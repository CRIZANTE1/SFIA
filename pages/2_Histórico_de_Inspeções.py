import streamlit as st
import pandas as pd
import sys
import os
from config.page_config import set_page_config 

# Chama a configuração da página no início
set_page_config()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def format_dataframe_for_display(df):
    """
    Prepara o DataFrame para exibição: renomeia colunas, formata links e datas.
    """
    if df.empty:
        return df

    # Garante que a coluna do link exista
    if 'link_relatorio_pdf' not in df.columns:
        df['link_relatorio_pdf'] = "N/A"
    
    # Cria a coluna de link clicável em formato Markdown
    df['Relatório (PDF)'] = df['link_relatorio_pdf'].apply(
        lambda link: f"[Ver Relatório]({link})" if isinstance(link, str) and link.startswith('http') else "N/A"
    )
    
    # Formata a data de serviço para o formato brasileiro
    df['data_servico'] = pd.to_datetime(df['data_servico']).dt.strftime('%d/%m/%Y')
    
    # Seleciona e renomeia as colunas na ordem desejada
    display_columns = {
        'data_servico': 'Data do Serviço',
        'numero_identificacao': 'ID do Equipamento',
        'numero_selo_inmetro': 'Selo INMETRO',
        'tipo_servico': 'Tipo de Serviço',
        'tipo_agente': 'Agente Extintor',
        'capacidade': 'Capacidade',
        'aprovado_inspecao': 'Status',
        'plano_de_acao': 'Plano de Ação',
        'Relatório (PDF)': 'Relatório (PDF)' # Usa o nome da nova coluna
    }
    
    # Filtra apenas as colunas que existem no DataFrame original para evitar KeyErrors
    cols_to_display = [col for col in display_columns.keys() if col in df.columns]
    
    return df[cols_to_display].rename(columns=display_columns)

def show_history_page():
    st.title("Histórico Completo de Serviços")
    st.info("Os dados são atualizados a cada 10 minutos. Para forçar a atualização, clique no botão abaixo.")
    
    if st.button("Limpar Cache e Recarregar Dados"):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner("Carregando histórico completo..."):
        df_inspections = load_sheet_data("extintores")

    if df_inspections.empty:
        st.warning("Ainda não há registros de inspeção no histórico.")
        return

    # Garante que a coluna de data seja do tipo datetime para poder filtrar
    df_inspections['data_servico'] = pd.to_datetime(df_inspections['data_servico'], errors='coerce')
    df_inspections.dropna(subset=['data_servico'], inplace=True)
    
    st.markdown("---")
    
    # --- FILTROS ---
    st.subheader("Filtrar Histórico")
    
    # Pega os anos disponíveis a partir da coluna de data
    available_years = sorted(df_inspections['data_servico'].dt.year.unique(), reverse=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por Ano
        selected_year = st.selectbox(
            "Filtrar por Ano do Serviço:",
            options=["Todos os Anos"] + available_years
        )

    with col2:
        # Filtro por ID do Equipamento (antigo "Selo INMETRO")
        search_id = st.text_input("Buscar por ID do Equipamento:", placeholder="Ex: 12345")

    # Aplica os filtros
    filtered_df = df_inspections.copy()
    if selected_year != "Todos os Anos":
        filtered_df = filtered_df[filtered_df['data_servico'].dt.year == selected_year]
    
    if search_id:
        filtered_df = filtered_df[filtered_df['numero_identificacao'].astype(str).str.contains(search_id, na=False)]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")
    else:
        st.subheader("Resultados")
        # Prepara o DataFrame para exibição final
        display_df = format_dataframe_for_display(filtered_df)
        
        st.dataframe(
            display_df,
            column_config={
                "Relatório (PDF)": st.column_config.LinkColumn(
                    "Relatório (PDF)",
                    display_text="Ver Relatório"
                )
            },
            hide_index=True,
            use_container_width=True
        )

# --- Boilerplate de Autenticação ---
if not show_login_page(): 
    st.stop()

show_user_header()
show_logout_button()

if is_admin_user():
    st.sidebar.success("✅ Acesso completo")
    show_history_page()
else:
    st.sidebar.error("🔒 Acesso de demonstração")
    show_demo_page()
