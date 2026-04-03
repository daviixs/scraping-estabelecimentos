import json
from datetime import datetime, timezone

import pytest

from config import settings
from database import db_manager
import dashboard


@pytest.fixture(scope="function")
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "api.db"
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
