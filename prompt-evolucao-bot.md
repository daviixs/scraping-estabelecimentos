# Prompt Estruturado v3 — Bot de Inteligência Comercial + Disparo WhatsApp

> Use este prompt para instruir qualquer IA a construir, evoluir ou depurar
> o sistema descrito abaixo.

---

## CONTEXTO DO PROJETO

Você é um engenheiro de software sênior especializado em automação, web scraping,
inteligência de dados e integrações com APIs de mensageria.

O sistema coleta dados públicos de estabelecimentos (nome, telefone, categoria, nota,
avaliações), armazena tudo em um banco SQLite local (`database.db`), exibe uma
dashboard web para o usuário aprovar leads, e dispara mensagens personalizadas via
WhatsApp usando a **Evolution API v3** — com intervalo controlado de 30 minutos
entre cada envio.

---

## OBJETIVO DO SISTEMA

1. Raspar estabelecimentos de múltiplas fontes (Google Maps, Apontador.com.br)
2. Calcular score de oportunidade comercial para cada um
3. Salvar tudo no `database.db` (SQLite)
4. Exibir dashboard web onde o usuário visualiza TODOS os estabelecimentos coletados
5. Usuário seleciona/aprova quais receberão mensagem
6. Sistema dispara mensagem personalizada via Evolution API com intervalo de 30 min
7. Dashboard registra e exibe status de cada envio

---

## FONTES DE DADOS

### Fonte 1 — Google Maps

- Playwright (renderização JS obrigatória)
- Busca por termo + cidade
- Scroll infinito para carregar todos os resultados

### Fonte 2 — Apontador.com.br

- Playwright (site dinâmico)
- URL padrão: `https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/`
- Exemplo: `https://www.apontador.com.br/em/franca-sp/bares-e-restaurantes/restaurantes/`
- Paginação via `?page=N` — iterar até não haver mais resultados
- Delay entre páginas: 3–6 segundos aleatórios
- Seletores a validar no DOM: nome, nota, nº avaliações, endereço, link individual
- Acessar página individual de cada estabelecimento para coletar telefone, site
  e comentários negativos

### Fonte 3 — Lista manual (CSV)

- Colunas mínimas: `nome`, `telefone`, `cidade`

---

## CAMPOS COLETADOS (por estabelecimento)

| Campo                 | Tipo       | Descrição                                                  |
| --------------------- | ---------- | ---------------------------------------------------------- |
| `id`                  | INTEGER PK | Autoincremental                                            |
| `nome`                | TEXT       | Nome do estabelecimento                                    |
| `categoria`           | TEXT       | Ex: restaurante, clínica, academia                         |
| `cidade`              | TEXT       | Cidade                                                     |
| `bairro`              | TEXT       | Bairro (se disponível)                                     |
| `telefone`            | TEXT       | Número com DDD (ex: 5516999990000)                         |
| `site`                | TEXT       | Site próprio                                               |
| `nota_media`          | REAL       | Nota atual (ex: 4.3)                                       |
| `total_avaliacoes`    | INTEGER    | Total de avaliações                                        |
| `link_origem`         | TEXT       | URL raspada                                                |
| `fonte`               | TEXT       | "google_maps", "apontador" ou "manual"                     |
| `data_coleta`         | TEXT       | Timestamp ISO                                              |
| `dono_responde`       | INTEGER    | 1 se o dono respondeu avaliações                           |
| `score_oportunidade`  | REAL       | Score de 0 a 100                                           |
| `faixa_classificacao` | TEXT       | "MUITO BOM", "MÉDIO" ou "MUITO RUIM"                       |
| `prioridade_lead`     | TEXT       | "ALTA", "MÉDIA" ou "BAIXA"                                 |
| `resumo_queixas`      | TEXT       | Ex: "atendimento (6), demora (4)"                          |
| `aprovado_disparo`    | INTEGER    | 0 ou 1 — aprovado pelo usuário na dashboard                |
| `status_whatsapp`     | TEXT       | "pendente", "enviado", "sem_whatsapp", "erro", "respondeu" |

---

## CLASSIFICAÇÃO POR NOTA

| Faixa         | Classificação |
| ------------- | ------------- |
| 4.8 – 5.0     | MUITO BOM     |
| 4.5 – 4.7     | MÉDIO         |
| Abaixo de 4.5 | MUITO RUIM    |

---

## SCORE DE OPORTUNIDADE (0–100)

```
score = (nota_inv  × 0.30)
      + (vol_norm  × 0.20)
      + (queixas   × 0.25)
      + (queda     × 0.15)
      + (sem_reply × 0.10)
      × 100
```

