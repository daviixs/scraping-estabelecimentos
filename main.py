import argparse
from datetime import datetime

from config import settings
from database import db_manager, history
from output import csv_exporter, excel_exporter
from processor import nlp_comments, normalizer, scorer
from scraper import apontador, csv_importer, google_maps
import dashboard


def process_registros(registros):
    db_manager.init_db()
    data_coleta = datetime.utcnow().isoformat()
    inseridos = 0
    with db_manager.get_connection() as conn:
        for reg in registros:
            reg["data_coleta"] = reg.get("data_coleta") or data_coleta
            reg_norm = normalizer.normalize_estabelecimento(reg)

            comentarios = reg.get("comentarios", []) or []
            # considera últimos 10 negativos (<=3 estrelas) se existirem, senão últimos 10
            negativos = [c for c in comentarios if c.get("estrelas") is not None and c.get("estrelas") <= 3]
            analisados = (negativos or comentarios)[:10]
            textos_negativos = [c.get("texto", "") for c in analisados]
            counts = nlp_comments.contar_queixas(textos_negativos)
            resumo = nlp_comments.resumo_queixas(counts)
            queixas_ratio = nlp_comments.proporcao_queixas(counts, len(analisados))

            # detecta queda
            estab_id_temp = None
            queda = False
            try:
                estab_id_temp = conn.execute(
                    "SELECT id FROM estabelecimentos WHERE nome=? AND cidade=?",
                    (reg_norm["nome"], reg_norm["cidade"]),
                ).fetchone()
                estab_id_temp = estab_id_temp["id"] if estab_id_temp else None
                if estab_id_temp:
                    queda = history.detect_queda(conn, estab_id_temp, reg_norm.get("nota_media"))
            except Exception:
                queda = False

            score = scorer.calcular_score(
                nota_media=reg_norm.get("nota_media") or 0,
                total_avaliacoes=reg_norm.get("total_avaliacoes") or 0,
                queixas_ratio=queixas_ratio,
                queda=queda,
                sem_reply=not bool(reg.get("dono_responde")),
            )
            prioridade = scorer.prioridade_por_score(score)

            reg_norm.update(
                {
                    "data_coleta": reg["data_coleta"],
                    "dono_responde": reg.get("dono_responde", 0),
                    "score_oportunidade": score,
                    "prioridade_lead": prioridade,
                    "resumo_queixas": resumo,
                }
            )

            estab_id = db_manager.upsert_estabelecimento(conn, reg_norm)
            db_manager.add_coleta_historico(
                conn,
                estab_id,
                reg_norm["data_coleta"],
                reg_norm.get("nota_media"),
                reg_norm.get("total_avaliacoes", 0),
                score,
            )
            db_manager.add_comentarios(conn, estab_id, comentarios, reg["data_coleta"])
            db_manager.add_queixas(conn, estab_id, counts, reg["data_coleta"])
            inseridos += 1
    return inseridos


def run_apontador(args):
    registros = apontador.scrape_apontador(args.cidade, args.estado, args.categoria)
    return process_registros(registros)


def run_google(args):
    registros = google_maps.scrape_google_maps(args.busca)
    return process_registros(registros)


def run_csv(args):
    registros = csv_importer.import_from_csv(args.arquivo)
    return process_registros(registros)


def main():
    parser = argparse.ArgumentParser(description="Bot de Inteligência Comercial")
    parser.add_argument("--fonte", choices=["apontador", "google_maps", "csv"], help="Fonte de coleta")
    parser.add_argument("--cidade", help="Cidade (apontador)")
    parser.add_argument("--estado", help="Estado (apontador)")
    parser.add_argument("--categoria", help="Categoria (apontador)")
    parser.add_argument("--busca", help="Termo de busca (google_maps)")
    parser.add_argument("--arquivo", help="Arquivo CSV (csv)")
    parser.add_argument("--dashboard", action="store_true", help="Inicia apenas a dashboard")
    args = parser.parse_args()

    if args.dashboard:
        dashboard.run_server(open_browser=True)
        return

    if args.fonte == "apontador":
        if not all([args.cidade, args.estado, args.categoria]):
            parser.error("--cidade, --estado e --categoria são obrigatórios para Apontador")
        inseridos = run_apontador(args)
        print(f"Inseridos/atualizados: {inseridos}")
    elif args.fonte == "google_maps":
        if not args.busca:
            parser.error("--busca é obrigatório para Google Maps")
        inseridos = run_google(args)
        print(f"Inseridos/atualizados: {inseridos}")
    elif args.fonte == "csv":
        if not args.arquivo:
            parser.error("--arquivo é obrigatório para CSV")
        inseridos = run_csv(args)
        print(f"Inseridos/atualizados: {inseridos}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
