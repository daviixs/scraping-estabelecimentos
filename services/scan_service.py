from __future__ import annotations

import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from config import settings
from database import db_manager, history
from processor import nlp_comments, normalizer, scorer
from scraper import apontador, google_maps

from .scan_parser import CommandParseError, ScanRequest, parse_scan_command


ProgressCallback = Callable[..., None]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScanJob:
    id: str
    command: str
    fonte: str
    status: str = "queued"
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    meta_minima: int = 30
    novos_encontrados: int = 0
    ignorados_existentes: int = 0
    paginas_percorridas: int = 0
    registros_inspecionados: int = 0
    mensagem: str = ""
    erro: Optional[str] = None


class ActiveScanError(RuntimeError):
    def __init__(self, snapshot: Dict[str, Any]):
        super().__init__("Ja existe uma varredura em andamento.")
        self.snapshot = snapshot


_jobs: Dict[str, ScanJob] = {}
_jobs_lock = threading.Lock()
_active_job_id: Optional[str] = None
_latest_job_id: Optional[str] = None


def get_scan_examples() -> list[str]:
    return [
        "google_maps restaurantes Franca SP",
        "apontador Franca SP bares-e-restaurantes/restaurantes",
        'python main.py --fonte google_maps --busca "restaurantes Franca SP"',
    ]


def build_scan_request_from_args(args) -> ScanRequest:
    if args.fonte == "google_maps":
        return ScanRequest(
            fonte="google_maps",
            busca=args.busca,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=f"google_maps {args.busca}",
        )
    if args.fonte == "apontador":
        return ScanRequest(
            fonte="apontador",
            cidade=args.cidade,
            estado=(args.estado or "").upper(),
            categoria=args.categoria,
            meta_minima=settings.VARREDURA_MINIMA_ESTABELECIMENTOS,
            ignorar_existentes=True,
            comando_original=f"apontador {args.cidade} {(args.estado or '').upper()} {args.categoria}",
        )
    raise ValueError(f"Fonte de varredura nao suportada: {args.fonte}")


def _notify(progress_cb: Optional[ProgressCallback], **kwargs) -> None:
    if progress_cb:
        progress_cb(**kwargs)


def process_registros(
    registros,
    *,
    ignore_existing: bool = False,
    progress_cb: Optional[ProgressCallback] = None,
) -> Dict[str, int]:
    db_manager.init_db()
    data_coleta = _utc_now_iso()
    stats = {
        "novos_encontrados": 0,
        "ignorados_existentes": 0,
        "registros_processados": 0,
    }

    with db_manager.get_connection() as conn:
        for reg in registros:
            stats["registros_processados"] += 1
            reg["data_coleta"] = reg.get("data_coleta") or data_coleta
            reg_norm = normalizer.normalize_estabelecimento(reg)

            if ignore_existing and db_manager.estabelecimento_exists(conn, reg_norm["nome"], reg_norm["cidade"]):
                stats["ignorados_existentes"] += 1
                _notify(progress_cb, ignorados_existentes=1)
                continue

            comentarios = reg.get("comentarios", []) or []
            negativos = [c for c in comentarios if c.get("estrelas") is not None and c.get("estrelas") <= 3]
            analisados = (negativos or comentarios)[:10]
            textos_negativos = [c.get("texto", "") for c in analisados]
            counts = nlp_comments.contar_queixas(textos_negativos)
            resumo = nlp_comments.resumo_queixas(counts)
            queixas_ratio = nlp_comments.proporcao_queixas(counts, len(analisados))

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
            stats["novos_encontrados"] += 1
            _notify(progress_cb, novos_encontrados=stats["novos_encontrados"])

    return stats


