import json
from datetime import datetime, timezone

import pytest

from config import settings
from database import db_manager
import dashboard


def _sample_estabelecimento(nome: str = "Padaria Teste") -> dict:
    return {
        "nome": nome,
        "categoria": "Padaria",
        "cidade": "Franca",
        "bairro": "Centro",
        "telefone": "16999990000",
        "site": None,
        "nota_media": 4.4,
        "total_avaliacoes": 120,
        "link_origem": "http://origem",
        "fonte": "apontador",
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "dono_responde": 0,
        "score_oportunidade": 55.0,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "ALTA",
        "resumo_queixas": "atendimento (2)",
    }


class FakeScheduler:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True
        return {
            "running": True,
            "paused": False,
            "next_run_at": "2026-04-09T09:00:00-03:00",
            "sent_today": 0,
            "pending_items": 1,
            "daily_limit": 30,
            "window_label": "09:00-18:00 dias uteis",
            "heartbeat_seconds": 15,
            "last_error": None,
            "enqueued": 1,
        }

    def pause(self):
        self.running = False
        return {
            "running": False,
            "paused": True,
            "next_run_at": None,
            "sent_today": 0,
            "pending_items": 1,
            "daily_limit": 30,
            "window_label": "09:00-18:00 dias uteis",
            "heartbeat_seconds": 15,
            "last_error": None,
        }

    def get_status_snapshot(self):
        return {
            "running": self.running,
            "paused": not self.running,
            "next_run_at": None,
            "sent_today": 0,
            "pending_items": 1,
            "daily_limit": 30,
            "window_label": "09:00-18:00 dias uteis",
            "heartbeat_seconds": 15,
            "last_error": None,
        }

    def sync_pending_queue(self):
        return 1

    def enqueue_estabelecimentos(self, ids, source="manual", approve=True):
        assert ids
        assert source in {"manual", "automatico"}
        return len(ids)


@pytest.fixture(scope="function")
def temp_db(temp_db_path, monkeypatch):
    db_file = temp_db_path
    monkeypatch.setattr(settings, "DATABASE_PATH", str(db_file))
    db_manager.init_db(db_path=str(db_file), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(db_file))

    first = _sample_estabelecimento("Padaria Teste")
    first_id = db_manager.upsert_estabelecimento(conn, first)
    db_manager.add_coleta_historico(
        conn,
        first_id,
        first["data_coleta"],
        first["nota_media"],
        first["total_avaliacoes"],
        first["score_oportunidade"],
    )

    second = _sample_estabelecimento("Clinica Teste")
    second["categoria"] = "Clinica"
    second["telefone"] = "16999991111"
    second_id = db_manager.upsert_estabelecimento(conn, second)
    conn.execute(
        "UPDATE estabelecimentos SET aprovado_disparo = 1 WHERE id = ?",
        (second_id,),
    )
    conn.execute(
        """
        INSERT INTO fila_disparos (
            estabelecimento_id, telefone, mensagem, status, tentativas, data_agendamento
        ) VALUES (?, ?, ?, 'pendente', 0, ?)
        """,
        (second_id, "5516999991111", "mensagem teste", "2026-04-09T09:00:00-03:00"),
    )
    conn.commit()
    conn.close()

    yield str(db_file)


