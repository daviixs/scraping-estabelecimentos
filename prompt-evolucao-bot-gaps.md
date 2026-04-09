# Analise de Gaps do `prompt-evolucao-bot.md`

Data da analise: 2026-04-09
Projeto analisado: `scraping-de-numeros`

## Resumo executivo

O projeto atual ja entrega a espinha dorsal do sistema:

- scraping por `Google Maps`
- scraping por `Apontador`
- importacao manual por `CSV`
- normalizacao dos dados
- NLP simples de comentarios
- calculo de score de oportunidade
- persistencia em `SQLite`
- dashboard web para consulta
- exportacao `CSV` e `XLSX`
- disparo de novas varreduras pela dashboard

O que ainda nao existe e impede o projeto de atender o documento `prompt-evolucao-bot.md` e, principalmente, todo o bloco de operacao comercial por WhatsApp:

- aprovacao de leads para disparo
- status de WhatsApp por estabelecimento
- fila de disparos persistida
- modulo `whatsapp/` com integracao Evolution API v3
- scheduler com intervalo de 30 minutos, janela de envio e limite diario
- rotas Flask para aprovacao, fila e controle de disparo
- interface da dashboard para operar o fluxo comercial

## O que ja esta pronto

### 1. Coleta de dados

Ja existe implementacao funcional para:

- `scraper/google_maps.py`
- `scraper/apontador.py`
- `scraper/csv_importer.py`

Cobertura atual:

- Google Maps com Playwright
- Apontador com Playwright e paginacao
- CSV manual com pipeline compativel com o banco

Observacao:

- o importador CSV atual aceita `nome` e campos opcionais como `telefone`, `cidade`, `categoria`, `site` e `url/link`
- isso atende o caso manual, embora a documentacao do prompt esteja mais fechada que a implementacao real

### 2. Processamento

Ja existe implementacao funcional para:

- `processor/normalizer.py`
- `processor/nlp_comments.py`
- `processor/scorer.py`
- `database/history.py`

Cobertura atual:

- classificacao por nota
- score 0-100 com pesos configuraveis
- prioridade `ALTA`, `MEDIA` e `BAIXA`
- resumo de queixas por palavras-chave
- deteccao de queda de reputacao com base em historico

### 3. Banco de dados

Ja existe implementacao funcional para:

- `database/schema.sql`
- `database/db_manager.py`

Tabelas existentes:

- `estabelecimentos`
- `coletas_historico`
- `comentarios`
- `queixas_categorias`

Cobertura atual:

- inicializacao do schema
- upsert de estabelecimento por `(nome, cidade)`
- historico de coletas
- persistencia de comentarios
- persistencia de categorias de queixa
- listagem filtrada e paginada
- resumo para KPIs
- consultas para exportacao

### 4. Dashboard e API

Ja existe implementacao funcional para:

- `dashboard.py`
- `templates/index.html`
- `frontend/src/components/DashboardApp.tsx`
- `frontend/src/components/ScanCommander.tsx`

Rotas atuais:

- `GET /`
- `GET /api/estabelecimentos`
- `GET /api/resumo`
- `GET /api/cidades`
- `GET /api/categorias`
- `POST /api/varreduras`
- `GET /api/varreduras/<job_id>`
- `GET /api/varreduras/ativa`
- `GET /api/export/csv`
- `GET /api/export/xlsx`

Cobertura atual:

- listagem de estabelecimentos
- filtros por classificacao, prioridade, fonte, cidade, categoria e score minimo
- ordenacao
- paginacao
- KPIs
- exportacao
- execucao e acompanhamento de varreduras

### 5. CLI e testes

Ja existe implementacao funcional para:

- `main.py`
- `tests/test_scorer.py`
- `tests/test_nlp_comments.py`
- `tests/test_db_manager.py`
- `tests/test_dashboard_api.py`
- `tests/test_scan_parser.py`

Cobertura atual:

- CLI para Google Maps, Apontador e CSV
- testes para score, NLP, banco e parte da API Flask

## O que esta parcial ou divergente do prompt

### 1. Dashboard existe, mas nao cobre o fluxo comercial

O prompt pede uma dashboard com:

- aprovacao individual e em lote
- filtro de aprovados
- status WhatsApp
- aba de disparos
- fila operacional de envio
- botoes de iniciar e pausar disparo

O projeto atual tem dashboard, mas ela cobre somente:

