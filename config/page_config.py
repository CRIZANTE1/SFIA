import streamlit as st

def set_page_config():
    """
    Define a configuração padrão para todas as páginas do aplicativo.
    """
    st.set_page_config(
        page_title="SFIA - Inspeção de Equipamentos de Emergência",
        page_icon="🔧",
        layout="wide"
    )
