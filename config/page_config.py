import streamlit as st
import os

def set_page_config():
    """
    Define a configuração padrão para todas as páginas do aplicativo
    e carrega o CSS customizado para formatação e impressão.
    """
    st.set_page_config(
        page_title="ISF IA - Sistema de Inspeções com IA",
        page_icon="🔧",
        layout="wide"
    )

    css_file_path = os.path.join(os.path.dirname(__file__), '..', 'style', 'style.css')
    
    try:
        with open(css_file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Arquivo 'style/style.css' não encontrado. A formatação de impressão pode não ser a ideal.")
