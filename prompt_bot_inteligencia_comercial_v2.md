# Prompt Estruturado v2 — Bot de Inteligência Comercial por Avaliações

> Use este prompt para instruir qualquer IA (Claude, ChatGPT, Gemini, etc.)
> a construir, evoluir ou depurar o sistema descrito abaixo.

---

## CONTEXTO DO PROJETO

Você é um engenheiro de software sênior especializado em automação, web scraping e
inteligência de dados para prospecção comercial B2B.

Estou construindo um **bot de raspagem e análise de avaliações de estabelecimentos**
com o objetivo de gerar uma lista priorizada de leads para uma empresa de soluções
tecnológicas. A lógica central é: estabelecimentos com notas medianas, alto volume de
avaliações e reclamações recorrentes são os melhores leads, pois têm dor real,
movimento real e impacto visível no faturamento.

Todos os dados coletados devem ser persistidos localmente em um arquivo **`database.db`**
(SQLite), sem dependência de servidores externos.

---

## OBJETIVO DO SISTEMA

1. Coletar dados públicos de avaliações via múltiplas fontes
2. Processar comentários com NLP simples para categorizar queixas
3. Calcular um **score de oportunidade comercial** (0–100)
4. Armazenar tudo em `database.db` (SQLite)
5. Exibir uma **dashboard web local** que lê do banco e permite filtrar, paginar e explorar os leads

---

## FONTES DE DADOS (ENTRADAS)

O sistema suporta três modos de entrada:

### Fonte 1 — Google Maps / Google Meu Negócio
- Raspagem via **Playwright** (necessário renderização JS)
- URL base: `https://www.google.com/maps/search/{termo}+{cidade}`
- Paginação: scroll infinito — simular scroll até carregar todos os resultados
- Campos disponíveis: nome, categoria, endereço, telefone, site, nota, nº de avaliações, comentários recentes, se o dono respondeu

### Fonte 2 — Apontador (apontador.com.br)
- Site dinâmico — usar **Playwright** (renderiza JS)
- URL padrão de listagem por categoria e cidade:
  `https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/`
  Exemplo: `https://www.apontador.com.br/em/franca-sp/bares-e-restaurantes/restaurantes/`
- URL de busca geral por cidade:
  `https://www.apontador.com.br/local/search.html?q=&loc=Franca+SP&city=Franca`
- **Paginação**: parâmetro `?page=N` — iterar de 1 até não haver mais resultados
- **Seletores a extrair por card de estabelecimento:**
  - Nome: `h2.place-name` ou título principal do card
  - Categoria: breadcrumb ou tag de categoria
  - Endereço/Bairro: campo de endereço do card
  - Telefone: campo de contato (quando disponível)
  - Nota: elemento de estrelas (valor numérico ou preenchimento visual)
  - Nº de avaliações: contador ao lado da nota
  - Link da página do estabelecimento: href do card
- **Detalhes do estabelecimento** (acessar página individual via link coletado):
  - Site do estabelecimento
  - Comentários dos usuários (texto + estrelas)
  - Se o proprietário respondeu comentários
- **Delay entre páginas**: 3–6 segundos aleatórios
- **User-Agent**: simular Chrome desktop real

### Fonte 3 — Lista manual (CSV/Excel)
- Arquivo com colunas: `nome`, `url`, `cidade` (mínimo)
- O bot acessa cada URL individualmente para coletar os dados

---

