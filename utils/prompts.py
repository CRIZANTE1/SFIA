# utils/prompts.py

def get_extinguisher_inspection_prompt():
    """
    Retorna um prompt robusto para extrair dados de diferentes tipos de relatórios de extintores
    (Inspeção Nível 1 e Manutenção Nível 2/3), seguindo a NBR 12962.
    """
    return """
    Você é um especialista em analisar relatórios de inspeção e manutenção de extintores de incêndio.
    Sua tarefa é analisar o relatório PDF fornecido, que contém uma lista tabular de múltiplos
    extintores, e extrair informações detalhadas para CADA extintor listado.

    **Instruções de Análise:**

    1.  **Identifique o Contexto:** Primeiro, determine o tipo de relatório.
        *   **Relatório de Inspeção (Nível 1):** Geralmente mais simples, focado em "STATUS" (CONFORME/N/CONFORME) e "Alterações". A data é proeminente no cabeçalho ela ocorre mensalmente.
        *   **Relatório de Manutenção (Nível 2/3):** Mais complexo, com colunas como "ANO FABRIC.", "ÚLTIMO TESTE", e detalhes de componentes e ensaios.

    2.  **Extraia Dados Globais:** Identifique informações que se aplicam a todos os extintores, como a data do relatório (use a data mais proeminente, como '27/01/2025' ou 'Data saída'), a empresa executante e o responsável técnico.

    3.  **Processe Cada Linha da Tabela:** Para cada extintor na tabela, extraia os seguintes campos:

    **Campos a Extrair:**

    *   `numero_identificacao`: Extraia da coluna "Extin.". Se o valor for "S/N", mantenha como "S/N".
    *   `tipo_agente`: Extraia da coluna "Tipo". (Ex: "PQS", "CO2"). Se incluir capacidade (ex: "PQS 4,5KG"), separe-a.
    *   `capacidade`: Se a capacidade estiver na coluna "Tipo" (ex: "PQS 4,5KG"), extraia-a ("4,5 kg"). Se não, deixe como `null`.
    *   `marca_fabricante`: Se houver uma coluna "FABRIC. OU MARCA", use-a. Caso contrário, se o relatório for simples, deixe como `null`, pois geralmente não é informado em inspeções Nível 1.
    *   `ano_fabricacao`: Se houver uma coluna "ANO FABRIC.", use-a. Caso contrário, deixe como `null`.
    *   `data_servico`: Use a data global identificada no Passo 2. Formate como YYYY-MM-DD.
    *   `empresa_executante`: Use o nome da empresa executante identificado no Passo 2 (ex: "VIBRA ENERGIA" se for interno, ou o nome da contratada se houver).
    *   `inspetor_responsavel`: Use o nome do responsável técnico no final ou cabeçalho do documento (ex:"Renato Busc").
    *   `aprovado_inspecao`: Extraia da coluna "STATUS". Se o valor for "CONFORME", considere "Sim". Se for "N/CONFORME", considere "Não".
    *   `observacoes_gerais`: Extraia da coluna "Alterações". Se o valor for "S/ALTERAÇÕES", deixe a observação vazia ou `null`. Se houver um código de reparo (ex: "7.PINTURA", "8. MANÔMETRO"), use a legenda "Código de reparos" se disponível no documento para descrever a alteração. Adicione também a informação da coluna "Local". Exemplo: "Local: PE 01. Necessita: Pintura (7)".

    **Formato de Saída OBRIGATÓRIO:**
    Retorne a resposta APENAS como um objeto JSON. O objeto deve ter uma única chave chamada "extintores",
    que contém uma LISTA de objetos JSON, onde cada objeto representa um extintor da tabela.

    Exemplo de formato de saída para o Relatório de Inspeção Nível 1:
    {
      "extintores": [
        {
          "numero_identificacao": "38",
          "tipo_agente": "PQS",
          "capacidade": null,
          "marca_fabricante": null,
          "ano_fabricacao": null,
          "data_servico": "2025-01-27",
          "empresa_executante": "VIBRA ENERGIA",
          "inspetor_responsavel": "CRISTIAN CARLOS",
          "aprovado_inspecao": "Sim",
          "observacoes_gerais": "Local: PE 01"
        },
        {
          "numero_identificacao": "10",
          "tipo_agente": "PQS",
          "capacidade": null,
          "marca_fabricante": null,
          "ano_fabricacao": null,
          "data_servico": "2025-01-27",
          "empresa_executante": "VIBRA ENERGIA",
          "inspetor_responsavel": "CRISTIAN CARLOS",
          "aprovado_inspecao": "Não",
          "observacoes_gerais": "Local: PQ DE BOMBAS MB 21 PROX. 1503. Necessita: Pintura (7)"
        }
      ]
    }
    """
