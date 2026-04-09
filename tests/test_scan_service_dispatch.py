from database import db_manager
from services.scan_service import _apply_automatic_dispatch
from whatsapp.scheduler import WhatsAppDispatchScheduler


def _sample_data(nome: str = "Lead Auto") -> dict:
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
        "fonte": "google_maps",
        "data_coleta": "2026-04-09T10:00:00-03:00",
        "dono_responde": 0,
        "score_oportunidade": 80,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "ALTA",
        "resumo_queixas": "atendimento (1)",
    }


def test_apply_automatic_dispatch_only_when_mode_is_enabled(temp_db_path, monkeypatch):
    monkeypatch.setattr("config.settings.DATABASE_PATH", str(temp_db_path))
    db_manager.init_db(db_path=str(temp_db_path), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(temp_db_path))
    estab_id = db_manager.upsert_estabelecimento(conn, _sample_data())
    db_manager.update_operational_mode(conn, "automatico")
    conn.close()

    scheduler = WhatsAppDispatchScheduler()
    monkeypatch.setattr("whatsapp.get_dispatch_scheduler", lambda: scheduler)

    created = _apply_automatic_dispatch([estab_id])

    conn = db_manager.get_connection(str(temp_db_path))
    estabelecimento = conn.execute(
        "SELECT aprovado_disparo FROM estabelecimentos WHERE id = ?",
        (estab_id,),
    ).fetchone()
    fila = db_manager.list_fila_disparos(conn)

    assert created == 1
    assert estabelecimento["aprovado_disparo"] == 1
    assert fila[0]["origem_disparo"] == "automatico"


def test_apply_automatic_dispatch_ignores_manual_mode(temp_db_path, monkeypatch):
    monkeypatch.setattr("config.settings.DATABASE_PATH", str(temp_db_path))
    db_manager.init_db(db_path=str(temp_db_path), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(temp_db_path))
    estab_id = db_manager.upsert_estabelecimento(conn, _sample_data("Lead Manual"))
    db_manager.update_operational_mode(conn, "manual")
    conn.close()

    scheduler = WhatsAppDispatchScheduler()
    monkeypatch.setattr("whatsapp.get_dispatch_scheduler", lambda: scheduler)

    created = _apply_automatic_dispatch([estab_id])

    conn = db_manager.get_connection(str(temp_db_path))
    estabelecimento = conn.execute(
        "SELECT aprovado_disparo FROM estabelecimentos WHERE id = ?",
        (estab_id,),
    ).fetchone()

    assert created == 0
    assert estabelecimento["aprovado_disparo"] == 0
    assert db_manager.list_fila_disparos(conn) == []