## CAMPOS A COLETAR (por estabelecimento)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PK | ID autoincremental |
| `nome` | TEXT | Nome oficial do estabelecimento |
| `categoria` | TEXT | Tipo (restaurante, clínica, academia, etc.) |
| `cidade` | TEXT | Cidade |
| `bairro` | TEXT | Bairro (se disponível) |
| `telefone` | TEXT | Telefone de contato |
| `site` | TEXT | URL do site próprio (se disponível) |
| `nota_media` | REAL | Nota média atual (ex: 4.3) |
| `total_avaliacoes` | INTEGER | Número total de avaliações |
| `link_origem` | TEXT | URL da página raspada |
| `fonte` | TEXT | "google_maps", "apontador" ou "manual" |
| `data_coleta` | TEXT | Timestamp ISO da coleta |
| `dono_responde` | INTEGER | 0 ou 1 — se o proprietário respondeu |
| `score_oportunidade` | REAL | Score calculado de 0 a 100 |
| `faixa_classificacao` | TEXT | "MUITO BOM", "MÉDIO" ou "MUITO RUIM" |
| `prioridade_lead` | TEXT | "ALTA", "MÉDIA" ou "BAIXA" |
| `resumo_queixas` | TEXT | Texto resumido das principais categorias detectadas |

---

## CLASSIFICAÇÃO POR NOTA

| Faixa de nota | `faixa_classificacao` |
|---|---|
| 4.8 a 5.0 | MUITO BOM |
| 4.5 a 4.7 | MÉDIO |
| Abaixo de 4.5 | MUITO RUIM |

> Nota: a classificação é apenas descritiva. A prioridade de lead é definida pelo
> **score de oportunidade**, não pela nota isolada.

---

## SCORE DE OPORTUNIDADE (0–100)

### Fórmula

```
score = (nota_inv  × 0.30)
      + (vol_norm  × 0.20)
      + (queixas   × 0.25)
      + (queda     × 0.15)
      + (sem_reply × 0.10)
      × 100
```

### Componentes

| Componente | Peso | Cálculo |
|---|---|---|
| `nota_inv` | 30% | `(5.0 - nota_media) / 4.0` — nota baixa = oportunidade alta |
| `vol_norm` | 20% | `min(total_avaliacoes / 500, 1.0)` — mais reviews = mais exposição |
| `queixas` | 25% | `comentarios_com_queixa / total_negativos_analisados` (últimos 10) |
| `queda` | 15% | `1.0` se nota caiu ≥ 0.2 pts vs. coleta anterior, `0.0` se não |
| `sem_reply` | 10% | `1.0` se dono não respondeu nenhuma avaliação, `0.0` se respondeu |

### Prioridade de lead

| Score | `prioridade_lead` |
|---|---|
| 60 a 100 | ALTA |
| 35 a 59 | MÉDIA |
| 0 a 34 | BAIXA |

---

## NLP DE COMENTÁRIOS

Usar dicionário de palavras-chave em português — sem modelos de ML.

```python
CATEGORIAS_QUEIXA = {
    "atendimento":  ["atendimento", "grosseiro", "ignorou", "mal atendido", "rude",
                     "funcionário", "garçom", "recepcionista", "educação"],
    "demora":       ["demora", "demorou", "espera", "fila", "lento", "tardou",
                     "muito tempo", "hora", "atraso"],
    "sistema":      ["sistema", "app", "aplicativo", "travou", "não funcionou",
                     "bug", "erro", "tecnologia", "plataforma", "software"],
    "limpeza":      ["sujo", "sujeira", "limpeza", "higiene", "barata",
                     "mosquito", "cheiro", "fedorento"],
    "preco":        ["caro", "preço", "valor", "cobrado", "cobrança",
                     "abusivo", "não vale", "salgado"],
    "qualidade":    ["qualidade", "ruim", "péssimo", "horrível", "decepcionante",
                     "não recomendo", "nunca mais"],
}
```

Retornar por estabelecimento:
```python
{
    "atendimento": 6,
    "demora": 4,
    "sistema": 2,
    "limpeza": 1,
    "preco": 0,
    "qualidade": 3
}
```

O campo `resumo_queixas` no banco deve ser uma string legível, ex:
`"atendimento (6), demora (4), qualidade (3)"`

---

## BANCO DE DADOS SQLite — `database.db`

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

---

## DASHBOARD WEB LOCAL

A dashboard é uma aplicação web local que lê direto do `database.db`.
Deve rodar com `python dashboard.py` e abrir em `http://localhost:5000`.

### Tecnologia

