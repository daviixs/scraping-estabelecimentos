from datetime import datetime

from database import db_manager
from whatsapp.scheduler import WhatsAppDispatchScheduler


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
        "data_coleta": "2026-04-09T10:00:00-03:00",
        "dono_responde": 0,
        "score_oportunidade": 80,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "ALTA",
        "resumo_queixas": "atendimento (1)",
    }


def _prepare_db(temp_db_path, monkeypatch):
    monkeypatch.setattr("config.settings.DATABASE_PATH", str(temp_db_path))
    db_manager.init_db(db_path=str(temp_db_path), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(temp_db_path))
    estab_id = db_manager.upsert_estabelecimento(conn, _sample_data())
    conn.execute(
        "UPDATE estabelecimentos SET aprovado_disparo = 1, status_whatsapp = 'pendente' WHERE id = ?",
        (estab_id,),
    )
    conn.commit()
    conn.close()
    return estab_id


def test_scheduler_enfileira_e_envia(temp_db_path, monkeypatch):
    estab_id = _prepare_db(temp_db_path, monkeypatch)
    fixed_now = datetime.fromisoformat("2026-04-09T10:00:00-03:00")

    monkeypatch.setattr("whatsapp.scheduler._now_local", lambda: fixed_now)
    monkeypatch.setattr("whatsapp.scheduler.validate_whatsapp_number", lambda number: type("Result", (), {"exists": True, "normalized_number": "5516999990000"})())
    monkeypatch.setattr("whatsapp.scheduler.send_text_message", lambda number, text: {"ok": True})

    scheduler = WhatsAppDispatchScheduler()
    monkeypatch.setattr(scheduler, "ensure_background_worker", lambda: None)
    created = scheduler.enqueue_estabelecimentos([estab_id], source="manual", approve=False)
    snapshot = scheduler.start()

    conn = db_manager.get_connection(str(temp_db_path))
    fila = db_manager.list_fila_disparos(conn)
    estabelecimento = conn.execute("SELECT status_whatsapp FROM estabelecimentos WHERE id = ?", (estab_id,)).fetchone()

    assert created == 1
    assert snapshot["running"] is True
    assert len(fila) == 1
    assert fila[0]["status"] == "enviado"
    assert fila[0]["origem_disparo"] == "manual"
    assert estabelecimento["status_whatsapp"] == "enviado"


def test_scheduler_marca_sem_whatsapp(temp_db_path, monkeypatch):
    estab_id = _prepare_db(temp_db_path, monkeypatch)
    fixed_now = datetime.fromisoformat("2026-04-09T10:00:00-03:00")

    monkeypatch.setattr("whatsapp.scheduler._now_local", lambda: fixed_now)
    monkeypatch.setattr("whatsapp.scheduler.validate_whatsapp_number", lambda number: type("Result", (), {"exists": False, "normalized_number": "5516999990000"})())

    scheduler = WhatsAppDispatchScheduler()
    monkeypatch.setattr(scheduler, "ensure_background_worker", lambda: None)
    scheduler.enqueue_estabelecimentos([estab_id], source="manual", approve=False)
    scheduler.start()

    conn = db_manager.get_connection(str(temp_db_path))
    fila = db_manager.list_fila_disparos(conn)
    estabelecimento = conn.execute("SELECT status_whatsapp FROM estabelecimentos WHERE id = ?", (estab_id,)).fetchone()

    assert fila[0]["status"] == "sem_whatsapp"
    assert estabelecimento["status_whatsapp"] == "sem_whatsapp"


def test_scheduler_respeita_janela_util(temp_db_path, monkeypatch):
    estab_id = _prepare_db(temp_db_path, monkeypatch)
    fixed_now = datetime.fromisoformat("2026-04-09T20:30:00-03:00")

    monkeypatch.setattr("whatsapp.scheduler._now_local", lambda: fixed_now)
    scheduler = WhatsAppDispatchScheduler()
    monkeypatch.setattr(scheduler, "ensure_background_worker", lambda: None)
    scheduler.enqueue_estabelecimentos([estab_id], source="manual", approve=False)
    snapshot = scheduler.start()

    assert snapshot["next_run_at"].startswith("2026-04-10T09:00:00")
