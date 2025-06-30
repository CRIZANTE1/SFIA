## SFIA - Sistema de Fiscalização por Inteligência Artificial
## Descrição do Projeto

O SFIA (Sistema de Fiscalização por Inteligência Artificial) é uma aplicação web desenvolvida para otimizar e padronizar o processo de inspeção de equipamentos de combate a incêndio, como extintores. Ele garante a conformidade com as normas e aumenta a segurança, utilizando inteligência artificial para extrair dados de relatórios em PDF e gerenciar o histórico de inspeções.

## Funcionalidades

- **Autenticação de Usuário**: Sistema de login para acesso seguro, com diferenciação entre usuários administradores e de demonstração.
- **Inspeção de Extintores (Registro em Lote)**: Permite o upload de relatórios PDF para extração automática de dados de extintores via IA.
- **Inspeção Rápida por QR Code**: Realiza inspeções rápidas de extintores existentes através da leitura de QR Code.
- **Histórico de Inspeções**: Consulta e gerenciamento de todas as inspeções realizadas, com dados centralizados em Google Sheets.
- **Cálculo Automático de Vencimentos**: Calcula automaticamente as próximas datas de inspeção e manutenção.
- **Geração de Planos de Ação**: Gera planos de ação padronizados para extintores "Não Conformes".
🛠️ Tecnologias Utilizadas
Frontend: Streamlit
Inteligência Artificial: Google AI (Gemini)
Backend & Banco de Dados: Google Sheets
Linguagem: Python 3.9+
Bibliotecas Principais: pandas, google-api-python-client, google-auth-oauthlib, opencv-python-headless, pyzbar, python-dateutil.
⚙️ Configuração e Instalação
Para executar este projeto localmente, siga os passos abaixo.
1. Pré-requisitos
Python 3.9 ou superior instalado.
Uma conta Google e um projeto no Google Cloud Platform.
2. Clone o Repositório
Generated bash
git clone <URL_DO_SEU_REPOSITORIO>
cd <NOME_DA_PASTA_DO_PROJETO>
Use code with caution.
Bash
3. Crie um Ambiente Virtual e Instale as Dependências
É uma boa prática usar um ambiente virtual para isolar as dependências do projeto.
Generated bash
# Criar ambiente virtual
python -m venv venv

# Ativar o ambiente (Windows)
.\venv\Scripts\activate

# Ativar o ambiente (Linux/macOS)
source venv/bin/activate

# Instalar as bibliotecas
pip install -r requirements.txt
Use code with caution.
Bash
4. Configure as Credenciais do Google
Esta é a parte mais importante. O aplicativo precisa de credenciais para acessar o Google Sheets, Google Drive e a API de IA.
Habilite as APIs no Google Cloud:
Vá para o seu projeto no Google Cloud Console.
Habilite as seguintes APIs: Google Drive API, Google Sheets API e Generative AI API (ou Vertex AI API).
Crie uma Conta de Serviço (para acesso ao Google Sheets/Drive):
Em "IAM & Admin" > "Service Accounts", crie uma nova conta de serviço.
Dê a ela um nome (ex: sfia-sheets-editor).
Crie uma chave para esta conta no formato JSON e faça o download. Renomeie este arquivo para credentials.json e coloque-o na pasta gdrive/. Não adicione este arquivo ao Git.
Compartilhe sua Planilha Google e a Pasta no Google Drive com o e-mail da conta de serviço que você acabou de criar (ex: sfia-sheets-editor@<seu-projeto>.iam.gserviceaccount.com), dando a ela permissão de "Editor".
Crie uma Credencial OAuth 2.0 (para Login de Usuário):
Em "APIs & Services" > "Credentials", crie uma nova "OAuth 2.0 Client ID".
Selecione "Web application".
Em "Authorized redirect URIs", adicione: http://localhost:8501
Salve e copie o Client ID e o Client Secret.
Crie o arquivo secrets.toml:
Na raiz do projeto, crie uma pasta chamada .streamlit.
Dentro dela, crie um arquivo chamado secrets.toml.
Cole o conteúdo abaixo no arquivo e preencha com suas próprias credenciais.
Generated toml
# .streamlit/secrets.toml