- **Backend**: Flask (Python) — serve os dados do SQLite via rotas REST
- **Frontend**: HTML + CSS + JavaScript puro (sem frameworks externos além de um CDN leve)
- Arquivo único ou estrutura mínima: `dashboard.py` + `templates/index.html`

### Funcionalidades obrigatórias

#### 1. Filtros (barra lateral ou topo)
- **Por classificação de nota**: checkboxes "MUITO BOM", "MÉDIO", "MUITO RUIM"
- **Por prioridade de lead**: checkboxes "ALTA", "MÉDIA", "BAIXA"
- **Por fonte**: checkboxes "Google Maps", "Apontador", "Manual"
- **Por cidade**: dropdown com cidades disponíveis no banco
- **Por categoria**: dropdown com categorias disponíveis
- **Score mínimo**: slider de 0 a 100
- **Botão "Aplicar filtros"** e **"Limpar filtros"**

#### 2. Tabela de resultados
Colunas exibidas:
- Nome do estabelecimento (link clicável para `link_origem`)
- Categoria
- Cidade / Bairro
- Nota média (com cor: verde ≥ 4.8, amarelo 4.5–4.7, vermelho < 4.5)
- Total de avaliações
- Score de oportunidade (barra de progresso colorida 0–100)
- Prioridade lead (badge colorido: vermelho=ALTA, amarelo=MÉDIA, verde=BAIXA)
- Resumo das queixas
- Fonte
- Data da coleta

#### 3. Paginação numérica
- 20 registros por página (configurável em `settings.py`)
- Botões: `« Anterior` · `1` · `2` · `3` · `...` · `N` · `Próximo »`
- Página atual destacada
- Exibir total: "Mostrando X–Y de Z resultados"

#### 4. Ordenação
- Clicar no cabeçalho da coluna ordena (asc/desc)
- Padrão: ordenar por `score_oportunidade` descendente

#### 5. Cards de resumo (topo da página)
- Total de estabelecimentos no banco
- Qtd com prioridade ALTA / MÉDIA / BAIXA
- Score médio geral
- Última data de coleta

#### 6. Exportar (botão)
- Exportar resultados filtrados para CSV
- Exportar resultados filtrados para Excel (.xlsx)

### Rota da API Flask (backend)

```
GET /api/estabelecimentos
  Params:
    ?page=1
    &per_page=20
    &classificacao=MUITO+RUIM,MÉDIO
    &prioridade=ALTA,MÉDIA
    &fonte=apontador
    &cidade=Franca
    &categoria=Restaurantes
    &score_min=40
    &order_by=score_oportunidade
    &order_dir=desc

Retorna JSON:
{
  "total": 342,
  "page": 1,
  "per_page": 20,
  "pages": 18,
  "data": [ { ...campos do estabelecimento... } ]
}
```

```
GET /api/resumo
Retorna contadores para os cards de topo

GET /api/export/csv   → arquivo CSV com filtros aplicados
GET /api/export/xlsx  → arquivo Excel com filtros aplicados
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
│   ├── normalizer.py           # Limpeza e padronização dos campos
│   ├── nlp_comments.py         # NLP por palavras-chave
│   └── scorer.py               # Cálculo do score de oportunidade
│
├── database/
│   ├── schema.sql              # Definição das 4 tabelas
│   ├── db_manager.py           # CRUD via sqlite3
│   └── history.py              # Detecção de queda de reputação
│
├── output/
│   ├── excel_exporter.py       # Gera .xlsx com formatação condicional
│   └── csv_exporter.py         # Gera .csv dos resultados
│
├── templates/
│   └── index.html              # Dashboard frontend (HTML/CSS/JS)
│
├── config/
│   └── settings.py             # Pesos, configurações, constantes
│
├── dashboard.py                # Servidor Flask da dashboard
├── main.py                     # Orquestrador principal (CLI)
├── database.db                 # Banco SQLite (gerado automaticamente)
├── requirements.txt
└── README.md
```

---

