# Design: Selecao de Estabelecimentos Dentro da Aba Mensagens

## Objetivo

Permitir que a aba `Mensagens` opere como uma central unica de disparo, com:

- selecao manual de estabelecimentos elegiveis para envio
- modo `Manual` para curadoria humana
- modo `Automatico` para aprovar e enfileirar novos resultados de varredura
- fila com rastreabilidade de origem (`manual` ou `automatico`)

## Decisoes

- A aba `Mensagens` passa a ter duas superficies:
  - `Selecionar estabelecimentos`
  - `Fila e scheduler`
- O modo operacional fica persistido em banco para que o backend consiga reagir apos cada varredura.
- `Aprovado` e `Na fila` deixam de ser a mesma coisa:
  - aprovado indica permissao para contato
  - fila indica item pronto para execucao pelo scheduler
- O scheduler passa a processar apenas a fila existente.
- O enfileiramento automatico acontece quando o modo `Automatico` estiver ativo e uma nova varredura concluir com novos leads elegiveis.

## Backend

- Nova configuracao operacional persistida em SQLite:
  - `modo_envio`: `manual` ou `automatico`
- Nova coluna na `fila_disparos`:
  - `origem_disparo`: `manual` ou `automatico`
- Novas capacidades:
  - listar estabelecimentos elegiveis para disparo com estado derivado
  - enfileirar estabelecimentos selecionados manualmente sem duplicar itens pendentes
  - atualizar e consultar o modo operacional da aba `Mensagens`
  - aprovar e enfileirar automaticamente novos leads apos varredura quando o modo automatico estiver ativo

## Frontend

- A aba `Mensagens` ganha:
  - seletor de modo `Manual` e `Automatico`
  - busca e filtros curtos para leads elegiveis
  - selecao por item e em lote
  - acoes `Aprovar`, `Remover aprovacao` e `Adicionar a fila`
  - leitura visual distinta entre curadoria humana e execucao automatizada

## Salvaguardas

- Nao duplicar itens na fila para o mesmo estabelecimento enquanto houver item pendente.
- Nao enfileirar itens sem telefone.
- Respeitar `sem_whatsapp`, `erro` e `enviado` como estados nao elegiveis para novo envio automatico.
- A automacao apos varredura atua apenas sobre novos leads inseridos no processamento atual.

## Validacao

- testes de banco para modo operacional, elegiveis e enfileiramento manual
- testes de API para configuracao do modo, elegiveis e enfileiramento
- testes de scheduler ajustados para operar apenas sobre itens ja enfileirados
- teste de servico de varredura para auto-aprovacao e auto-enfileiramento no modo automatico
