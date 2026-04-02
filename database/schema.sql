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

CREATE TABLE IF NOT EXISTS coletas_historico (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    data_coleta         TEXT,
    nota_media          REAL,
    total_avaliacoes    INTEGER,
    score_oportunidade  REAL
);

CREATE TABLE IF NOT EXISTS comentarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    texto               TEXT,
    estrelas            INTEGER,
    data_comentario     TEXT,
    data_coleta         TEXT
);

CREATE TABLE IF NOT EXISTS queixas_categorias (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    categoria           TEXT,
    contagem            INTEGER,
    data_coleta         TEXT
);
