# Manual do Pipeline de Vendas

## Sumário

## Visão geral

O pipeline carrega os pedidos diários do ERP para o **Lakehouse** e atualiza o modelo semântico `VENDAS_HOLDING_PRD`.

> Este documento é um exemplo fictício usado para demonstrar o Gera Documents.

## Arquitetura

| Camada | Tecnologia | Responsável |
|---|---|---|
| Ingestão | Data Pipeline | Engenharia de Dados |
| Transformação | Notebook PySpark | Engenharia de Dados |
| Consumo | Power BI Direct Lake | BI |

## Operação

1. Confira o status da execução diária.
2. Em caso de falha, reprocesse a partição:

```python
reprocessar(data_carga="2026-10-26")
```

- Prazo de atualização: **06:00**
- Alertas: `#dados-alertas`