## `config/settings.py` — Configurações centrais

```python
# Banco de dados
DATABASE_PATH = "database.db"

# Dashboard
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5000
REGISTROS_POR_PAGINA = 20

# Score — pesos ajustáveis
PESO_NOTA_INVERTIDA  = 0.30
PESO_VOLUME_REVIEWS  = 0.20
PESO_QUEIXAS         = 0.25
PESO_QUEDA_REPUTACAO = 0.15
PESO_SEM_REPLY       = 0.10

# Volume de normalização
VOLUME_MAXIMO_NORM   = 500

# Queda de reputação
DELTA_QUEDA_MINIMO   = 0.2   # Diferença mínima de nota para contar como queda

# Scraping
DELAY_MIN_SEGUNDOS   = 3
DELAY_MAX_SEGUNDOS   = 6
USER_AGENT           = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Apontador — URL base
APONTADOR_BASE_URL   = "https://www.apontador.com.br/em/{cidade}-{estado}/{categoria}/"
APONTADOR_BUSCA_URL  = "https://www.apontador.com.br/local/search.html?q=&loc={cidade}+{estado}&city={cidade}"

# Classificação por nota
FAIXA_MUITO_BOM      = 4.8
FAIXA_MEDIO          = 4.5

# Prioridade de lead por score
SCORE_PRIORIDADE_ALTA  = 60
SCORE_PRIORIDADE_MEDIA = 35
```

---

## `scraper/apontador.py` — Especificação detalhada

```python
"""
Scraper do Apontador.com.br usando Playwright.

Fluxo:
1. Receber lista de URLs de categorias (ex: restaurantes em Franca SP)
2. Para cada URL de categoria:
   a. Abrir página com Playwright (headless=True)
   b. Aguardar carregamento dos cards (.place-card ou seletor equivalente)
   c. Coletar dados de todos os cards da página
   d. Verificar se existe botão/link de próxima página
   e. Se sim, navegar e repetir; se não, encerrar
3. Para cada estabelecimento coletado, acessar a página individual
4. Coletar comentários, telefone, site e status de resposta do dono
5. Retornar lista de dicionários com todos os campos

Seletores esperados (validar com inspeção do DOM real):
- Cards de lista:    .place-card, .place-item, [data-place-id]
- Nome:              h2.place-name, .card-title, .name
- Nota:              .rating-value, .stars-value, [itemprop='ratingValue']
- Nº avaliações:     .rating-count, .reviews-count
- Endereço:          .address, .place-address
- Link individual:   a[href*='/local/'] ou href do card principal
- Paginação:         a.next-page, [rel='next'], .pagination .active + li a
"""
```

---

## `dashboard.py` — Especificação Flask

```python
"""
Servidor Flask local da dashboard de leads.

Rotas:
  GET  /                          → renderiza templates/index.html
  GET  /api/estabelecimentos      → JSON paginado com filtros
  GET  /api/resumo                → JSON com totais e KPIs
  GET  /api/cidades               → lista de cidades disponíveis
  GET  /api/categorias            → lista de categorias disponíveis
  GET  /api/export/csv            → download CSV com filtros
  GET  /api/export/xlsx           → download Excel com filtros

Inicialização:
  1. Verificar se database.db existe; se não, criar com schema.sql
  2. Iniciar servidor em localhost:5000
  3. Abrir browser automaticamente (webbrowser.open)
"""
```

---