| Componente  | Peso | Cálculo                                                   |
| ----------- | ---- | --------------------------------------------------------- |
| `nota_inv`  | 30%  | `(5.0 - nota_media) / 4.0`                                |
| `vol_norm`  | 20%  | `min(total_avaliacoes / 500, 1.0)`                        |
| `queixas`   | 25%  | proporção de comentários negativos com queixas detectadas |
| `queda`     | 15%  | `1.0` se nota caiu ≥ 0.2 pts vs coleta anterior           |
| `sem_reply` | 10%  | `1.0` se dono nunca respondeu avaliações                  |

| Score  | Prioridade |
| ------ | ---------- |
| 60–100 | ALTA       |
| 35–59  | MÉDIA      |
| 0–34   | BAIXA      |

---

## NLP DE COMENTÁRIOS

```python
CATEGORIAS_QUEIXA = {
    "atendimento":  ["atendimento", "grosseiro", "ignorou", "mal atendido",
                     "rude", "funcionário", "garçom", "recepcionista"],
    "demora":       ["demora", "demorou", "espera", "fila", "lento",
                     "muito tempo", "atraso"],
    "sistema":      ["sistema", "app", "aplicativo", "travou", "não funcionou",
                     "bug", "erro", "tecnologia", "plataforma", "software"],
    "limpeza":      ["sujo", "sujeira", "limpeza", "higiene", "barata",
                     "cheiro", "fedorento"],
    "preco":        ["caro", "preço", "valor", "abusivo", "não vale", "salgado"],
    "qualidade":    ["qualidade", "ruim", "péssimo", "horrível",
                     "decepcionante", "não recomendo"],
}
```

---

## BANCO DE DADOS — `database.db` (SQLite)

### Tabela `estabelecimentos`

```sql
CREATE TABLE IF NOT EXISTS estabelecimentos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT NOT NULL,
    categoria           TEXT,
    cidade              TEXT,
    bairro              TEXT,
    telefone            TEXT,
    site                TEXT,
    nota_media          REAL,
    total_avaliacoes    INTEGER DEFAULT 0,
    link_origem         TEXT,
    fonte               TEXT,
    data_coleta         TEXT,
    dono_responde       INTEGER DEFAULT 0,
    score_oportunidade  REAL DEFAULT 0,
    faixa_classificacao TEXT,
    prioridade_lead     TEXT,
    resumo_queixas      TEXT,
    aprovado_disparo    INTEGER DEFAULT 0,
    status_whatsapp     TEXT DEFAULT 'pendente',
    UNIQUE(nome, cidade)
);
```

### Tabela `coletas_historico`

```sql
CREATE TABLE IF NOT EXISTS coletas_historico (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    data_coleta         TEXT,
    nota_media          REAL,
    total_avaliacoes    INTEGER,
    score_oportunidade  REAL
);
```

### Tabela `comentarios`

```sql
CREATE TABLE IF NOT EXISTS comentarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    texto               TEXT,
    estrelas            INTEGER,
    data_comentario     TEXT,
    data_coleta         TEXT
);
```

### Tabela `queixas_categorias`

```sql
CREATE TABLE IF NOT EXISTS queixas_categorias (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    categoria           TEXT,
    contagem            INTEGER,
    data_coleta         TEXT
);
```

### Tabela `fila_disparos`

```sql
CREATE TABLE IF NOT EXISTS fila_disparos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    telefone            TEXT,
    mensagem            TEXT,
    status              TEXT DEFAULT 'pendente',
    tentativas          INTEGER DEFAULT 0,
    data_agendamento    TEXT,
    data_envio          TEXT,
    erro_descricao      TEXT,
    resposta_recebida   INTEGER DEFAULT 0
);
```

---

## MÓDULO WHATSAPP — `whatsapp/sender.py`

### Integração com Evolution API v3

A Evolution API v3 é uma API REST open source que conecta ao WhatsApp via QR Code.
Funciona com qualquer número — chip físico ou E-SIM — incluindo WhatsApp Business.
O número deve estar conectado e autenticado via QR Code no painel da Evolution.

**Endpoint de envio de mensagem de texto:**

```
POST {EVOLUTION_BASE_URL}/message/sendText/{INSTANCE_NAME}
Headers:
  apikey: {EVOLUTION_API_KEY}
  Content-Type: application/json

Body:
{
  "number": "5516999990000",   // número com código do país + DDD, sem formatação
  "text": "mensagem aqui"
}
```

