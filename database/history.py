from typing import Optional

from config import settings


def detect_queda(conn, estabelecimento_id: int, nota_atual: Optional[float]) -> bool:
    """
    Retorna True se a nota atual caiu pelo menos DELTA_QUEDA_MINIMO
    em relação à última coleta registrada.
    """
    if nota_atual is None:
        return False
    row = conn.execute(
        """
        SELECT nota_media FROM coletas_historico
        WHERE estabelecimento_id = ?
        ORDER BY data_coleta DESC
        LIMIT 1
        """,
        (estabelecimento_id,),
    ).fetchone()
    if not row or row["nota_media"] is None:
        return False
    nota_anterior = float(row["nota_media"])
    return (nota_anterior - float(nota_atual)) >= settings.DELTA_QUEDA_MINIMO
