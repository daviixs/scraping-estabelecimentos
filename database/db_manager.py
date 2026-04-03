import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from config import settings


def get_connection(db_path: str = None) -> sqlite3.Connection:
    db_path = db_path or settings.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(
    db_path: str = None, schema_path: str = "database/schema.sql"
) -> None:
    db_path = db_path or settings.DATABASE_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with closing(get_connection(db_path)) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def _normalize_city(value: Optional[str]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def estabelecimento_exists(conn: sqlite3.Connection, nome: Optional[str], cidade: Optional[str]) -> bool:
    if not nome:
        return False
    row = conn.execute(
        "SELECT 1 FROM estabelecimentos WHERE nome=? AND cidade=? LIMIT 1",
        (str(nome).strip(), _normalize_city(cidade)),
    ).fetchone()
    return row is not None


def upsert_estabelecimento(conn: sqlite3.Connection, data: Dict) -> int:
    """
    Insere ou atualiza um estabelecimento pelo par (nome, cidade).
    Retorna o id do registro.
    """
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
    # recuperar id
    cur = conn.execute(
        "SELECT id FROM estabelecimentos WHERE nome=? AND cidade=?",
        (payload["nome"], payload["cidade"]),
    )
    row = cur.fetchone()
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
        placeholders = ",".join("?" * len(classificacoes))
        clauses.append(f"faixa_classificacao IN ({placeholders})")
        params.extend(classificacoes)

    if prioridades := filters.get("prioridade"):
        placeholders = ",".join("?" * len(prioridades))
        clauses.append(f"prioridade_lead IN ({placeholders})")
        params.extend(prioridades)

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
        ORDER BY {order_col} {order_dir}
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(data_sql, params + [per_page, offset]).fetchall()
    data = [dict(row) for row in rows]
    pages = (total + per_page - 1) // per_page if per_page else 1

    return {"total": total, "page": page, "per_page": per_page, "pages": pages, "data": data}


def get_resumo(conn: sqlite3.Connection) -> Dict:
    total = conn.execute("SELECT COUNT(*) as c FROM estabelecimentos").fetchone()["c"]
    alta = conn.execute(
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead='ALTA'"
    ).fetchone()["c"]
    media = conn.execute(
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead='MÉDIA'"
    ).fetchone()["c"]
    baixa = conn.execute(
        "SELECT COUNT(*) as c FROM estabelecimentos WHERE prioridade_lead='BAIXA'"
    ).fetchone()["c"]
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
        "score_medio": score_medio,
        "ultima_coleta": ultima,
    }


def list_cidades(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute("SELECT DISTINCT cidade FROM estabelecimentos WHERE cidade IS NOT NULL").fetchall()
    return [row["cidade"] for row in rows if row["cidade"]]


def list_categorias(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute(
        "SELECT DISTINCT categoria FROM estabelecimentos WHERE categoria IS NOT NULL"
    ).fetchall()
    return [row["categoria"] for row in rows if row["categoria"]]


def fetch_for_export(conn: sqlite3.Connection, filters: Dict) -> List[Dict]:
    where_clause, params = _build_filters(filters)
    sql = f"SELECT * FROM estabelecimentos {where_clause} ORDER BY score_oportunidade DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
