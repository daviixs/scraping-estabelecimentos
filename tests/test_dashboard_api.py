import json
from datetime import datetime, timezone

import pytest

from config import settings
from database import db_manager
import dashboard


@pytest.fixture(scope="function")
def temp_db(temp_db_path, monkeypatch):
    db_file = temp_db_path
    monkeypatch.setattr(settings, "DATABASE_PATH", str(db_file))
    db_manager.init_db(db_path=str(db_file), schema_path="database/schema.sql")
    conn = db_manager.get_connection(str(db_file))
    data = {
        "nome": "Padaria Teste",
        "categoria": "Padaria",
        "cidade": "Franca",
        "bairro": "Centro",
        "telefone": "123",
        "site": None,
        "nota_media": 4.4,
        "total_avaliacoes": 120,
        "link_origem": "http://origem",
        "fonte": "apontador",
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "dono_responde": 0,
        "score_oportunidade": 55.0,
        "faixa_classificacao": "MUITO RUIM",
        "prioridade_lead": "MÉDIA",
        "resumo_queixas": "atendimento (2)",
    }
    estab_id = db_manager.upsert_estabelecimento(conn, data)
    db_manager.add_coleta_historico(
        conn, estab_id, data["data_coleta"], data["nota_media"], data["total_avaliacoes"], data["score_oportunidade"]
    )
    conn.close()
    yield str(db_file)


def test_api_estabelecimentos(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/estabelecimentos")
    assert resp.status_code == 200
    payload = json.loads(resp.data)
    assert payload["total"] == 1
    assert payload["data"][0]["nome"] == "Padaria Teste"


def test_api_resumo(temp_db):
    client = dashboard.app.test_client()
    resp = client.get("/api/resumo")
    data = json.loads(resp.data)
    assert data["total"] == 1


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