## `templates/index.html` — Especificação da Dashboard

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: "Bot de Leads Comerciais"   [Exportar CSV][XLSX]│
├─────────────────────────────────────────────────────────┤
│  CARDS KPI:  Total | Alta | Média | Baixa | Score médio  │
├──────────────────┬──────────────────────────────────────┤
│  FILTROS (esq.)  │  TABELA DE RESULTADOS                │
│                  │                                      │
│  Classificação   │  Nome | Cat | Nota | Score | Prior.  │
│  [ ] Muito bom   │  ...linha 1...                       │
│  [ ] Médio       │  ...linha 2...                       │
│  [ ] Muito ruim  │  ...linha 3...                       │
│                  │  ...                                 │
│  Prioridade      │                                      │
│  [ ] Alta        ├──────────────────────────────────────┤
│  [ ] Média       │  « 1  2  3  4  5 ... 18 »            │
│  [ ] Baixa       │  Mostrando 1–20 de 342 resultados    │
│                  │                                      │
│  Fonte           │                                      │
│  [ ] Google Maps │                                      │
│  [ ] Apontador   │                                      │
│  [ ] Manual      │                                      │
│                  │                                      │
│  Cidade ▼        │                                      │
│  Categoria ▼     │                                      │
│  Score mín: 40   │                                      │
│  [Aplicar]       │                                      │
│  [Limpar]        │                                      │
└──────────────────┴──────────────────────────────────────┘
```

### Cores das badges de prioridade
- ALTA → fundo vermelho claro `#ffdddd`, texto `#a32d2d`
- MÉDIA → fundo amarelo claro `#fff3cd`, texto `#856404`
- BAIXA → fundo verde claro `#d4edda`, texto `#155724`

### Cores da coluna de nota
- ≥ 4.8 → `#28a745` (verde)
- 4.5–4.7 → `#ffc107` (amarelo)
- < 4.5 → `#dc3545` (vermelho)

### Barra de progresso do score
- 0–34: barra vermelha
- 35–59: barra amarela
- 60–100: barra azul (lead quente para tecnologia)

---

## REQUIREMENTS.TXT

```
playwright==1.44.0
beautifulsoup4==4.12.3
requests==2.32.3
pandas==2.2.2
openpyxl==3.1.4
flask==3.0.3
lxml==5.2.2
```

---

## `main.py` — Orquestrador CLI

```
Uso:
  python main.py --fonte apontador --cidade Franca --estado SP --categoria restaurantes
  python main.py --fonte google_maps --busca "restaurantes Franca SP"
  python main.py --fonte csv --arquivo minha_lista.csv
  python main.py --dashboard        # só sobe a dashboard sem coletar
```

---

## REGRAS DE NEGÓCIO

1. Um estabelecimento com nota 4.4 e 400 avaliações é lead melhor do que um com nota 4.1 e 8 avaliações.
2. Comentários sem resposta do proprietário indicam gestão reativa — maior abertura para soluções externas.
3. Queda de reputação recente é sinal de urgência — negócio em degradação ativa.
4. Reclamações sobre "sistema", "app" ou "plataforma" são o sinal mais qualificado para uma empresa de tecnologia.
5. Os pesos do score devem ser ajustáveis via `config/settings.py`.
6. Ao reraspar um estabelecimento já existente, atualizar os campos e registrar o histórico em `coletas_historico`.
7. Duplicatas são evitadas pela constraint `UNIQUE(nome, cidade)` — usar `INSERT OR REPLACE`.

---

## COMANDOS PARA GERAR CADA MÓDULO

Envie este prompt a uma IA seguido de um dos comandos:

```
"Gere o código completo de scraper/apontador.py usando Playwright"
"Gere o código completo de scraper/google_maps.py usando Playwright"
"Gere o código completo de database/schema.sql com as 4 tabelas"
"Gere o código completo de database/db_manager.py com CRUD SQLite"
"Gere o código completo de processor/scorer.py com a fórmula do score"
"Gere o código completo de processor/nlp_comments.py"
"Gere o código completo de dashboard.py com Flask"
"Gere o código completo de templates/index.html com filtros e paginação"
"Gere o código completo de main.py com CLI argparse"
"Gere o requirements.txt completo"
"Gere o README.md completo do projeto"
```

---

*Versão: 2.0 — 02/04/2026*
*Projeto: Bot de Inteligência Comercial por Avaliações*
*Fonte adicional: Apontador.com.br (Playwright, paginação ?page=N)*
*Armazenamento: SQLite local — database.db*
*Dashboard: Flask + HTML/JS local em localhost:5000*
