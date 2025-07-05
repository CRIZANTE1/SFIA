import streamlit as st
import sys
import os
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, is_admin_user
from operations.demo_page import show_demo_page
from config.page_config import set_page_config 

set_page_config()

def main():

    
    if not is_user_logged_in():
        show_login_page()
       
        return

  
    show_user_header()
    show_logout_button() 

  
    if is_admin_user():
        st.sidebar.success("✅ Acesso completo")
        
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

    else:
        st.sidebar.error("🔒 Acesso de demonstração")
        show_demo_page()

if __name__ == "__main__":
    main()
    st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
    st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')