# Credenciais para a API do Google Gemini
[general]
GOOGLE_API_KEY = "SUA_API_KEY_DO_GEMINI"

# Credenciais da Conta de Serviço (para acesso ao Google Sheets)
[connections.gsheets]
type = "service_account"
project_id = "SEU_ID_DE_PROJETO_GOOGLE_CLOUD"
private_key_id = "ID_DA_CHAVE_PRIVADA_DO_JSON"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n" # Copie e cole a chave inteira do JSON, mantendo as quebras de linha
client_email = "EMAIL_DA_CONTA_DE_SERVIÇO"
client_id = "ID_DA_CONTA_DE_SERVIÇO_DO_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "URL_DO_CERTIFICADO_X509_DO_JSON"
universe_domain = "googleapis.com"

# Configuração para o Login OIDC do Streamlit
[oidc]
google_client_id = "SEU_CLIENT_ID_OAUTH_2.0"
google_client_secret = "SEU_CLIENT_SECRET_OAUTH_2.0"
google_redirect_uri = "http://localhost:8501" # Mantenha como está para testes locais
cookie_secret = "GERAR_UM_SEGREDO_FORTE_E_ALEATORIO" # Use um gerador de senhas para criar uma string longa e aleatória
cookie_expiry_days = 30
Use code with caution.
Toml
5. Configure a Planilha Google
Crie uma nova Planilha Google.
Pegue o ID da planilha da URL (ex: .../d/ESTE_EH_O_ID/edit...) e coloque-o em gdrive/config.py.
Crie duas abas com os nomes exatos:
extintores
adm
Na aba adm, crie uma coluna na célula A1 com o título Nome. Adicione abaixo os nomes dos usuários do Google que terão acesso de administrador.
Na aba extintores, cole a seguinte linha de cabeçalho na célula A1:
Generated code
numero_identificacao	tipo_agente	capacidade	marca_fabricante	ano_fabricacao	tipo_servico	data_servico	inspetor_responsavel	empresa_executante	data_proxima_inspecao	data_proxima_manutencao_2_nivel	data_proxima_manutencao_3_nivel	data_ultimo_ensaio_hidrostatico	aprovado_inspecao	observacoes_gerais	plano_de_acao
Use code with caution.
🚀 Como Executar
Após concluir a configuração, execute o seguinte comando no terminal (com o ambiente virtual ativado):
Generated bash
streamlit run Pagina_Inicial.py
Use code with caution.
Bash
O aplicativo será aberto no seu navegador.
📁 Estrutura do Projeto
Generated code
sfia-extintores/
├── .streamlit/
│   └── secrets.toml        # ⚠️ Arquivo de segredos (NÃO versionar no Git)
├── AI/
│   ├── api_Operation.py    # Lógica de interação com a API Gemini
│   └── ...
├── auth/
│   ├── auth_utils.py       # Funções de verificação de login e admin
│   └── login_page.py       # Componentes da interface de login
├── gdrive/
│   ├── config.py           # IDs de planilhas/pastas e credenciais
│   └── gdrive_upload.py    # Funções para upload e manipulação de planilhas
├── operations/
│   ├── extinguisher_operations.py # Lógica de negócio para inspeções
│   └── history.py          # Função para carregar dados históricos
├── pages/
│   ├── 1_Inspecao_de_Extintores.py # Página principal com abas de inspeção
│   └── 2_Historico_de_Inspecoes.py # Página para visualizar o histórico
├── utils/
│   └── prompts.py          # Armazena os prompts da IA
├── Pagina_Inicial.py       # Ponto de entrada da aplicação
├── requirements.txt        # Dependências do projeto
└── README.md               # Este arquivo
Use code with caution.
📄 Licença
Copyright 2024, Cristian Ferreira Carlos. Todos os direitos reservados.
O uso, redistribuição ou modificação deste código é estritamente proibido sem a permissão expressa do autor.

## 👤 Autor
Cristian Ferreira Carlos
LinkedIn