**Endpoint de validação — checar se número tem WhatsApp:**

```
POST {EVOLUTION_BASE_URL}/chat/whatsappNumbers/{INSTANCE_NAME}
Body:
{
  "numbers": ["5516999990000"]
}
Retorna: [{ "number": "...", "exists": true/false }]
```

### Lógica de disparo (`whatsapp/sender.py`)

```python
"""
Fluxo do módulo de disparo:

1. Buscar no banco todos os registros com:
   - aprovado_disparo = 1
   - status_whatsapp = 'pendente'
   - telefone NOT NULL

2. Para cada registro na fila:
   a. Validar se o número tem WhatsApp (endpoint whatsappNumbers)
   b. Se não tem: atualizar status_whatsapp = 'sem_whatsapp', pular
   c. Se tem: gerar mensagem personalizada com o template
   d. Enviar via POST /message/sendText
   e. Atualizar status_whatsapp = 'enviado' e data_envio
   f. Aguardar 30 minutos (1800 segundos) antes do próximo envio
   g. Em caso de erro: registrar erro_descricao, incrementar tentativas
   h. Se tentativas >= 2: status_whatsapp = 'erro' (não tentar mais)

3. Janela de envio: somente das 9h às 18h em dias úteis
4. Limite diário: configurável em settings.py (padrão: 30 mensagens/dia)
5. Ao atingir o limite diário, pausar e retomar no próximo dia útil
"""
```

---

## TEMPLATE DA MENSAGEM

A mensagem deve ser personalizada com o nome e a categoria do estabelecimento.
Nunca enviar a mesma mensagem idêntica duas vezes — o WhatsApp detecta padrões.

### Template base

```
Olá, tudo bem? Aqui é o Gustavo, da InovaSociety.

Estamos desenvolvendo soluções para ajudar {categoria} a organizar processos,
prazos e rotinas operacionais de forma mais eficiente.

Antes de construir qualquer ferramenta, estamos conversando com alguns
estabelecimentos para entender os principais desafios reais do dia a dia.

Podemos conversar?
```

### Função de geração (`whatsapp/message_builder.py`)

```python
import random

VARIACOES_ABERTURA = [
    "Olá, tudo bem?",
    "Oi, tudo certo?",
    "Olá! Boa tarde.",
    "Oi! Tudo bem?",
]

def gerar_mensagem(nome: str, categoria: str) -> str:
    abertura = random.choice(VARIACOES_ABERTURA)
    return (
        f"{abertura} Aqui é o Gustavo, da InovaSociety.\n\n"
        f"Estamos desenvolvendo soluções para ajudar {categoria} a organizar "
        f"processos, prazos e rotinas operacionais de forma mais eficiente.\n\n"
        f"Antes de construir qualquer ferramenta, estamos conversando com alguns "
        f"estabelecimentos para entender os principais desafios reais do dia a dia.\n\n"
        f"Podemos conversar?"
    )
```

A variação na abertura evita que o WhatsApp detecte mensagens idênticas em sequência.

---

## DASHBOARD WEB LOCAL

Roda com `python dashboard.py` → `http://localhost:5000`
Backend: Flask · Frontend: HTML + CSS + JS puro

### Aba 1 — Estabelecimentos (visão geral)

Exibe **TODOS** os estabelecimentos coletados, sem filtro de aprovação.

**Filtros disponíveis:**

- Classificação: MUITO BOM / MÉDIO / MUITO RUIM (checkboxes)
- Prioridade: ALTA / MÉDIA / BAIXA (checkboxes)
- Fonte: Google Maps / Apontador / Manual (checkboxes)
- Cidade (dropdown)
- Categoria (dropdown)
- Score mínimo (slider 0–100)
- Status WhatsApp: todos / pendente / enviado / sem_whatsapp / erro / respondeu
- Aprovados para disparo: todos / aprovados / não aprovados

**Colunas da tabela:**

- Checkbox de seleção (para aprovar em lote)
- Nome (link para `link_origem`)
- Categoria
- Cidade / Bairro
- Telefone
- Nota (colorida: verde/amarelo/vermelho)
- Nº avaliações
- Score (barra de progresso)
- Prioridade (badge colorido)
- Resumo de queixas
- Aprovado para disparo (toggle on/off)
- Status WhatsApp (ícone + texto)
- Data da coleta

**Ações em lote:**

- Selecionar todos os filtrados
- Aprovar selecionados para disparo
- Remover aprovação dos selecionados

**Paginação numérica:**