def test_api_estabelecimentos(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/estabelecimentos")
    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["total"] == 2


def test_api_estabelecimentos_filtra_por_aprovacao(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/estabelecimentos?aprovado_disparo=approved")
    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["total"] == 1
    assert payload["data"][0]["aprovado_disparo"] == 1


def test_api_resumo(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/resumo")
    data = json.loads(resp.data)
    assert data["total"] == 2
    assert "aprovados" in data
    assert "enviados_hoje" in data


def test_api_aprovar(temp_db, monkeypatch):
    client = dashboard.app.test_client()
    monkeypatch.setattr(dashboard, "get_dispatch_scheduler", lambda: FakeScheduler())

    resp = client.post("/api/aprovar", json={"ids": [1]})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["updated"] == 1


def test_api_remover_aprovacao(temp_db):
    client = dashboard.app.test_client()
    resp = client.post("/api/remover-aprovacao", json={"ids": [2]})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["updated"] == 1


def test_api_fila_disparos(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/fila-disparos")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert len(payload["data"]) == 1
    assert payload["data"][0]["nome"] == "Clinica Teste"


def test_api_mensagens_elegiveis(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/mensagens/elegiveis?q=Clinica")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert len(payload["data"]) == 1
    assert payload["data"][0]["nome"] == "Clinica Teste"


def test_api_mensagens_config(temp_db):
    client = dashboard.app.test_client()

    get_resp = client.get("/api/mensagens/config")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["config"]["modo_envio"] == "manual"

    post_resp = client.post("/api/mensagens/config", json={"modo_envio": "automatico"})
    assert post_resp.status_code == 200
    assert post_resp.get_json()["config"]["modo_envio"] == "automatico"


def test_api_disparo_status(temp_db, monkeypatch):
    client = dashboard.app.test_client()
    fake = FakeScheduler()
    monkeypatch.setattr(dashboard, "get_dispatch_scheduler", lambda: fake)

    resp = client.get("/api/disparo/status")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["scheduler"]["paused"] is True


def test_api_disparo_enfileirar(temp_db, monkeypatch):
    client = dashboard.app.test_client()
    fake = FakeScheduler()
    monkeypatch.setattr(dashboard, "get_dispatch_scheduler", lambda: fake)

    resp = client.post("/api/disparo/enfileirar", json={"ids": [1, 2]})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["created"] == 2


def test_api_disparo_iniciar_e_pausar(temp_db, monkeypatch):
    client = dashboard.app.test_client()
    fake = FakeScheduler()
    monkeypatch.setattr(dashboard, "get_dispatch_scheduler", lambda: fake)

    start_resp = client.post("/api/disparo/iniciar")
    pause_resp = client.post("/api/disparo/pausar")

    assert start_resp.status_code == 200
    assert start_resp.get_json()["scheduler"]["running"] is True
    assert pause_resp.status_code == 200
    assert pause_resp.get_json()["scheduler"]["paused"] is True


def test_api_start_varredura(monkeypatch, temp_db):
    client = dashboard.app.test_client()

    def fake_start_scan_job(command, source=None):
        assert command == "restaurantes Franca SP"
        assert source == "google_maps"
        return {
            "id": "job-1",
            "command": command,
            "fonte": "google_maps",
            "status": "queued",
            "meta_minima": 30,
            "novos_encontrados": 0,
            "ignorados_existentes": 0,
            "paginas_percorridas": 0,
            "registros_inspecionados": 0,
            "mensagem": "Job criado.",
            "erro": None,
        }

    monkeypatch.setattr(dashboard, "start_scan_job", fake_start_scan_job)
    resp = client.post("/api/varreduras", json={"source": "google_maps", "command": "restaurantes Franca SP"})
    payload = resp.get_json()

    assert resp.status_code == 202
    assert payload["job"]["id"] == "job-1"
    assert payload["job"]["status"] == "queued"


def test_api_get_varredura_ativa(monkeypatch, temp_db):
    client = dashboard.app.test_client()

    monkeypatch.setattr(
        dashboard,
        "get_active_or_latest_job_snapshot",
        lambda: {
            "id": "job-2",
            "command": "apontador Franca SP bares-e-restaurantes/restaurantes",
            "fonte": "apontador",
            "status": "running",
            "meta_minima": 30,
            "novos_encontrados": 12,
            "ignorados_existentes": 4,
            "paginas_percorridas": 3,
            "registros_inspecionados": 18,
            "mensagem": "Executando.",
            "erro": None,
        },
    )

    resp = client.get("/api/varreduras/ativa")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["job"]["status"] == "running"
    assert payload["job"]["novos_encontrados"] == 12
