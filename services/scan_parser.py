import argparse
import shlex
from dataclasses import dataclass
from typing import List

from config import settings


class CommandParseError(ValueError):
    pass


@dataclass
class ScanRequest:
    fonte: str
    busca: str | None = None
    cidade: str | None = None
    estado: str | None = None
    categoria: str | None = None
    meta_minima: int = 30
    ignorar_existentes: bool = True
    comando_original: str = ""


def _normalize_source(source: str) -> str:
    normalized = (source or "").strip().lower().replace("-", "_")
    if normalized in {"google maps", "googlemaps"}:
        return "google_maps"
    return normalized


def _normalize_tokens(command: str) -> List[str]:
    try:
        return shlex.split(command)
    except ValueError as exc:
        raise CommandParseError(f"Comando invalido: {exc}") from exc


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fonte", choices=["apontador", "google_maps", "csv"])
    parser.add_argument("--cidade")
    parser.add_argument("--estado")
    parser.add_argument("--categoria")
    parser.add_argument("--busca")
    parser.add_argument("--arquivo")
    return parser


def _parse_cli_command(tokens: List[str], command: str) -> ScanRequest:
    working = list(tokens)
    if working and working[0].lower() in {"python", "python3", "py"}:
        working = working[1:]
    if working and working[0].lower().endswith("main.py"):
        working = working[1:]

    parser = _build_cli_parser()
    try:
        args, extras = parser.parse_known_args(working)
    except SystemExit as exc:
        raise CommandParseError("Nao foi possivel interpretar o comando informado.") from exc

    if extras:
        raise CommandParseError(f"Tokens nao reconhecidos no comando: {' '.join(extras)}")

    if args.fonte == "google_maps":
        if not args.busca:
            raise CommandParseError("Informe `--busca` para varreduras do Google Maps.")
        return ScanRequest(
            fonte="google_maps",
            busca=args.busca,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=command,
        )

    if args.fonte == "apontador":
        if not all([args.cidade, args.estado, args.categoria]):
            raise CommandParseError("Informe `--cidade`, `--estado` e `--categoria` para varreduras do Apontador.")
        return ScanRequest(
            fonte="apontador",
            cidade=args.cidade,
            estado=args.estado.upper(),
            categoria=args.categoria,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=command,
        )

    raise CommandParseError("Use `--fonte google_maps` ou `--fonte apontador` na caixa de comando.")


def _parse_shorthand(tokens: List[str], command: str) -> ScanRequest:
    if not tokens:
        raise CommandParseError("Digite um comando para iniciar a varredura.")

    first = tokens[0].lower().replace("-", "_")
    second = tokens[1].lower() if len(tokens) > 1 else ""

    if first in {"google_maps", "googlemaps"} or (first == "google" and second == "maps"):
        busca_tokens = tokens[2:] if first == "google" and second == "maps" else tokens[1:]
        busca = " ".join(busca_tokens).strip()
        if not busca:
            raise CommandParseError("Informe a busca apos `google_maps`.")
        return ScanRequest(
            fonte="google_maps",
            busca=busca,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=command,
        )

    if first == "apontador":
        rest = tokens[1:]
        if len(rest) < 3:
            raise CommandParseError("Use `apontador <cidade> <UF> <categoria>`.")
        categoria = rest[-1]
        estado = rest[-2].upper()
        cidade = " ".join(rest[:-2]).strip()
        if len(estado) != 2 or not cidade:
            raise CommandParseError("Use `apontador <cidade> <UF> <categoria>`.")
        return ScanRequest(
            fonte="apontador",
            cidade=cidade,
            estado=estado,
            categoria=categoria,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=command,
        )

    raise CommandParseError("Comando invalido. Comece com `google_maps`, `google maps` ou `apontador`.")


def parse_dashboard_scan_command(source: str, command: str) -> ScanRequest:
    normalized_source = _normalize_source(source)
    normalized_command = " ".join((command or "").split())
    if not normalized_command:
        raise CommandParseError("Digite o comando da varredura antes de executar.")

    if normalized_source == "google_maps":
        return ScanRequest(
            fonte="google_maps",
            busca=normalized_command,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=normalized_command,
        )

    if normalized_source == "apontador":
        tokens = _normalize_tokens(normalized_command)
        if len(tokens) < 3:
            raise CommandParseError("No Apontador, use `cidade UF categoria`.")
        categoria = tokens[-1]
        estado = tokens[-2].upper()
        cidade = " ".join(tokens[:-2]).strip()
        if len(estado) != 2 or not estado.isalpha() or not cidade:
            raise CommandParseError("No Apontador, use `cidade UF categoria`.")
        return ScanRequest(
            fonte="apontador",
            cidade=cidade,
            estado=estado,
            categoria=categoria,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=normalized_command,
        )

    raise CommandParseError("Selecione uma fonte valida para iniciar a varredura.")


def parse_scan_command(command: str) -> ScanRequest:
    normalized = " ".join((command or "").split())
    if not normalized:
        raise CommandParseError("Digite um comando para iniciar a varredura.")

    tokens = _normalize_tokens(normalized)
    if any(token.startswith("--") for token in tokens):
        return _parse_cli_command(tokens, normalized)
    return _parse_shorthand(tokens, normalized)
