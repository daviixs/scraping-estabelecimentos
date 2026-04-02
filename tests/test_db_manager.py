from database import db_manager
from pathlib import Path
import sqlite3
from datetime import datetime


def test_upsert_and_history(tmp_path):
    db_file = tmp_path / "test.db"
    schema_path = Path("database/schema.sql")
    db_manager.init_db(db_path=str(db_file), schema_path=str(schema_path))
    conn = db_manager.get_connection(str(db_file))
    data = {
        "nome": "Loja Teste",
        "categoria": "Restaurante",
        "cidade": "Franca",
        "bairro": "Centro",
        "telefone": "123",
        "site": "http://exemplo.com",
        "nota_media": 4.2,
        "total_avaliacoes": 10,
        "link_origem": "http://origem",
        "fonte": "manual",
        "data_coleta": datetime.utcnow().isoformat(),
        "dono_responde": 0,
        "score_oportunidade": 50,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "MÉDIA",
        "resumo_queixas": "atendimento (1)",
    }
    estab_id = db_manager.upsert_estabelecimento(conn, data)
    assert estab_id == 1
    db_manager.add_coleta_historico(conn, estab_id, data["data_coleta"], data["nota_media"], data["total_avaliacoes"], data["score_oportunidade"])
    row = conn.execute("SELECT COUNT(*) as c FROM coletas_historico").fetchone()
    assert row["c"] == 1
