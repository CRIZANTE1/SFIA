import streamlit as st
import pandas as pd
import sys
import os
from config.page_config import set_page_config 

set_page_config()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def format_dataframe_for_display(df):
    """
    Prepara o DataFrame para exibição: apenas seleciona e renomeia as colunas.
    A formatação de links e datas será feita pelo st.dataframe.
    """
    if df.empty:
        return df

    # Garante que a coluna do link exista e preenche valores nulos
    if 'link_relatorio_pdf' not in df.columns:
        df['link_relatorio_pdf'] = None
    df['link_relatorio_pdf'] = df['link_relatorio_pdf'].fillna("N/A")

    # Seleciona e renomeia as colunas na ordem desejada
    # Mantém o nome da coluna original do link para a configuração funcionar
    display_columns = {
        'data_servico': 'Data do Serviço',
        'numero_identificacao': 'ID do Equipamento',
        'numero_selo_inmetro': 'Selo INMETRO',
        'tipo_servico': 'Tipo de Serviço',
        'tipo_agente': 'Agente Extintor',
        'capacidade': 'Capacidade',
        'aprovado_inspecao': 'Status',
        'plano_de_acao': 'Plano de Ação',
        'link_relatorio_pdf': 'Relatório (PDF)' # Renomeia o cabeçalho para exibição
    }
    
    # Filtra apenas as colunas que existem no DataFrame original
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
        st.warning("Ainda não há registros de inspeção no histórico."); return

    # Cria uma cópia para evitar SettingWithCopyWarning
    df_inspections = df_inspections.copy()
    df_inspections['data_servico_dt'] = pd.to_datetime(df_inspections['data_servico'], errors='coerce')
    df_inspections.dropna(subset=['data_servico_dt'], inplace=True)
    
    st.markdown("---")
    
    # --- FILTROS ---
    st.subheader("Filtrar Histórico")
    available_years = sorted(df_inspections['data_servico_dt'].dt.year.unique(), reverse=True)
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Filtrar por Ano:", options=["Todos os Anos"] + available_years)
    with col2:
        search_id = st.text_input("Buscar por ID do Equipamento:", placeholder="Ex: 12345")

    # Aplica os filtros
    filtered_df = df_inspections
    if selected_year != "Todos os Anos":
        filtered_df = filtered_df[filtered_df['data_servico_dt'].dt.year == selected_year]
    if search_id:
        filtered_df = filtered_df[filtered_df['numero_identificacao'].astype(str).str.contains(search_id, na=False)]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")
    else:
        st.subheader("Resultados")
        display_df = format_dataframe_for_display(filtered_df)
        
        # Exibição com column_config corrigido
        st.dataframe(
            display_df,
            column_config={
                "Data do Serviço": st.column_config.DatetimeColumn(
                    "Data do Serviço",
                    format="DD/MM/YYYY",
                ),
                # A configuração agora aponta para a coluna com o nome final
                "Relatório (PDF)": st.column_config.LinkColumn(
                    "Relatório (PDF)",
                    help="Clique para abrir o relatório PDF em uma nova aba",
                    display_text="🔗 Ver Relatório"
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