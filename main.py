import argparse
import sys


def ensure_supported_python():
    if sys.version_info < (3, 10):
        raise SystemExit("Este projeto requer Python 3.10 ou superior.")
    if sys.version_info >= (3, 14):
        raise SystemExit(
            "Python 3.14 nao e compativel com as dependencias atuais do projeto. "
            "Crie uma .venv com Python 3.12 e rode `.venv/bin/python main.py --dashboard`."
        )


ensure_supported_python()

from scraper import csv_importer
from services import build_scan_request_from_args, execute_scan_request, process_registros
import dashboard


def run_apontador(args):
    return execute_scan_request(build_scan_request_from_args(args))


def run_google(args):
    return execute_scan_request(build_scan_request_from_args(args))


def run_csv(args):
    registros = csv_importer.import_from_csv(args.arquivo)
    return process_registros(registros)["novos_encontrados"]


def _print_scan_result(resultado):
    print(
        f"Novos inseridos: {resultado['novos_encontrados']} | "
        f"Ignorados existentes: {resultado['ignorados_existentes']} | "
        f"Paginas percorridas: {resultado['paginas_percorridas']} | "
        f"Status: {resultado['status']}"
    )


def main():
    parser = argparse.ArgumentParser(description="Bot de Inteligencia Comercial")
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
            parser.error("--cidade, --estado e --categoria sao obrigatorios para Apontador")
        _print_scan_result(run_apontador(args))
    elif args.fonte == "google_maps":
        if not args.busca:
            parser.error("--busca e obrigatorio para Google Maps")
        _print_scan_result(run_google(args))
    elif args.fonte == "csv":
        if not args.arquivo:
            parser.error("--arquivo e obrigatorio para CSV")
        inseridos = run_csv(args)
        print(f"Novos inseridos: {inseridos}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
