import os
import webbrowser
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, request, send_file

from config import settings
from database import db_manager
from output import csv_exporter, excel_exporter

app = Flask(
    __name__,
    static_folder="frontend/dist",
    static_url_path="/",
    template_folder="templates",
)


def ensure_db():
    if not Path(settings.DATABASE_PATH).exists():
        db_manager.init_db()


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
    if args.get("score_min") is not None:
        try:
            filters["score_min"] = float(args.get("score_min"))
        except ValueError:
            filters["score_min"] = None
    return filters


@app.route("/")
def index():
    # serve Astro build se existir, senão fallback para templates/index.html
    dist_index = Path(app.static_folder) / "index.html"
    if dist_index.exists():
        return send_file(dist_index)
    return send_file(Path(app.template_folder) / "index.html")


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
