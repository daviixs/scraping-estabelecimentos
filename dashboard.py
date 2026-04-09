import webbrowser
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, request, send_file

from config import settings
from database import db_manager
from output import csv_exporter, excel_exporter
from services import (
    ActiveScanError,
    CommandParseError,
    get_active_or_latest_job_snapshot,
    get_job_snapshot,
    get_scan_examples,
    start_scan_job,
)
from whatsapp import get_dispatch_scheduler

app = Flask(
    __name__,
    static_folder="frontend/dist",
    static_url_path="/",
)


def ensure_db() -> None:
    db_manager.init_db()


def _parse_status_filter(raw_value: str) -> List[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def parse_filters(args) -> Dict:
    filters = {}
    if args.get("classificacao"):
        filters["classificacao"] = args.get("classificacao").split(",")
    if args.get("prioridade"):
        filters["prioridade"] = args.get("prioridade").split(",")
    if args.get("fonte"):
        filters["fonte"] = args.get("fonte").split(",")
    if args.get("cidade"):
        filters["cidade"] = args.get("cidade")
    if args.get("categoria"):
        filters["categoria"] = args.get("categoria")
    if args.get("status_whatsapp"):
        filters["status_whatsapp"] = _parse_status_filter(args.get("status_whatsapp"))
    if args.get("aprovado_disparo"):
        filters["aprovado_disparo"] = args.get("aprovado_disparo")
    if args.get("score_min") is not None:
        try:
            filters["score_min"] = float(args.get("score_min"))
        except ValueError:
            filters["score_min"] = None
    return filters


def _parse_ids(payload) -> List[int]:
    raw_ids = payload.get("ids")
    if not isinstance(raw_ids, list):
        return []
    parsed: List[int] = []
    for item in raw_ids:
        try:
            parsed.append(int(item))
        except (TypeError, ValueError):
            continue
    return parsed


def _parse_limit(raw_value: str, default: int = 60) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, 200))


@app.route("/")
def index():
    dist_index = Path(app.static_folder) / "index.html"
    if not dist_index.exists():
        return (
            "Frontend build nao encontrado. Rode `npm install` e `npm run build` em `frontend/`.",
            503,
        )
    return send_file(dist_index)


@app.route("/api/estabelecimentos")
def api_estabelecimentos():
    ensure_db()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", settings.REGISTROS_POR_PAGINA))
    order_by = request.args.get("order_by", "score_oportunidade")
    order_dir = request.args.get("order_dir", "desc")
    filters = parse_filters(request.args)
    with db_manager.get_connection() as conn:
        resultado = db_manager.query_estabelecimentos(
            conn=conn,
            filters=filters,
            page=page,
            per_page=per_page,
            order_by=order_by,
            order_dir=order_dir,
        )
    return jsonify(resultado)


@app.route("/api/resumo")
def api_resumo():
    ensure_db()
    with db_manager.get_connection() as conn:
        resumo = db_manager.get_resumo(conn)
    return jsonify(resumo)


@app.route("/api/cidades")
def api_cidades():
    ensure_db()
    with db_manager.get_connection() as conn:
        cidades = db_manager.list_cidades(conn)
    return jsonify(cidades)


@app.route("/api/categorias")
def api_categorias():
    ensure_db()
    with db_manager.get_connection() as conn:
        categorias = db_manager.list_categorias(conn)
    return jsonify(categorias)


@app.route("/api/aprovar", methods=["POST"])
def api_aprovar():
    ensure_db()
    payload = request.get_json(silent=True) or {}
    ids = _parse_ids(payload)
    if not ids:
        return jsonify({"error": "Informe uma lista de IDs para aprovar."}), 400

    with db_manager.get_connection() as conn:
        updated = db_manager.update_aprovacao_lote(conn, ids, aprovado=True)
    return jsonify({"updated": updated})


@app.route("/api/remover-aprovacao", methods=["POST"])
def api_remover_aprovacao():
    ensure_db()
    payload = request.get_json(silent=True) or {}
    ids = _parse_ids(payload)
    if not ids:
        return jsonify({"error": "Informe uma lista de IDs para remover aprovacao."}), 400

    with db_manager.get_connection() as conn:
        updated = db_manager.update_aprovacao_lote(conn, ids, aprovado=False)
    return jsonify({"updated": updated})


@app.route("/api/fila-disparos")
def api_fila_disparos():
    ensure_db()
    with db_manager.get_connection() as conn:
        fila = db_manager.list_fila_disparos(conn)
    return jsonify({"data": fila})