- 20 registros por página (configurável)
- Botões: `« Anterior · 1 · 2 · 3 · ... · N · Próximo »`
- Página atual destacada
- "Mostrando X–Y de Z resultados"
- Ordenação clicando no cabeçalho da coluna (padrão: score desc)

**Cards KPI no topo:**

- Total coletado
- Aprovados para disparo
- Enviados hoje
- Aguardando resposta
- Score médio geral

### Aba 2 — Disparos WhatsApp

**Controles:**

- Botão "Iniciar Disparo" (dispara o scheduler de envio)
- Botão "Pausar Disparo"
- Indicador de status: "Ativo — próximo envio em X min" ou "Pausado"
- Contador: "X de Y aprovados enviados hoje"

**Tabela de fila:**

- Nome do estabelecimento
- Telefone
- Status (pendente / enviado / sem_whatsapp / erro / respondeu)
- Data/hora do envio
- Mensagem enviada (expansível)
- Erro (se houver)

**Regras exibidas na interface:**

- Intervalo entre envios: 30 minutos
- Janela de envio: 9h–18h dias úteis
- Limite diário: X mensagens (configurável)

---

## ROTAS DA API FLASK

```
GET  /                                → dashboard (index.html)

GET  /api/estabelecimentos            → lista paginada com filtros
GET  /api/resumo                      → KPIs do topo
GET  /api/cidades                     → cidades disponíveis
GET  /api/categorias                  → categorias disponíveis

POST /api/aprovar                     → aprovar IDs para disparo
     Body: { "ids": [1, 2, 3] }

POST /api/remover-aprovacao           → remover aprovação
     Body: { "ids": [1, 2, 3] }

GET  /api/fila-disparos               → lista da fila de envios
POST /api/disparo/iniciar             → inicia o scheduler de envio
POST /api/disparo/pausar              → pausa o scheduler

GET  /api/export/csv                  → CSV com filtros aplicados
GET  /api/export/xlsx                 → Excel com filtros aplicados
```

---

## LAYOUT DA DASHBOARD

```
┌──────────────────────────────────────────────────────────────┐
│  InovaSociety — Bot de Leads       [Estabelecimentos][Disparos]│
├──────────────────────────────────────────────────────────────┤
│  Total: 342 | Aprovados: 87 | Enviados hoje: 12 | Score: 54  │
├─────────────────┬────────────────────────────────────────────┤
│  FILTROS        │  [Aprovar Selecionados] [Exportar CSV/XLSX] │
│                 │  ──────────────────────────────────────────│
│  Classificação  │  □ Nome      Nota  Score  Prior. Status     │
│  □ Muito bom   │  □ Restaurante X  4.3  ██ 72  ALTA  pendente│
│  □ Médio       │  □ Clínica Y      4.6  ██ 48  MÉDIA enviado │
│  □ Muito ruim  │  □ Academia Z     4.1  ██ 81  ALTA  pendente│
│                 │  ...                                        │
│  Prioridade     ├────────────────────────────────────────────┤
│  □ Alta        │  « 1  2  3  4  5 ... 18 »                  │
│  □ Média       │  Mostrando 1–20 de 342 resultados           │
│  □ Baixa       │                                             │
│                 │                                             │
│  Status WPP     │                                             │
│  □ Pendente    │                                             │
│  □ Enviado     │                                             │
│  □ Respondeu   │                                             │
│                 │                                             │
│  Cidade ▼       │                                             │
│  Categoria ▼    │                                             │
│  Score min: 40  │                                             │
│  [Aplicar]      │                                             │
│  [Limpar]       │                                             │
└─────────────────┴────────────────────────────────────────────┘
```

---

## ARQUITETURA COMPLETA DO PROJETO

```
bot-inteligencia-comercial/
│
├── scraper/
│   ├── google_maps.py          # Playwright — Google Maps
│   ├── apontador.py            # Playwright — Apontador.com.br
│   └── csv_importer.py         # Importação de lista manual
│
├── processor/
│   ├── normalizer.py           # Limpeza e padronização
│   ├── nlp_comments.py         # NLP por palavras-chave
│   └── scorer.py               # Cálculo do score
│
├── database/
│   ├── schema.sql              # 5 tabelas SQLite
│   ├── db_manager.py           # CRUD
│   └── history.py              # Detecção de queda de reputação
│
├── whatsapp/
│   ├── sender.py               # Integração Evolution API v3
│   ├── message_builder.py      # Gerador de mensagem personalizada
│   ├── validator.py            # Valida se número tem WhatsApp
│   └── scheduler.py            # Controla intervalo e limite diário
│
├── output/
│   ├── excel_exporter.py       # .xlsx com formatação condicional
│   └── csv_exporter.py         # .csv dos resultados
│
├── templates/
│   └── index.html              # Dashboard HTML/CSS/JS
│
├── config/
│   └── settings.py             # Todas as configurações centrais
│
├── dashboard.py                # Servidor Flask
├── main.py                     # Orquestrador CLI
├── database.db                 # Banco SQLite (gerado automaticamente)
├── requirements.txt
└── README.md
```

