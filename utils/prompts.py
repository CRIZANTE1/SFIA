def get_extinguisher_inspection_prompt():
    """
    Retorna um prompt robusto e inteligente para extrair dados de relatórios de extintores,
    determinando automaticamente o nível de serviço para cada item.
    """
    return """
    Você é um especialista em analisar relatórios de inspeção e manutenção de extintores de incêndio.
    Sua tarefa é analisar o relatório PDF fornecido e extrair informações detalhadas para CADA extintor listado.
    O identificador principal e permanente é o "N° DO CILINDRO / RECIPIENTE" ou "Extin.".

    **Para cada extintor (cada linha da tabela), extraia os seguintes campos:**

    1.  `tipo_servico`: **CAMPO ESSENCIAL.** Determine o tipo de serviço com a seguinte prioridade:
        *   **Primeiro**, verifique se a coluna "MANUTENÇÃO NÍVEL" existe. Se o valor for '3', retorne "Manutenção Nível 3".
        *   **Se não for 3**, verifique se o valor é '2'. Se sim, retorne "Manutenção Nível 2".
        *   **Se a coluna não existir ou não for 2 ou 3**, verifique a coluna "Nivel da Inspeção". Se o valor for '1', retorne "Inspeção".
        *   Use "Inspeção" como valor padrão se nenhuma das condições acima for atendida.

    2.  `numero_identificacao`: Extraia da coluna "N° DO CILINDRO / RECIPIENTE". Este é o campo chave.
    3.  `numero_selo_inmetro`: Extraia da coluna "N° SELO INMETRO".
    4.  `tipo_agente`: Extraia da coluna "Tipo" ou "TIPO".
    5.  `capacidade`: Extraia da coluna "CAPAC. CARGA" ou do tipo (ex: "PQS 4,5KG").
    6.  `marca_fabricante`: Extraia da coluna "FABRIC. OU MARCA".
    7.  `ano_fabricacao`: Extraia da coluna "ANO FABRIC.".
    8.  `data_servico`: Use a data global do relatório (ex: "Data saída....:" ou a data no cabeçalho). Formato YYYY-MM-DD.
    9.  `empresa_executante`: Nome da empresa que realizou o serviço.
    10. `inspetor_responsavel`: Nome do responsável técnico.
    11. `aprovado_inspecao`: Da coluna "STATUS" ou "INSPEÇÃO FINAL" ('CONFORME'/'A' = "Sim", 'N/CONFORME'/'R' = "Não").
    12. `observacoes_gerais`: Da coluna "Alterações" ou "PEÇA". Use legendas para decodificar

    **Formato de Saída OBRIGATÓRIO:**
    Retorne a resposta APENAS como um objeto JSON com uma chave "extintores" contendo uma LISTA de objetos,
    onde cada objeto representa um extintor.

    Exemplo de formato de saída obrigatório:
    {
      "extintores": [
        {
          "tipo_servico": "Manutenção Nível 2",
          "numero_identificacao": "20579",
          "numero_selo_inmetro": "306472069",
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
