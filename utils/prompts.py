def get_extinguisher_inspection_prompt():
    """
    Retorna um prompt robusto para extrair dados de relatórios de extintores,
    usando o SELO INMETRO como identificador principal.
    """
    return """
    Você é um especialista em analisar relatórios de inspeção e manutenção de extintores de incêndio.
    Sua tarefa é analisar o relatório PDF fornecido e extrair informações para CADA extintor listado.
    O identificador principal e mais importante de cada extintor é o "N° SELO INMETRO".

    **Para cada extintor (cada linha da tabela), extraia os seguintes campos:**

    *   `numero_identificacao`: Extraia da coluna "N° DO CILINDRO / RECIPIENTE" ou "Extin.".
    *   `numero_selo_inmetro`: Extraia da coluna "N° SELO INMETRO". Este é o campo chave.
    *   `tipo_agente`: Extraia da coluna "Tipo" ou "TIPO".
    *   `capacidade`: Extraia da coluna "CAPAC. CARGA" ou do tipo (ex: "PQS 4,5KG").
    *   `marca_fabricante`: Extraia da coluna "FABRIC. OU MARCA".
    *   `ano_fabricacao`: Extraia da coluna "ANO FABRIC.".
    *   `data_servico`: Use a data global do relatório (ex: "Data saída....:" ou a data no cabeçalho). Formato YYYY-MM-DD.
    *   `empresa_executante`: Nome da empresa que realizou o serviço.
    *   `inspetor_responsavel`: Nome do responsável técnico.
    *   `aprovado_inspecao`: Da coluna "STATUS" ou "INSPEÇÃO FINAL" ('CONFORME'/'A' = "Sim", 'N/CONFORME'/'R' = "Não").
    *   `observacoes_gerais`: Da coluna "Alterações" ou "PEÇA". Use legendas para decodificar, se houver. Adicione o "Local" se disponível.

    **Formato de Saída OBRIGATÓRIO:**
    Retorne a resposta APENAS como um objeto JSON com uma chave "extintores" contendo uma LISTA de objetos,
    onde cada objeto representa um extintor.

    Exemplo de formato de saída:
    {
      "extintores": [
        {
          "numero_identificacao": "16500",
          "numero_selo_inmetro": "306472073",
          "tipo_agente": "CO2",
          "capacidade": "6 kg",
          "marca_fabricante": "KB",
          "ano_fabricacao": "2021",
          "data_servico": "2024-10-08",
          "empresa_executante": "Extintores Armênia",
          "inspetor_responsavel": "Renato Busch",
          "aprovado_inspecao": "Sim",
          "observacoes_gerais": "Peças verificadas: 16/51/23/22/24/52/48"
        }
      ]
    }
    """