- consulta dos estabelecimentos
- filtros
- exportacao
- inicio de novas varreduras

### 2. `requirements.txt` nao bate totalmente com o prompt

Hoje existe:

- `playwright`
- `beautifulsoup4`
- `requests`
- `openpyxl`
- `flask`
- `lxml`
- `python-dotenv`

O prompt espera tambem:

- `apscheduler`
- `pandas`

Leitura pratica:

- `apscheduler` esta realmente faltando para o scheduler de WhatsApp
- `pandas` so deve ser adicionado se a implementacao futura realmente precisar dele

### 3. Frontend atual e maior que o especificado

O prompt descreve `HTML + CSS + JS puro` na dashboard.
O projeto atual tem:

- frontend moderno em Astro/React

Isso nao e um problema funcional, mas precisa ser considerado por quem implementar o que falta:

- ou expande o frontend moderno

## O que nao tem e como fazer

### 1. Campos faltantes na tabela `estabelecimentos`

Nao existem hoje:

- `aprovado_disparo`
- `status_whatsapp`

Como fazer:

- atualizar `database/schema.sql`
- adicionar os dois campos com defaults compativeis:
  - `aprovado_disparo INTEGER DEFAULT 0`
  - `status_whatsapp TEXT DEFAULT 'pendente'`
- garantir migracao segura para bancos ja existentes
- atualizar `database/db_manager.py` para ler, filtrar e atualizar esses campos

### 2. Tabela `fila_disparos`

Nao existe hoje:

- tabela `fila_disparos`

Como fazer:

- adicionar a tabela ao `database/schema.sql`
- criar funcoes em `database/db_manager.py` para:
  - enfileirar disparos
  - listar fila
  - atualizar status, tentativas, erro e data de envio
  - marcar resposta recebida quando esse fluxo for implementado

### 3. Modulo `whatsapp/`

Nao existe hoje:

- pasta `whatsapp/`
- `whatsapp/sender.py`
- `whatsapp/message_builder.py`
- `whatsapp/validator.py`
- `whatsapp/scheduler.py`

Como fazer:

- criar o pacote `whatsapp`
- implementar:
  - `message_builder.py` para gerar mensagem com variacao de abertura
  - `validator.py` para chamar `/chat/whatsappNumbers/{INSTANCE_NAME}`
  - `sender.py` para chamar `/message/sendText/{INSTANCE_NAME}`
  - `scheduler.py` para controlar fila, intervalo, limite diario e janela de envio
- usar `requests` com timeouts e tratamento de erro
- manter toda a integracao configuravel por `config/settings.py`

### 4. Configuracoes da Evolution API e regras de envio

Nao existem hoje em `config/settings.py`:

- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE`
- `INTERVALO_ENTRE_ENVIOS`
- `LIMITE_DIARIO_ENVIOS`
- `JANELA_INICIO_HORA`
- `JANELA_FIM_HORA`
- `MAX_TENTATIVAS`

Como fazer:

- adicionar essas configuracoes em `config/settings.py`
- manter defaults compativeis com o prompt
- opcionalmente permitir override por variaveis de ambiente

### 5. Rotas Flask de aprovacao e disparo

Nao existem hoje:

- `POST /api/aprovar`
- `POST /api/remover-aprovacao`
- `GET /api/fila-disparos`
- `POST /api/disparo/iniciar`
- `POST /api/disparo/pausar`

Como fazer:

- adicionar as rotas em `dashboard.py`
- validar payloads com IDs
- usar `db_manager` para atualizar aprovacoes
- integrar os endpoints de disparo ao scheduler
- retornar snapshots operacionais claros para a UI

### 6. Filtros e colunas de disparo na listagem principal

Nao existem hoje na dashboard:

- checkbox por linha
- selecao em lote
- aprovar selecionados
- remover aprovacao dos selecionados
- filtro por aprovados
- coluna `aprovado_disparo`
- coluna `status_whatsapp`

Como fazer:

- atualizar a UI principal no frontend moderno
- decidir se o fallback em `templates/index.html` tambem sera atualizado
- adaptar `GET /api/estabelecimentos` para aceitar:
  - filtro de status WhatsApp
  - filtro de aprovados
- expor esses campos na resposta da API

### 7. Aba ou painel de disparos WhatsApp

Nao existe hoje na dashboard:

- area operacional da fila de disparos
- status do scheduler
- contador de enviados hoje
- mensagem enviada
- erro por item
- proximo envio previsto

Como fazer:

- criar um segundo painel ou aba no frontend
- consumir:
  - `GET /api/fila-disparos`
  - `POST /api/disparo/iniciar`
  - `POST /api/disparo/pausar`
- exibir regras de operacao:
  - intervalo de 30 minutos
  - janela de envio
  - limite diario

### 8. Testes dos fluxos novos

Nao existem hoje:

- testes para aprovacao de disparo
- testes para fila de disparos
- testes do scheduler
- testes da integracao Evolution com mocks
- testes das novas rotas Flask

Como fazer:

- adicionar testes unitarios para `message_builder`, `validator`, `sender` e `scheduler`
- mockar chamadas HTTP da Evolution API
- criar fixtures SQLite para fila e aprovacao
- validar comportamento de tentativas, horario util e limite diario

### 9. README e documentacao operacional

Nao existe hoje:

- documentacao do fluxo de aprovacao e envio WhatsApp
- configuracao da Evolution API
- descricao do scheduler

Como fazer:

- atualizar `README.md`
- incluir setup da Evolution API
- incluir variaveis/configuracoes
- incluir fluxo da dashboard para aprovar e disparar

## Ordem recomendada de implementacao

1. Atualizar schema e camada `db_manager`
2. Adicionar configuracoes novas em `settings.py`
3. Criar pacote `whatsapp/`
4. Implementar scheduler e estado operacional
5. Expor novas rotas Flask
6. Atualizar frontend principal e painel de disparos
7. Escrever testes
8. Atualizar `requirements.txt` e `README.md`

## Prompt unico para implementar tudo o que falta

Use o prompt abaixo em outra IA ou como base de execucao para completar o projeto:

```text
Voce esta evoluindo um projeto Python local chamado `scraping-de-numeros`.

O projeto ja possui:
- scraping de Google Maps, Apontador e CSV
- pipeline de normalizacao, NLP simples e score de oportunidade
- persistencia em SQLite
- dashboard Flask para consulta, filtros, exportacao e execucao de varreduras

Seu objetivo e implementar tudo o que falta para o projeto cumprir a especificacao do arquivo `prompt-evolucao-bot.md`, sem quebrar o que ja funciona hoje.

Regras obrigatorias:
- preserve scraping, score, exportacao e dashboard atuais
- faca mudancas compativeis com o banco SQLite existente
- prefira migracao defensiva a reset do banco
- mantenha a arquitetura atual baseada em Flask + SQLite
- nao introduza Redis, Celery, fila externa ou servicos extras
- use mocks nos testes para chamadas da Evolution API

Implemente os seguintes itens:

1. Banco de dados
- Atualize `database/schema.sql` para incluir na tabela `estabelecimentos`:
  - `aprovado_disparo INTEGER DEFAULT 0`
  - `status_whatsapp TEXT DEFAULT 'pendente'`
- Adicione a tabela `fila_disparos` com os campos:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `estabelecimento_id INTEGER REFERENCES estabelecimentos(id)`
  - `telefone TEXT`
  - `mensagem TEXT`
  - `status TEXT DEFAULT 'pendente'`
  - `tentativas INTEGER DEFAULT 0`
  - `data_agendamento TEXT`
  - `data_envio TEXT`
  - `erro_descricao TEXT`
  - `resposta_recebida INTEGER DEFAULT 0`
- Garanta inicializacao e migracao compativel para bancos ja existentes.

2. Camada de banco
- Atualize `database/db_manager.py` para:
  - aprovar estabelecimentos para disparo em lote
  - remover aprovacao em lote
  - filtrar estabelecimentos por `status_whatsapp`
  - filtrar estabelecimentos por `aprovado_disparo`
  - listar fila de disparos
  - enfileirar disparos pendentes
  - atualizar status, tentativas, erro e data de envio
  - expor KPIs relacionados a aprovacao e WhatsApp

3. Configuracoes
- Atualize `config/settings.py` com:
  - `EVOLUTION_BASE_URL`
  - `EVOLUTION_API_KEY`
  - `EVOLUTION_INSTANCE`
  - `INTERVALO_ENTRE_ENVIOS = 1800`
  - `LIMITE_DIARIO_ENVIOS = 30`
  - `JANELA_INICIO_HORA = 9`
  - `JANELA_FIM_HORA = 18`
  - `MAX_TENTATIVAS = 2`
