from database import db_manager
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


def test_upsert_and_history(temp_db_path):
    db_file = temp_db_path
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
        "data_coleta": datetime.now(timezone.utc).isoformat(),
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


def test_upsert_sem_cidade_reutiliza_registro(temp_db_path):
    db_file = temp_db_path
    schema_path = Path("database/schema.sql")
    db_manager.init_db(db_path=str(db_file), schema_path=str(schema_path))
    conn = db_manager.get_connection(str(db_file))
    data = {
        "nome": "Loja Sem Cidade",
        "categoria": "Restaurante",
        "cidade": None,
        "bairro": "Centro",
        "telefone": "123",
        "site": None,
        "nota_media": 4.2,
        "total_avaliacoes": 10,
        "link_origem": "http://origem",
        "fonte": "manual",
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "dono_responde": 0,
        "score_oportunidade": 50,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "MÃ‰DIA",
        "resumo_queixas": "atendimento (1)",
    }

    primeiro_id = db_manager.upsert_estabelecimento(conn, data)
    data["telefone"] = "456"
    segundo_id = db_manager.upsert_estabelecimento(conn, data)

    assert primeiro_id == segundo_id == 1
    row = conn.execute("SELECT COUNT(*) as c, MAX(telefone) as telefone FROM estabelecimentos").fetchone()
    assert row["c"] == 1
    assert row["telefone"] == "456"