def execute_scan_request(
    scan_request: ScanRequest,
    *,
    progress_cb: Optional[ProgressCallback] = None,
) -> Dict[str, Any]:
    db_manager.init_db()
    summary: Dict[str, Any] = {
        "status": "running",
        "fonte": scan_request.fonte,
        "meta_minima": scan_request.meta_minima,
        "novos_encontrados": 0,
        "ignorados_existentes": 0,
        "paginas_percorridas": 0,
        "registros_inspecionados": 0,
        "mensagem": "Preparando varredura...",
    }

    def on_scrape_progress(**kwargs) -> None:
        if "paginas_percorridas" in kwargs:
            summary["paginas_percorridas"] = max(
                summary["paginas_percorridas"],
                int(kwargs["paginas_percorridas"]),
            )
        if "registros_inspecionados" in kwargs:
            summary["registros_inspecionados"] += int(kwargs["registros_inspecionados"])
        if "ignorados_existentes" in kwargs:
            summary["ignorados_existentes"] += int(kwargs["ignorados_existentes"])
        if "novos_encontrados" in kwargs:
            summary["novos_encontrados"] = int(kwargs["novos_encontrados"])
        if "mensagem" in kwargs:
            summary["mensagem"] = kwargs["mensagem"]
        _notify(progress_cb, **summary)

    with db_manager.get_connection() as lookup_conn:
        def should_skip(candidate: Dict[str, Any]) -> bool:
            return db_manager.estabelecimento_exists(
                lookup_conn,
                candidate.get("nome"),
                candidate.get("cidade"),
            )

        if scan_request.fonte == "google_maps":
            registros = google_maps.scrape_google_maps(
                scan_request.busca or "",
                target_count=scan_request.meta_minima,
                should_skip=should_skip if scan_request.ignorar_existentes else None,
                progress_cb=on_scrape_progress,
            )
        elif scan_request.fonte == "apontador":
            registros = apontador.scrape_apontador(
                scan_request.cidade or "",
                scan_request.estado or "",
                scan_request.categoria or "",
                target_count=scan_request.meta_minima,
                should_skip=should_skip if scan_request.ignorar_existentes else None,
                progress_cb=on_scrape_progress,
            )
        else:
            raise ValueError(f"Fonte de varredura nao suportada: {scan_request.fonte}")

    persisted = process_registros(
        registros,
        ignore_existing=scan_request.ignorar_existentes,
    )
    summary["novos_encontrados"] = persisted["novos_encontrados"]
    summary["ignorados_existentes"] += persisted["ignorados_existentes"]
    if summary["novos_encontrados"] >= scan_request.meta_minima:
        summary["status"] = "completed"
        summary["mensagem"] = f"Meta atingida com {summary['novos_encontrados']} novos estabelecimentos."
    else:
        summary["status"] = "partial"
        summary["mensagem"] = (
            f"Busca encerrada com {summary['novos_encontrados']} novos estabelecimentos "
            f"de {scan_request.meta_minima} desejados."
        )
    _notify(progress_cb, **summary)
    return summary


def _snapshot(job: ScanJob) -> Dict[str, Any]:
    return asdict(job)


def _update_job(job_id: str, **fields) -> Dict[str, Any]:
    with _jobs_lock:
        job = _jobs[job_id]
        for key, value in fields.items():
            if hasattr(job, key) and value is not None:
                setattr(job, key, value)
        job.updated_at = _utc_now_iso()
        return _snapshot(job)


def _run_scan_job(job_id: str, scan_request: ScanRequest) -> None:
    _update_job(
        job_id,
        status="running",
        started_at=_utc_now_iso(),
        mensagem="Iniciando varredura...",
    )
    try:
        result = execute_scan_request(
            scan_request,
            progress_cb=lambda **kwargs: _update_job(job_id, **kwargs),
        )
        _update_job(
            job_id,
            status=result["status"],
            finished_at=_utc_now_iso(),
            meta_minima=result["meta_minima"],
            novos_encontrados=result["novos_encontrados"],
            ignorados_existentes=result["ignorados_existentes"],
            paginas_percorridas=result["paginas_percorridas"],
            registros_inspecionados=result["registros_inspecionados"],
            mensagem=result["mensagem"],
        )
    except Exception as exc:
        _update_job(
            job_id,
            status="error",
            finished_at=_utc_now_iso(),
            erro=str(exc),
            mensagem="Falha ao executar a varredura.",
        )
        traceback.print_exc()
    finally:
        global _active_job_id
        with _jobs_lock:
            if _active_job_id == job_id:
                _active_job_id = None


def start_scan_job(command: str) -> Dict[str, Any]:
    scan_request = parse_scan_command(command)
    global _active_job_id, _latest_job_id
    with _jobs_lock:
        if _active_job_id is not None:
            active = _jobs.get(_active_job_id)
            if active and active.status in {"queued", "running"}:
                raise ActiveScanError(_snapshot(active))

        job_id = uuid.uuid4().hex
        job = ScanJob(
            id=job_id,
            command=command,
            fonte=scan_request.fonte,
            meta_minima=scan_request.meta_minima,
            mensagem="Job criado e aguardando execucao.",
        )
        _jobs[job_id] = job
        _active_job_id = job_id
        _latest_job_id = job_id

    thread = threading.Thread(
        target=_run_scan_job,
        args=(job_id, scan_request),
        daemon=True,
        name=f"scan-job-{job_id[:8]}",
    )
    thread.start()
    return get_job_snapshot(job_id)


def get_job_snapshot(job_id: str) -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return _snapshot(job) if job else None


def get_active_or_latest_job_snapshot() -> Optional[Dict[str, Any]]:
    with _jobs_lock:
        if _active_job_id and _active_job_id in _jobs:
            return _snapshot(_jobs[_active_job_id])
        if _latest_job_id and _latest_job_id in _jobs:
            return _snapshot(_jobs[_latest_job_id])
        return None
