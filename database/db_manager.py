import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from config import settings


PRIORIDADE_MEDIA_ALIASES = ("MEDIA", "MÉDIA", "MÃ‰DIA", "MÃƒâ€°DIA")
CLASSIFICACAO_MEDIA_ALIASES = ("MEDIO", "MÉDIO", "MÃ‰DIO", "MÃƒâ€°DIO")

MESSAGE_MODE_MANUAL = "manual"
MESSAGE_MODE_AUTOMATICO = "automatico"
VALID_MESSAGE_MODES = {MESSAGE_MODE_MANUAL, MESSAGE_MODE_AUTOMATICO}


def get_connection(db_path: str = None) -> sqlite3.Connection:
    db_path = db_path or settings.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None, schema_path: str = "database/schema.sql") -> None:
    db_path = db_path or settings.DATABASE_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with open(schema_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()
    with closing(get_connection(db_path)) as conn:
        conn.executescript(schema_sql)
        _apply_migrations(conn)
        conn.commit()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "estabelecimentos", "aprovado_disparo", "INTEGER DEFAULT 0")
    _ensure_column(conn, "estabelecimentos", "status_whatsapp", "TEXT DEFAULT 'pendente'")
    _ensure_column(conn, "fila_disparos", "origem_disparo", "TEXT DEFAULT 'manual'")

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS fila_disparos (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
            telefone            TEXT,
            mensagem            TEXT,
            origem_disparo      TEXT DEFAULT 'manual',
            status              TEXT DEFAULT 'pendente',
            tentativas          INTEGER DEFAULT 0,
            data_agendamento    TEXT,
            data_envio          TEXT,
            erro_descricao      TEXT,
            resposta_recebida   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS configuracoes_operacionais (
            id            INTEGER PRIMARY KEY CHECK (id = 1),
            modo_envio    TEXT DEFAULT 'manual',
            atualizado_em TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_estabelecimentos_status_whatsapp
            ON estabelecimentos(status_whatsapp);

        CREATE INDEX IF NOT EXISTS idx_estabelecimentos_aprovado_disparo
            ON estabelecimentos(aprovado_disparo);

        CREATE INDEX IF NOT EXISTS idx_fila_disparos_status_agendamento
            ON fila_disparos(status, data_agendamento);
        """
    )
    _ensure_operational_config_row(conn)


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    existing_columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def _normalize_city(value: Optional[str]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _current_local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def _current_local_timestamp() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _normalize_message_mode(value: Optional[str]) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in VALID_MESSAGE_MODES else MESSAGE_MODE_MANUAL


def _ensure_operational_config_row(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO configuracoes_operacionais (id, modo_envio, atualizado_em)
        SELECT 1, ?, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM configuracoes_operacionais
            WHERE id = 1
        )
        """,
        (MESSAGE_MODE_MANUAL, _current_local_timestamp()),
    )


def _expand_prioridade_values(values: List[str]) -> List[str]:
    expanded: List[str] = []
    for value in values:
        normalized = (value or "").strip().upper()
        if normalized in PRIORIDADE_MEDIA_ALIASES:
            expanded.extend(PRIORIDADE_MEDIA_ALIASES)
        else:
            expanded.append(value)
    return list(dict.fromkeys(expanded))


def _expand_classificacao_values(values: List[str]) -> List[str]:
    expanded: List[str] = []
    for value in values:
        normalized = (value or "").strip().upper()
        if normalized in CLASSIFICACAO_MEDIA_ALIASES:
            expanded.extend(CLASSIFICACAO_MEDIA_ALIASES)
        else:
            expanded.append(value)
    return list(dict.fromkeys(expanded))


def estabelecimento_exists(conn: sqlite3.Connection, nome: Optional[str], cidade: Optional[str]) -> bool:
    if not nome:
        return False
    row = conn.execute(
        "SELECT 1 FROM estabelecimentos WHERE nome=? AND cidade=? LIMIT 1",
        (str(nome).strip(), _normalize_city(cidade)),
    ).fetchone()
    return row is not None


def upsert_estabelecimento(conn: sqlite3.Connection, data: Dict) -> int:
    payload = dict(data)
    payload["cidade"] = _normalize_city(payload.get("cidade"))

    sql = """
    INSERT INTO estabelecimentos (
        nome, categoria, cidade, bairro, telefone, site,
        nota_media, total_avaliacoes, link_origem, fonte,
        data_coleta, dono_responde, score_oportunidade,
        faixa_classificacao, prioridade_lead, resumo_queixas
    ) VALUES (
        :nome, :categoria, :cidade, :bairro, :telefone, :site,
        :nota_media, :total_avaliacoes, :link_origem, :fonte,
        :data_coleta, :dono_responde, :score_oportunidade,
        :faixa_classificacao, :prioridade_lead, :resumo_queixas
    )
    ON CONFLICT(nome, cidade) DO UPDATE SET
        categoria=excluded.categoria,
        bairro=excluded.bairro,
        telefone=excluded.telefone,
        site=excluded.site,
        nota_media=excluded.nota_media,
        total_avaliacoes=excluded.total_avaliacoes,
        link_origem=excluded.link_origem,
        fonte=excluded.fonte,
        data_coleta=excluded.data_coleta,
        dono_responde=excluded.dono_responde,
        score_oportunidade=excluded.score_oportunidade,
        faixa_classificacao=excluded.faixa_classificacao,
        prioridade_lead=excluded.prioridade_lead,
        resumo_queixas=excluded.resumo_queixas;
    """
    conn.execute(sql, payload)
    conn.commit()
    row = conn.execute(
        "SELECT id FROM estabelecimentos WHERE nome=? AND cidade=?",
        (payload["nome"], payload["cidade"]),
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"Nao foi possivel recuperar o estabelecimento salvo: nome={payload['nome']!r}, cidade={payload['cidade']!r}"
        )
    return int(row["id"])


def add_coleta_historico(
    conn: sqlite3.Connection,
    estabelecimento_id: int,
    data_coleta: str,
    nota_media: float,
    total_avaliacoes: int,
    score_oportunidade: float,
) -> None:
    conn.execute(
        """
        INSERT INTO coletas_historico
            (estabelecimento_id, data_coleta, nota_media, total_avaliacoes, score_oportunidade)
        VALUES
            (?, ?, ?, ?, ?)
        """,
        (estabelecimento_id, data_coleta, nota_media, total_avaliacoes, score_oportunidade),
    )
    conn.commit()


def add_comentarios(
    conn: sqlite3.Connection,
    estabelecimento_id: int,
    comentarios: Iterable[Dict],
    data_coleta: str,
) -> None:
    to_insert = [
        (
            comentario.get("texto", ""),
            comentario.get("estrelas"),
            comentario.get("data_comentario"),
            data_coleta,
            estabelecimento_id,
        )
        for comentario in comentarios
        if comentario.get("texto")
    ]
    if not to_insert:
        return
    conn.executemany(
        """
        INSERT INTO comentarios (texto, estrelas, data_comentario, data_coleta, estabelecimento_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        to_insert,
    )
    conn.commit()


def add_queixas(
    conn: sqlite3.Connection,
    estabelecimento_id: int,
    queixas: Dict[str, int],
    data_coleta: str,
) -> None:
    rows = [
        (categoria, contagem, data_coleta, estabelecimento_id)
        for categoria, contagem in queixas.items()
        if contagem and contagem > 0
    ]
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO queixas_categorias (categoria, contagem, data_coleta, estabelecimento_id)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def _build_filters(filters: Dict) -> Tuple[str, List]:
    clauses = []
    params: List = []

    if classificacoes := filters.get("classificacao"):
        values = _expand_classificacao_values(classificacoes)
        placeholders = ",".join("?" * len(values))
        clauses.append(f"faixa_classificacao IN ({placeholders})")
        params.extend(values)

    if prioridades := filters.get("prioridade"):
        values = _expand_prioridade_values(prioridades)
        placeholders = ",".join("?" * len(values))
        clauses.append(f"prioridade_lead IN ({placeholders})")
        params.extend(values)

    if fontes := filters.get("fonte"):
        placeholders = ",".join("?" * len(fontes))
        clauses.append(f"fonte IN ({placeholders})")
        params.extend(fontes)

    if cidade := filters.get("cidade"):
        clauses.append("cidade = ?")
        params.append(cidade)

    if categoria := filters.get("categoria"):
        clauses.append("categoria = ?")
        params.append(categoria)

    if status_list := filters.get("status_whatsapp"):
        placeholders = ",".join("?" * len(status_list))
        clauses.append(f"status_whatsapp IN ({placeholders})")
        params.extend(status_list)

    approved_filter = filters.get("aprovado_disparo")
    if approved_filter in {"approved", "1", 1, True}:
        clauses.append("aprovado_disparo = 1")
    elif approved_filter in {"not_approved", "0", 0, False}:
        clauses.append("aprovado_disparo = 0")

    if (score_min := filters.get("score_min")) is not None:
        clauses.append("score_oportunidade >= ?")
        params.append(score_min)

    where_clause = ""
    if clauses:
        where_clause = "WHERE " + " AND ".join(clauses)
    return where_clause, params


ALLOWED_ORDER = {
    "score_oportunidade": "score_oportunidade",
    "nota_media": "nota_media",
    "total_avaliacoes": "total_avaliacoes",
    "data_coleta": "data_coleta",
    "nome": "nome",
    "categoria": "categoria",
    "cidade": "cidade",
    "prioridade_lead": "prioridade_lead",
    "status_whatsapp": "status_whatsapp",
    "aprovado_disparo": "aprovado_disparo",
}


def query_estabelecimentos(
    conn: sqlite3.Connection,
    filters: Dict,
    page: int,
    per_page: int,
    order_by: str = "score_oportunidade",
    order_dir: str = "DESC",
) -> Dict:
    order_col = ALLOWED_ORDER.get(order_by, "score_oportunidade")
    order_dir = "ASC" if str(order_dir).lower() == "asc" else "DESC"

    where_clause, params = _build_filters(filters)
    offset = (page - 1) * per_page

    total_sql = f"SELECT COUNT(*) as total FROM estabelecimentos {where_clause}"
    total = conn.execute(total_sql, params).fetchone()["total"]

    data_sql = f"""
        SELECT * FROM estabelecimentos
        {where_clause}
        ORDER BY {order_col} {order_dir}, score_oportunidade DESC, id DESC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(data_sql, params + [per_page, offset]).fetchall()
    data = [dict(row) for row in rows]
    pages = (total + per_page - 1) // per_page if per_page else 1

    return {"total": total, "page": page, "per_page": per_page, "pages": pages, "data": data}


def _count_with_query(conn: sqlite3.Connection, sql: str, params: Tuple = ()) -> int:
    return int(conn.execute(sql, params).fetchone()["c"])


def get_resumo(conn: sqlite3.Connection) -> Dict:
    today = _current_local_date()
    total = _count_with_query(conn, "SELECT COUNT(*) as c FROM estabelecimentos")
    alta = _count_with_query(
        conn,
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead='ALTA'",
    )
    media_placeholders = ",".join("?" * len(PRIORIDADE_MEDIA_ALIASES))
    media = _count_with_query(
        conn,
        f"SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead IN ({media_placeholders})",
        PRIORIDADE_MEDIA_ALIASES,
    )
    baixa = _count_with_query(
        conn,
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead='BAIXA'",
    )
    aprovados = _count_with_query(
        conn,
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE aprovado_disparo = 1",
    )
    aguardando_envio = _count_with_query(
        conn,
        """
        SELECT COUNT(*) as c
        FROM estabelecimentos
        WHERE aprovado_disparo = 1
          AND status_whatsapp = 'pendente'
          AND telefone IS NOT NULL
          AND TRIM(telefone) <> ''
        """,
    )
    enviados_hoje = _count_with_query(
        conn,
        """
        SELECT COUNT(*) as c
        FROM fila_disparos
        WHERE status = 'enviado'
          AND data_envio LIKE ?
        """,
        (f"{today}%",),
    )
    score_medio_row = conn.execute(
        "SELECT AVG(score_oportunidade) as avg_score FROM estabelecimentos"
    ).fetchone()
    score_medio = score_medio_row["avg_score"] or 0
    ultima = conn.execute(
        "SELECT MAX(data_coleta) as ultima FROM estabelecimentos"
    ).fetchone()["ultima"]
    return {
        "total": total,
        "alta": alta,
        "media": media,
        "baixa": baixa,
        "aprovados": aprovados,
        "enviados_hoje": enviados_hoje,
        "aguardando_envio": aguardando_envio,
        "score_medio": score_medio,
        "ultima_coleta": ultima,
    }


def list_cidades(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT DISTINCT cidade FROM estabelecimentos WHERE cidade IS NOT NULL ORDER BY cidade ASC"
    ).fetchall()
    return [row["cidade"] for row in rows if row["cidade"]]


def list_categorias(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT DISTINCT categoria FROM estabelecimentos WHERE categoria IS NOT NULL ORDER BY categoria ASC"
    ).fetchall()
    return [row["categoria"] for row in rows if row["categoria"]]


def fetch_for_export(conn: sqlite3.Connection, filters: Dict) -> List[Dict]:
    where_clause, params = _build_filters(filters)
    sql = f"SELECT * FROM estabelecimentos {where_clause} ORDER BY score_oportunidade DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def get_operational_config(conn: sqlite3.Connection) -> Dict:
    _ensure_operational_config_row(conn)
    row = conn.execute(
        """
        SELECT modo_envio, atualizado_em
        FROM configuracoes_operacionais
        WHERE id = 1
        """
    ).fetchone()
    return dict(row) if row else {"modo_envio": MESSAGE_MODE_MANUAL, "atualizado_em": None}


def update_operational_mode(conn: sqlite3.Connection, modo_envio: str) -> Dict:
    normalized_mode = _normalize_message_mode(modo_envio)
    timestamp = _current_local_timestamp()
    _ensure_operational_config_row(conn)
    conn.execute(
        """
        UPDATE configuracoes_operacionais
        SET modo_envio = ?,
            atualizado_em = ?
        WHERE id = 1
        """,
        (normalized_mode, timestamp),
    )
    conn.commit()
    return {"modo_envio": normalized_mode, "atualizado_em": timestamp}


def update_aprovacao_lote(conn: sqlite3.Connection, ids: List[int], aprovado: bool) -> int:
    clean_ids = [int(item) for item in ids if item is not None]
    if not clean_ids:
        return 0
    placeholders = ",".join("?" * len(clean_ids))
    cursor = conn.execute(
        f"UPDATE estabelecimentos SET aprovado_disparo = ? WHERE id IN ({placeholders})",
        [1 if aprovado else 0] + clean_ids,
    )
    if not aprovado:
        conn.execute(
            f"""
            DELETE FROM fila_disparos
            WHERE estabelecimento_id IN ({placeholders})
              AND status = 'pendente'
            """,
            clean_ids,
        )
    conn.commit()
    return cursor.rowcount or 0


def list_estabelecimentos_para_disparo(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM estabelecimentos
        WHERE aprovado_disparo = 1
          AND status_whatsapp = 'pendente'
          AND telefone IS NOT NULL
          AND TRIM(telefone) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM fila_disparos f
              WHERE f.estabelecimento_id = estabelecimentos.id
                AND f.status = 'pendente'
          )
        ORDER BY score_oportunidade DESC, total_avaliacoes DESC, id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def list_estabelecimentos_para_fila_por_ids(
    conn: sqlite3.Connection,
    ids: List[int],
) -> List[Dict]:
    clean_ids = [int(item) for item in ids if item is not None]
    if not clean_ids:
        return []

    placeholders = ",".join("?" * len(clean_ids))
    rows = conn.execute(
        f"""
        SELECT *
        FROM estabelecimentos
        WHERE id IN ({placeholders})
          AND status_whatsapp = 'pendente'
          AND telefone IS NOT NULL
          AND TRIM(telefone) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM fila_disparos f
              WHERE f.estabelecimento_id = estabelecimentos.id
                AND f.status = 'pendente'
          )
        ORDER BY score_oportunidade DESC, total_avaliacoes DESC, id ASC
        """,
        clean_ids,
    ).fetchall()
    return [dict(row) for row in rows]


def list_estabelecimentos_mensagens(
    conn: sqlite3.Connection,
    search: str = "",
    limit: int = 60,
) -> List[Dict]:
    clauses = ["TRIM(COALESCE(e.telefone, '')) <> ''"]
    params: List = []
    normalized_search = (search or "").strip()
    if normalized_search:
        like_value = f"%{normalized_search}%"
        clauses.append(
            """
            (
                e.nome LIKE ?
                OR e.cidade LIKE ?
                OR e.categoria LIKE ?
                OR e.telefone LIKE ?
            )
            """
        )
        params.extend([like_value, like_value, like_value, like_value])

    where_clause = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        WITH pending_queue AS (
            SELECT fila.*
            FROM fila_disparos fila
            INNER JOIN (
                SELECT estabelecimento_id, MIN(id) AS selected_id
                FROM fila_disparos
                WHERE status = 'pendente'
                GROUP BY estabelecimento_id
            ) pending_lookup
                ON pending_lookup.selected_id = fila.id
        )
        SELECT
            e.*,
            pending_queue.id AS queue_item_id,
            pending_queue.status AS queue_status,
            pending_queue.data_agendamento AS queue_data_agendamento,
            pending_queue.origem_disparo AS queue_origem_disparo,
            CASE
                WHEN pending_queue.id IS NOT NULL THEN 'na_fila'
                WHEN e.status_whatsapp = 'enviado' THEN 'enviado'
                WHEN e.status_whatsapp = 'sem_whatsapp' THEN 'sem_whatsapp'
                WHEN e.status_whatsapp = 'erro' THEN 'erro'
                WHEN e.aprovado_disparo = 1 THEN 'aprovado'
                ELSE 'disponivel'
            END AS dispatch_state
        FROM estabelecimentos e
        LEFT JOIN pending_queue
            ON pending_queue.estabelecimento_id = e.id
        WHERE {where_clause}
        ORDER BY
            CASE
                WHEN pending_queue.id IS NOT NULL THEN 2
                WHEN e.status_whatsapp = 'enviado' THEN 5
                WHEN e.status_whatsapp = 'sem_whatsapp' THEN 4
                WHEN e.status_whatsapp = 'erro' THEN 3
                WHEN e.aprovado_disparo = 1 THEN 1
                ELSE 0
            END ASC,
            e.score_oportunidade DESC,
            e.total_avaliacoes DESC,
            e.id DESC
        LIMIT ?
        """,
        params + [max(1, min(limit, 200))],
    ).fetchall()
    return [dict(row) for row in rows]


def get_pending_queue_count(conn: sqlite3.Connection) -> int:
    return _count_with_query(
        conn,
        "SELECT COUNT(*) as c FROM fila_disparos WHERE status = 'pendente'",
    )


def get_last_pending_schedule(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        """
        SELECT MAX(data_agendamento) AS last_schedule
        FROM fila_disparos
        WHERE status = 'pendente'
          AND data_agendamento IS NOT NULL
        """
    ).fetchone()
    return row["last_schedule"] if row else None


def count_sent_on_date(conn: sqlite3.Connection, date_prefix: str) -> int:
    return _count_with_query(
        conn,
        """
        SELECT COUNT(*) as c
        FROM fila_disparos
        WHERE status = 'enviado'
          AND data_envio LIKE ?
        """,
        (f"{date_prefix}%",),
    )


def count_pending_scheduled_on_date(conn: sqlite3.Connection, date_prefix: str) -> int:
    return _count_with_query(
        conn,
        """
        SELECT COUNT(*) as c
        FROM fila_disparos
        WHERE status = 'pendente'
          AND data_agendamento LIKE ?
        """,
        (f"{date_prefix}%",),
    )


def create_queue_item(
    conn: sqlite3.Connection,
    estabelecimento_id: int,
    telefone: str,
    mensagem: str,
    data_agendamento: str,
    origem_disparo: str = "manual",
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO fila_disparos (
            estabelecimento_id,
            telefone,
            mensagem,
            origem_disparo,
            status,
            tentativas,
            data_agendamento,
            data_envio,
            erro_descricao,
            resposta_recebida
        ) VALUES (?, ?, ?, ?, 'pendente', 0, ?, NULL, NULL, 0)
        """,
        (estabelecimento_id, telefone, mensagem, origem_disparo, data_agendamento),
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_fila_disparos(conn: sqlite3.Connection, limit: int = 300) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT
            f.*,
            e.nome,
            e.categoria,
            e.cidade,
            e.status_whatsapp,
            e.aprovado_disparo
        FROM fila_disparos f
        LEFT JOIN estabelecimentos e ON e.id = f.estabelecimento_id
        ORDER BY
            CASE f.status
                WHEN 'pendente' THEN 0
                WHEN 'erro' THEN 1
                WHEN 'sem_whatsapp' THEN 2
                ELSE 3
            END,
            COALESCE(f.data_agendamento, f.data_envio, '') ASC,
            f.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_next_due_queue_item(conn: sqlite3.Connection, now_iso: str) -> Optional[Dict]:
    row = conn.execute(
        """
        SELECT
            f.*,
            e.nome,
            e.categoria,
            e.status_whatsapp AS estabelecimento_status
        FROM fila_disparos f
        INNER JOIN estabelecimentos e ON e.id = f.estabelecimento_id
        WHERE f.status = 'pendente'
          AND e.aprovado_disparo = 1
          AND e.status_whatsapp = 'pendente'
          AND f.data_agendamento IS NOT NULL
          AND f.data_agendamento <= ?
        ORDER BY f.data_agendamento ASC, f.id ASC
        LIMIT 1
        """,
        (now_iso,),
    ).fetchone()
    return dict(row) if row else None


def get_next_pending_schedule(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        """
        SELECT MIN(data_agendamento) AS next_schedule
        FROM fila_disparos
        WHERE status = 'pendente'
          AND data_agendamento IS NOT NULL
        """
    ).fetchone()
    return row["next_schedule"] if row else None


def update_estabelecimento_status(conn: sqlite3.Connection, estabelecimento_id: int, status: str) -> None:
    conn.execute(
        "UPDATE estabelecimentos SET status_whatsapp = ? WHERE id = ?",
        (status, estabelecimento_id),
    )
    conn.commit()


def mark_queue_item_sent(conn: sqlite3.Connection, queue_id: int, estabelecimento_id: int, sent_at: str) -> None:
    conn.execute(
        """
        UPDATE fila_disparos
        SET status = 'enviado',
            data_envio = ?,
            erro_descricao = NULL
        WHERE id = ?
        """,
        (sent_at, queue_id),
    )
    conn.execute(
        """
        UPDATE estabelecimentos
        SET status_whatsapp = 'enviado'
        WHERE id = ?
        """,
        (estabelecimento_id,),
    )
    conn.commit()


def mark_queue_item_sem_whatsapp(conn: sqlite3.Connection, queue_id: int, estabelecimento_id: int, error_text: str) -> None:
    conn.execute(
        """
        UPDATE fila_disparos
        SET status = 'sem_whatsapp',
            erro_descricao = ?
        WHERE id = ?
        """,
        (error_text, queue_id),
    )
    conn.execute(
        """
        UPDATE estabelecimentos
        SET status_whatsapp = 'sem_whatsapp'
        WHERE id = ?
        """,
        (estabelecimento_id,),
    )
    conn.commit()


def mark_queue_item_retry(
    conn: sqlite3.Connection,
    queue_id: int,
    tentativas: int,
    error_text: str,
    next_schedule_at: str,
) -> None:
    conn.execute(
        """
        UPDATE fila_disparos
        SET status = 'pendente',
            tentativas = ?,
            erro_descricao = ?,
            data_agendamento = ?
        WHERE id = ?
        """,
        (tentativas, error_text, next_schedule_at, queue_id),
    )
    conn.commit()


def mark_queue_item_error(
    conn: sqlite3.Connection,
    queue_id: int,
    estabelecimento_id: int,
    tentativas: int,
    error_text: str,
) -> None:
    conn.execute(
        """
        UPDATE fila_disparos
        SET status = 'erro',
            tentativas = ?,
            erro_descricao = ?
        WHERE id = ?
        """,
        (tentativas, error_text, queue_id),
    )
    conn.execute(
        """
        UPDATE estabelecimentos
        SET status_whatsapp = 'erro'
        WHERE id = ?
        """,
        (estabelecimento_id,),
    )
    conn.commit()
