import streamlit as st

def show_demo_page():
    """
    Exibe uma página de demonstração para usuários não autorizados,
    com informações sobre o sistema de inspeção de extintores.
    """
    st.title("Sistema de Gestão de Inspeções de Incêndio")

    # URL do vídeo de demonstração (você pode inserir o link aqui depois)
    video_url = 'https://youtu.be/h7DSCUAzHsE' 
    if video_url:
        st.video(video_url)
    else:
        # Mostra um placeholder se não houver vídeo
        st.info("Vídeo de demonstração em breve.")

    st.header("Versão de Demonstração")
    st.warning("🔒 Acesso restrito. Esta é uma versão de demonstração apenas para visualização.")
    
    st.markdown("""
    Você está vendo esta página porque seu usuário não tem permissão de administrador para acessar a versão completa da aplicação.

    ### Funcionalidades da Versão Completa:
    - **🤖 Extração em Lote com IA**: Faça o upload de relatórios de inspeção ou manutenção em PDF e a Inteligência Artificial extrai e cataloga os dados de todos os extintores automaticamente.
    - **📱 Inspeção Rápida em Campo**: Use a câmera do seu celular para escanear o QR Code de um equipamento, registrar uma inspeção de Nível 1 e capturar a geolocalização do ponto em segundos.
    - **🗺️ Mapa Interativo de Equipamentos**: Visualize a localização de todos os seus extintores em um mapa, com cores e tamanhos que indicam o tipo e a capacidade de cada um.
    - **📊 Dashboard de Status em Tempo Real**: Tenha uma visão clara de quais equipamentos estão "OK", "Vencidos" ou "Não Conforme", com planos de ação sugeridos para cada pendência.
    - **📋 Gestão de Ações Corretivas**: Registre a resolução de problemas, incluindo a substituição de equipamentos, mantendo um log completo para auditorias.
    - **⚙️ Utilitários do Sistema**: Gere QR Codes para seus equipamentos diretamente da plataforma.

    ---
    
    **Para obter acesso completo, por favor, entre em contato com o administrador do sistema.**
    """)
    
    try:
        # Tenta obter o nome do usuário logado para facilitar o pedido de acesso
        if hasattr(st.user, 'name') and st.user.name:
            user_name = st.user.name
            st.info(f"Seu nome de login é: **{user_name}**. Se você acredita que deveria ter acesso, forneça este nome ao administrador.")
        else:
            st.info("Para obter acesso, entre em contato com o administrador do sistema.")
    except Exception:
        st.info("Para obter acesso, entre em contato com o administrador do sistema.")
