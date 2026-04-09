from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from database import db_manager


def _sample_data(nome: str = "Loja Teste") -> dict:
    return {
        "nome": nome,
        "categoria": "Restaurante",
        "cidade": "Franca",
        "bairro": "Centro",
        "telefone": "16999990000",
        "site": "http://exemplo.com",
        "nota_media": 4.2,
        "total_avaliacoes": 10,
        "link_origem": "http://origem",
        "fonte": "manual",
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "dono_responde": 0,
        "score_oportunidade": 50,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "ALTA",
        "resumo_queixas": "atendimento (1)",
    }


def test_upsert_and_history(temp_db_path):
    db_file = temp_db_path
    schema_path = Path("database/schema.sql")
    db_manager.init_db(db_path=str(db_file), schema_path=str(schema_path))
    conn = db_manager.get_connection(str(db_file))
    data = _sample_data()

    estab_id = db_manager.upsert_estabelecimento(conn, data)
    assert estab_id == 1

    db_manager.add_coleta_historico(
        conn,
        estab_id,
        data["data_coleta"],
        data["nota_media"],
        data["total_avaliacoes"],
        data["score_oportunidade"],
    )
    row = conn.execute("SELECT COUNT(*) as c FROM coletas_historico").fetchone()
    assert row["c"] == 1


def test_upsert_sem_cidade_reutiliza_registro(temp_db_path):
    db_file = temp_db_path
    schema_path = Path("database/schema.sql")
    db_manager.init_db(db_path=str(db_file), schema_path=str(schema_path))
    conn = db_manager.get_connection(str(db_file))
    data = _sample_data("Loja Sem Cidade")
    data["cidade"] = None

    primeiro_id = db_manager.upsert_estabelecimento(conn, data)
    data["telefone"] = "456"
    segundo_id = db_manager.upsert_estabelecimento(conn, data)

    assert primeiro_id == segundo_id == 1
    row = conn.execute("SELECT COUNT(*) as c, MAX(telefone) as telefone FROM estabelecimentos").fetchone()
    assert row["c"] == 1
    assert row["telefone"] == "456"


def test_init_db_migrates_old_schema(temp_db_path):
    db_file = temp_db_path
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        CREATE TABLE estabelecimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cidade TEXT,
            categoria TEXT
        );

        CREATE TABLE coletas_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estabelecimento_id INTEGER,
            data_coleta TEXT
        );

        CREATE TABLE comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estabelecimento_id INTEGER,
            texto TEXT
        );

        CREATE TABLE queixas_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estabelecimento_id INTEGER,
            categoria TEXT
        );
        """
    )
    conn.commit()
    conn.close()

    db_manager.init_db(db_path=str(db_file), schema_path="database/schema.sql")
    migrated = db_manager.get_connection(str(db_file))

    columns = {
        row["name"]
        for row in migrated.execute("PRAGMA table_info(estabelecimentos)").fetchall()
    }
    assert "aprovado_disparo" in columns
    assert "status_whatsapp" in columns

    fila_exists = migrated.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='fila_disparos'"
    ).fetchone()
    assert fila_exists is not None
    fila_columns = {
        row["name"]
        for row in migrated.execute("PRAGMA table_info(fila_disparos)").fetchall()
    }
    assert "origem_disparo" in fila_columns

    config_exists = migrated.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='configuracoes_operacionais'"
    ).fetchone()
    assert config_exists is not None


def test_aprovacao_lote_e_fila(temp_db_path):
    db_file = temp_db_path
    db_manager.init_db(db_path=str(db_file), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(db_file))

    first_id = db_manager.upsert_estabelecimento(conn, _sample_data("Loja 1"))
    second = _sample_data("Loja 2")
    second["telefone"] = "16999991111"
    second_id = db_manager.upsert_estabelecimento(conn, second)

    updated = db_manager.update_aprovacao_lote(conn, [first_id, second_id], aprovado=True)
    assert updated == 2

    aprovados = db_manager.list_estabelecimentos_para_disparo(conn)
    assert {row["id"] for row in aprovados} == {first_id, second_id}

    queue_id = db_manager.create_queue_item(
        conn,
        estabelecimento_id=first_id,
        telefone="5516999990000",
        mensagem="teste",
        data_agendamento="2026-04-09T09:00:00-03:00",
    )
    assert queue_id == 1
    fila = db_manager.list_fila_disparos(conn)
    assert fila[0]["estabelecimento_id"] == first_id
    assert fila[0]["origem_disparo"] == "manual"

    removed = db_manager.update_aprovacao_lote(conn, [first_id], aprovado=False)
    assert removed == 1
    fila_restante = db_manager.list_fila_disparos(conn)
    assert all(item["estabelecimento_id"] != first_id for item in fila_restante)


def test_operational_mode_and_message_candidates(temp_db_path):
    db_file = temp_db_path
    db_manager.init_db(db_path=str(db_file), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(db_file))

    first_id = db_manager.upsert_estabelecimento(conn, _sample_data("Lead Disponivel"))
    second = _sample_data("Lead Aprovado")
    second["telefone"] = "16999992222"
    second_id = db_manager.upsert_estabelecimento(conn, second)
    conn.execute(
        "UPDATE estabelecimentos SET aprovado_disparo = 1 WHERE id = ?",
        (second_id,),
    )
    db_manager.create_queue_item(
        conn,
        estabelecimento_id=second_id,
        telefone="5516999992222",
        mensagem="teste",
        data_agendamento="2026-04-09T09:00:00-03:00",
        origem_disparo="automatico",
    )
    conn.commit()

    config = db_manager.get_operational_config(conn)
    assert config["modo_envio"] == "manual"

    updated = db_manager.update_operational_mode(conn, "automatico")
    assert updated["modo_envio"] == "automatico"

    rows = db_manager.list_estabelecimentos_mensagens(conn)
    by_name = {row["nome"]: row for row in rows}
    assert by_name["Lead Disponivel"]["dispatch_state"] == "disponivel"
    assert by_name["Lead Aprovado"]["dispatch_state"] == "na_fila"
    assert by_name["Lead Aprovado"]["queue_origem_disparo"] == "automatico"

    elegiveis = db_manager.list_estabelecimentos_para_fila_por_ids(conn, [first_id, second_id])
    assert [row["id"] for row in elegiveis] == [first_id]
