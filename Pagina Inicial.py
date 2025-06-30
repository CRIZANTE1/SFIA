import streamlit as st
import sys
import os
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, is_admin_user
from operations.demo_page import show_demo_page

def main():
    st.set_page_config(
        page_title="SFIA - Inspeção de Equipamentos de Emergência",
        page_icon="🔧",
        layout="wide"
    )

    # 1. Forçar o login antes de mostrar qualquer coisa
    if not show_login_page():
        return # Para a execução se o usuário não estiver logado

    # 2. Mostrar cabeçalho do usuário e botão de sair
    show_user_header()
    show_logout_button()

    # 3. Lógica principal da página
    if is_admin_user():
        # Usuário admin vê a página principal de boas-vindas
        st.sidebar.success("✅ Acesso completo")
        st.title("Bem-vindo ao SFIA!")
        st.subheader("Sistema de Fiscalização por Inteligência Artificial")
        st.markdown("""
        Use a barra de navegação à esquerda para acessar as funcionalidades do sistema.

        - **Inspeção de Extintores**: Registre novas inspeções, extraia dados de relatórios PDF com IA e salve o histórico.
        - **Histórico de Inspeções**: Consulte todas as inspeções já realizadas.
        
        Este sistema foi projetado para otimizar e padronizar o processo de inspeção de equipamentos de combate a incêndio, 
        garantindo conformidade com as normas e segurança.
        """)

    else:
        # Usuário não-admin vê a página de demonstração
        st.sidebar.error("🔒 Acesso de demonstração")
        show_demo_page()

if __name__ == "__main__":
    main()
    st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
    st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')