---

## `config/settings.py`

```python
# Banco
DATABASE_PATH           = "database.db"

# Dashboard
DASHBOARD_HOST          = "127.0.0.1"
DASHBOARD_PORT          = 5000
REGISTROS_POR_PAGINA    = 20

# Score
PESO_NOTA_INVERTIDA     = 0.30
PESO_VOLUME_REVIEWS     = 0.20
PESO_QUEIXAS            = 0.25
PESO_QUEDA_REPUTACAO    = 0.15
PESO_SEM_REPLY          = 0.10
VOLUME_MAXIMO_NORM      = 500
DELTA_QUEDA_MINIMO      = 0.2

# Scraping
DELAY_MIN_SEGUNDOS      = 3
DELAY_MAX_SEGUNDOS      = 6
USER_AGENT              = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Apontador
APONTADOR_BASE_URL      = "https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/"

# Classificação
FAIXA_MUITO_BOM         = 4.8
FAIXA_MEDIO             = 4.5

# Prioridade
SCORE_PRIORIDADE_ALTA   = 60
SCORE_PRIORIDADE_MEDIA  = 35

# Evolution API v3
EVOLUTION_BASE_URL      = "http://localhost:8080"   # URL do seu servidor Evolution
EVOLUTION_API_KEY       = "sua-api-key-aqui"
EVOLUTION_INSTANCE      = "nome-da-instancia"       # nome configurado no painel

# Disparo WhatsApp
INTERVALO_ENTRE_ENVIOS  = 1800   # 30 minutos em segundos
LIMITE_DIARIO_ENVIOS    = 30
JANELA_INICIO_HORA      = 9      # 9h
JANELA_FIM_HORA         = 18     # 18h
MAX_TENTATIVAS          = 2
```

---

## REQUIREMENTS.TXT

```
playwright==1.44.0
beautifulsoup4==4.12.3
requests==2.32.3
pandas==2.2.2
openpyxl==3.1.4
flask==3.0.3
apscheduler==3.10.4
lxml==5.2.2
```

---

## NOTAS SOBRE E-SIM + WHATSAPP BUSINESS + EVOLUTION API

- E-SIM funciona normalmente com a Evolution API — a API conecta via QR Code,
  independente do tipo de chip
- WhatsApp Business no E-SIM é a melhor combinação: perfil comercial aumenta
  credibilidade e reduz risco de bloqueio
- Aquecer o número por 7–14 dias antes de usar para prospecção
- O intervalo de 30 minutos entre envios é intencional para simular
  comportamento humano e proteger o número
- Nunca enviar mensagem idêntica em sequência — o `message_builder.py` já
  inclui variações aleatórias na abertura para isso
- Validar sempre se o número tem WhatsApp antes de enviar (endpoint
  `/chat/whatsappNumbers`) para evitar erros que o algoritmo detecta

---

## COMANDOS PARA GERAR CADA MÓDULO

```
"Gere o código completo de scraper/apontador.py usando Playwright"
"Gere o código completo de scraper/google_maps.py usando Playwright"
"Gere o código completo de database/schema.sql com as 5 tabelas"
"Gere o código completo de database/db_manager.py com CRUD SQLite"
"Gere o código completo de processor/scorer.py"
"Gere o código completo de processor/nlp_comments.py"
"Gere o código completo de whatsapp/sender.py com Evolution API v3"
"Gere o código completo de whatsapp/message_builder.py"
"Gere o código completo de whatsapp/scheduler.py com APScheduler"
"Gere o código completo de dashboard.py com Flask"
"Gere o código completo de templates/index.html com filtros, paginação e aba de disparos"
"Gere o código completo de main.py com CLI argparse"
"Gere o requirements.txt completo"
"Gere o README.md completo do projeto"
```

---

_Versão: 3.0 — 09/04/2026_
_Projeto: Bot de Inteligência Comercial — InovaSociety_
_Disparo: Evolution API v3 · Intervalo: 30 min · Limite: 30/dia_
_Banco: SQLite local (database.db) · Dashboard: Flask localhost:5000_