- Se fizer sentido, suporte override por variaveis de ambiente.

4. Pacote WhatsApp
- Crie a pasta `whatsapp/` com:
  - `__init__.py`
  - `message_builder.py`
  - `validator.py`
  - `sender.py`
  - `scheduler.py`
- `message_builder.py` deve gerar mensagem personalizada com variacao de abertura para evitar mensagens identicas em sequencia.
- `validator.py` deve validar se o numero possui WhatsApp via endpoint:
  - `POST {EVOLUTION_BASE_URL}/chat/whatsappNumbers/{INSTANCE_NAME}`
- `sender.py` deve enviar mensagem via endpoint:
  - `POST {EVOLUTION_BASE_URL}/message/sendText/{INSTANCE_NAME}`
- `scheduler.py` deve:
  - buscar aprovados com `status_whatsapp = 'pendente'`
  - validar numero antes de enviar
  - marcar `sem_whatsapp` quando necessario
  - respeitar intervalo de 30 minutos
  - respeitar janela de envio em dias uteis
  - respeitar limite diario
  - registrar tentativas e erro
  - parar de tentar quando atingir `MAX_TENTATIVAS`
  - permitir iniciar e pausar o processamento

5. Dashboard Flask
- Atualize `dashboard.py` para adicionar:
  - `POST /api/aprovar`
  - `POST /api/remover-aprovacao`
  - `GET /api/fila-disparos`
  - `POST /api/disparo/iniciar`
  - `POST /api/disparo/pausar`
- Atualize `GET /api/estabelecimentos` para aceitar filtros:
  - `status_whatsapp`
  - `aprovado_disparo`
- Atualize `GET /api/resumo` para retornar tambem:
  - total aprovados para disparo
  - enviados hoje
  - aguardando resposta

6. Frontend da dashboard
- Atualize o frontend principal para incluir na listagem:
  - checkbox por linha
  - selecao em lote
  - aprovar selecionados
  - remover aprovacao dos selecionados
  - coluna de aprovado para disparo
  - coluna `status_whatsapp`
  - filtro por aprovados
  - filtro por status WhatsApp
- Adicione um segundo painel ou aba de `Disparos WhatsApp` com:
  - botao `Iniciar Disparo`
  - botao `Pausar Disparo`
  - status do scheduler
  - proximo envio previsto
  - contador `X de Y enviados hoje`
  - tabela da fila com nome, telefone, status, data/hora, mensagem e erro
- Se existir frontend moderno e fallback HTML, preserve o funcionamento atual e mantenha pelo menos um caminho totalmente funcional.

7. Requirements e documentacao
- Atualize `requirements.txt` para incluir `apscheduler`.
- So adicione `pandas` se a implementacao realmente precisar.
- Atualize `README.md` com:
  - configuracao da Evolution API
  - fluxo de aprovacao
  - fluxo de disparo
  - regras operacionais do scheduler

8. Testes
- Adicione ou atualize testes para:
  - schema/migracao
  - aprovacao e remocao de aprovacao
  - filtro por `status_whatsapp`
  - fila de disparos
  - `message_builder`
  - `validator` com mock HTTP
  - `sender` com mock HTTP
  - `scheduler` com cenarios de horario, limite diario e tentativas
  - novas rotas Flask
- Mantenha a suite atual passando.

9. Criterios de aceite
- O sistema atual continua funcionando para scraping, score e exportacao.
- E possivel aprovar leads pela API/dashboard.
- A fila de disparos fica persistida no SQLite.
- O scheduler respeita horario util, intervalo e limite diario.
- Numeros sem WhatsApp ficam com status `sem_whatsapp`.
- Falhas repetidas ficam com status `erro`.
- A dashboard mostra claramente o estado operacional do disparo.
- Os testes automatizados cobrem os fluxos novos.

Entregue:
- codigo implementado
- arquivos alterados
- resumo objetivo do que foi adicionado
- observacoes sobre migracao do banco, se houver
```

## Conclusao

O projeto atual ja cobre bem a etapa de descoberta e qualificacao de leads.
O gap real esta concentrado na camada de execucao comercial por WhatsApp.

Em termos praticos:

- a parte de `lead intelligence` existe
- a parte de `lead activation via WhatsApp` ainda nao existe

Esse e o foco correto da proxima evolucao.
