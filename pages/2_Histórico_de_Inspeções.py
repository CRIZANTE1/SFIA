import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from operations.history import load_sheet_data
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_admin_user
from operations.demo_page import show_demo_page

def make_link_clickable(link):
    """Transforma um link de texto em uma tag HTML clicável, se for uma URL válida."""
    if isinstance(link, str) and link.startswith('http'):
        return f'<a href="{link}" target="_blank">Ver Relatório</a>'
    return "N/A"

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

    # Garante que a coluna do link exista para evitar erros, caso a planilha esteja desatualizada
    if 'link_relatorio_pdf' not in df_inspections.columns:
        df_inspections['link_relatorio_pdf'] = "N/A"
    else:
        # Preenche valores vazios com N/A antes de aplicar a função
        df_inspections['link_relatorio_pdf'].fillna("N/A", inplace=True)

    # Cria uma cópia para exibição com links clicáveis
    df_display = df_inspections.copy()
    df_display['link_relatorio_pdf'] = df_display['link_relatorio_pdf'].apply(make_link_clickable)

    st.markdown("---")
    st.subheader("Buscar Registro por Selo INMETRO")
    search_id = st.text_input("Digite o número do Selo INMETRO:", key="search_id_input", placeholder="Ex: 21769")

    # DataFrame a ser exibido: filtrado ou completo
    if search_id:
        # Busca no DataFrame original (sem HTML) e depois aplica a formatação
        result_df = df_inspections[df_inspections['numero_selo_inmetro'].astype(str) == search_id]
        if not result_df.empty:
            st.markdown(f"### Histórico para o Selo: {search_id}")
            # Cria uma cópia do resultado para não alterar o original
            display_result = result_df.copy()
            display_result['link_relatorio_pdf'] = display_result['link_relatorio_pdf'].apply(make_link_clickable)
            # Exibe o resultado da busca
            st.markdown(display_result.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info(f"Nenhum registro encontrado para o selo: {search_id}")
        
        # Oculta a tabela completa quando uma busca é realizada para focar no resultado
        st.markdown("---")
        if st.button("Limpar Busca e Ver Histórico Completo"):
            st.rerun()
            
    else:
        st.subheader("Histórico Completo de Todos os Serviços")
        # Usa to_html para renderizar a tabela completa com links clicáveis
        st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)


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