@app.route("/api/mensagens/elegiveis")
def api_mensagens_elegiveis():
    ensure_db()
    search = request.args.get("q", "")
    limit = _parse_limit(request.args.get("limit"), default=60)
    with db_manager.get_connection() as conn:
        registros = db_manager.list_estabelecimentos_mensagens(conn, search=search, limit=limit)
    return jsonify({"data": registros})


@app.route("/api/mensagens/config")
def api_mensagens_config():
    ensure_db()
    with db_manager.get_connection() as conn:
        config = db_manager.get_operational_config(conn)
    return jsonify({"config": config})


@app.route("/api/mensagens/config", methods=["POST"])
def api_mensagens_config_update():
    ensure_db()
    payload = request.get_json(silent=True) or {}
    modo_envio = str(payload.get("modo_envio") or "").strip().lower()
    if modo_envio not in {"manual", "automatico"}:
        return jsonify({"error": "Informe `manual` ou `automatico` para o modo de envio."}), 400

    with db_manager.get_connection() as conn:
        config = db_manager.update_operational_mode(conn, modo_envio)
    return jsonify({"config": config})


@app.route("/api/disparo/status")
def api_disparo_status():
    ensure_db()
    scheduler = get_dispatch_scheduler()
    return jsonify({"scheduler": scheduler.get_status_snapshot()})


@app.route("/api/disparo/enfileirar", methods=["POST"])
def api_disparo_enfileirar():
    ensure_db()
    payload = request.get_json(silent=True) or {}
    ids = _parse_ids(payload)
    if not ids:
        return jsonify({"error": "Informe uma lista de IDs para adicionar a fila."}), 400

    scheduler = get_dispatch_scheduler()
    created = scheduler.enqueue_estabelecimentos(ids, source="manual", approve=True)
    return jsonify({"created": created, "scheduler": scheduler.get_status_snapshot()})


@app.route("/api/disparo/iniciar", methods=["POST"])
def api_disparo_iniciar():
    ensure_db()
    scheduler = get_dispatch_scheduler()
    snapshot = scheduler.start()
    return jsonify({"scheduler": snapshot})


@app.route("/api/disparo/pausar", methods=["POST"])
def api_disparo_pausar():
    ensure_db()
    scheduler = get_dispatch_scheduler()
    snapshot = scheduler.pause()
    return jsonify({"scheduler": snapshot})


@app.route("/api/varreduras", methods=["POST"])
def api_start_varredura():
    payload = request.get_json(silent=True) or {}
    source = str(payload.get("source") or "").strip() or None
    command = str(payload.get("command") or "").strip()
    if not command:
        return jsonify({"error": "Digite um comando para iniciar a varredura.", "examples": get_scan_examples(source)}), 400
    try:
        job = start_scan_job(command, source=source)
        return jsonify({"job": job}), 202
    except CommandParseError as exc:
        return jsonify({"error": str(exc), "examples": get_scan_examples(source)}), 400
    except ActiveScanError as exc:
        return jsonify({"error": str(exc), "job": exc.snapshot}), 409


@app.route("/api/varreduras/<job_id>")
def api_get_varredura(job_id: str):
    job = get_job_snapshot(job_id)
    if not job:
        return jsonify({"error": "Varredura nao encontrada."}), 404
    return jsonify({"job": job})


@app.route("/api/varreduras/ativa")
def api_get_varredura_ativa():
    return jsonify({"job": get_active_or_latest_job_snapshot()})


def _collect_and_export(fmt: str):
    ensure_db()
    filters = parse_filters(request.args)
    with db_manager.get_connection() as conn:
        registros = db_manager.fetch_for_export(conn, filters)
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    if fmt == "csv":
        filepath = out_dir / "export.csv"
        csv_exporter.export_csv(registros, filepath)
    else:
        filepath = out_dir / "export.xlsx"
        excel_exporter.export_excel(registros, filepath)
    return send_file(filepath, as_attachment=True)


@app.route("/api/export/csv")
def api_export_csv():
    return _collect_and_export("csv")


@app.route("/api/export/xlsx")
def api_export_xlsx():
    return _collect_and_export("xlsx")


def run_server(open_browser: bool = True):
    ensure_db()
    if open_browser:
        webbrowser.open(f"http://{settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}")
    app.run(host=settings.DASHBOARD_HOST, port=settings.DASHBOARD_PORT, debug=False)


if __name__ == "__main__":
    run_server(open_browser=True)
