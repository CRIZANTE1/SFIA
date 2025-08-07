import streamlit as st
import sys
import os
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, is_admin, can_edit, can_view, get_user_role
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 

set_page_config()

def show_admin_homepage():
    """Conteúdo completo para administradores."""
    st.sidebar.success("👑 Acesso de Administrador")
    st.title("Bem-vindo ao ISF IA!")
    st.subheader("Sistema de Fiscalização e Inspeções com Inteligência Artificial")
    st.markdown("""
    Use a barra de navegação à esquerda para acessar as funcionalidades do sistema.

    - **Inspeção de Extintores**: Registre novas inspeções, extraia dados de relatórios PDF com IA e salve o histórico.
    - **Situação Atual**: Visualize um dashboard com o status de todos os equipamentos.
    - **Histórico de Inspeções**: Consulte todos os registros já realizados.
    
    Este sistema foi projetado para otimizar e padronizar o processo de inspeção de equipamentos de combate a incêndio, 
    garantindo conformidade com as normas e segurança.
    """)

def show_editor_homepage():
    """Conteúdo para editores (pode ser o mesmo do admin ou um pouco diferente)."""
    st.sidebar.info("✏️ Acesso de Editor")
    st.title("Bem-vindo ao ISF IA!")
    st.subheader("Sistema de Fiscalização e Inspeções com Inteligência Artificial")
    st.markdown("""
    Você tem permissão para registrar novas inspeções e atualizar o status dos equipamentos.
    Use a barra de navegação à esquerda para acessar as funcionalidades de edição.
    """)

def main():
    if not is_user_logged_in():
        show_login_page()
        return

    show_user_header()
    show_logout_button() 

    user_role = get_user_role()

    if user_role == 'admin':
        show_admin_homepage()
        
    elif user_role == 'editor':
        show_admin_homepage() # Reutilizando a função
        
    elif user_role == 'viewer':
        st.sidebar.warning("👁️ Acesso Somente Leitura")
        show_demo_page()

    else:
        st.sidebar.error("🔒 Acesso de Demonstração")
        show_demo_page()

if __name__ == "__main__":
    main()
    st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
    st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')
