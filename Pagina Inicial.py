import streamlit as st
import sys
import os
from auth.login_page import show_login_page, show_user_header, show_logout_button
from auth.auth_utils import is_user_logged_in, is_admin_user
from operations.demo_page import show_demo_page

# Configuração da página no topo para ser aplicada globalmente
st.set_page_config(
    page_title="SFIA - Inspeção de Equipamentos de Emergência",
    page_icon="🔧",
    layout="wide"
)

def main():
    # --- Verificação de Login ANTES de qualquer outra coisa ---
    # A função show_login_page já exibe a tela de login se necessário.
    # Ela retorna False se o usuário não estiver logado.
    if not is_user_logged_in():
        show_login_page()
        # Para a execução aqui, garantindo que nada mais seja renderizado
        # para um usuário não logado, incluindo o conteúdo da sidebar.
        return

  
    show_user_header()
    show_logout_button() # Esta função já coloca o botão na sidebar.

    # Lógica de permissão para o conteúdo principal
    if is_admin_user():
        st.sidebar.success("✅ Acesso completo")
        
        st.title("Bem-vindo ao SFIA!")
        st.subheader("Sistema de Fiscalização por Inteligência Artificial")
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
    # Os rodapés podem ficar fora da função main
    st.caption('Copyright 2024, Cristian Ferreira Carlos, Todos os direitos reservados.')
    st.caption('https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/')
