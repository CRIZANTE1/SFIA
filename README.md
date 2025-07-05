# SFIA - Sistema de Fiscalização por Inteligência Artificial
### Gerenciador de Inspeções de Equipamentos de Combate a Incêndio

Este é um aplicativo web desenvolvido com Streamlit para otimizar e modernizar o processo de inspeção e manutenção de extintores de incêndio. A ferramenta utiliza a API Generative AI do Google (Gemini) para extrair dados de relatórios em PDF, automatiza o cálculo de vencimentos e planos de ação, centraliza todos os registros em uma planilha Google Sheets e oferece um conjunto de dashboards e mapas para uma gestão visual e proativa.

O objetivo é aumentar a eficiência, padronizar os registros de acordo com as normas e fornecer um sistema de gestão completo para a segurança contra incêndio.

## ✨ Funcionalidades Principais

*   **🔐 Autenticação Nativa (OIDC):** Sistema de login seguro via Google (OIDC) integrado ao Streamlit, com diferenciação entre usuários administradores (acesso completo) e usuários de demonstração (acesso restrito).
*   **🤖 Extração com IA (Registro em Lote):** Faça o upload de um relatório de manutenção em PDF e a IA extrai automaticamente os dados de todos os extintores listados, economizando horas de digitação manual.
*   **📱 Inspeção Rápida Georreferenciada:** Utilize a câmera do celular para escanear o QR Code de um extintor, visualizar seu status, capturar a geolocalização exata (GPS) e registrar uma nova inspeção de Nível 1 em segundos.
*   **📊 Dashboard de Situação Atual:** Um painel de controle central que exibe métricas em tempo real (Total, OK, Vencido, Não Conforme) e permite a gestão de pendências.
*   **🗺️ Mapa Interativo do SCI:** Visualize todos os equipamentos em um mapa, com cores por tipo e tamanho por capacidade, usando os dados de geolocalização capturados durante as inspeções.
*   **✍️ Gestão de Ações Corretivas:** Para cada equipamento "Não Conforme", registre ações corretivas, anexe fotos de evidência e gerencie a substituição de equipamentos, mantendo um log detalhado de todas as ações.
*   **📷 Registro Fotográfico:** Anexe fotos de não conformidades durante as inspeções ou como evidência de ações corretivas, com upload automático para o Google Drive.
*   **🗓️ Cálculo Automático de Vencimentos:** Com base na data e no nível do serviço, o sistema calcula automaticamente as próximas datas de inspeção e manutenções.
*   **📋 Geração de Planos de Ação Inteligentes:** Para cada não conformidade, o sistema sugere um plano de ação padronizado, transformando registros em tarefas gerenciáveis.
*   **🛠️ Utilitário Gerador de QR Codes:** Gere QR Codes em lote para seus equipamentos, prontos para impressão e fixação.
*   **📚 Histórico Centralizado e Pesquisável:** Todos os registros são salvos e podem ser visualizados, filtrados e pesquisados diretamente na aplicação.

## 🛠️ Tecnologias Utilizadas

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **Inteligência Artificial:** [Google AI (Gemini)](https://ai.google.dev/)
*   **Backend & Banco de Dados:** [Google Sheets](https://www.google.com/sheets/about/) e [Google Drive](https://www.google.com/drive/)
*   **Linguagem:** Python 3.9+
*   **Autenticação:** Google OIDC via Authlib

## 📄 Licença e Uso

Copyright 2024, Cristian Ferreira Carlos. Todos os direitos reservados.

Este é um software proprietário. O uso, redistribuição, cópia ou modificação deste código é estritamente proibido sem a permissão expressa do autor. O acesso à aplicação é feito através de credenciais autorizadas.

## 👤 Autor

**Cristian Ferreira Carlos**
*   [LinkedIn](https://www.linkedin.com/in/cristian-ferreira-carlos-256b19161/)
👤 Autor
Cristian Ferreira Carlos
LinkedIn

