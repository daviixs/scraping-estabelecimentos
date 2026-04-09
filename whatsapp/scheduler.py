from __future__ import annotations

from datetime import datetime, timedelta
import threading
from typing import Dict, Optional

from config import settings
from database import db_manager

from .message_builder import gerar_mensagem
from .sender import EvolutionSendError, send_text_message
from .validator import EvolutionValidationError, validate_whatsapp_number

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    class BackgroundScheduler:  # type: ignore[override]
        def __init__(self, daemon: bool = True):
            self._daemon = daemon
            self._running = False
            self._thread = None
            self._event = threading.Event()
            self._job = None
            self._seconds = 0

        @property
        def running(self) -> bool:
            return self._running

        def add_job(self, func, trigger: str, seconds: int, id: str, replace_existing: bool = True, max_instances: int = 1, coalesce: bool = True):  # noqa: ARG002
            self._job = func
            self._seconds = seconds

        def start(self):
            if self._running:
                return
            self._running = True
            self._event.clear()

            def loop():
                while not self._event.wait(self._seconds):
                    if self._job:
                        self._job()

            self._thread = threading.Thread(target=loop, daemon=self._daemon)
            self._thread.start()

        def shutdown(self, wait: bool = False):
            self._event.set()
            self._running = False
            if wait and self._thread:
                self._thread.join(timeout=1)


def _now_local() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class WhatsAppDispatchScheduler:
    def __init__(self, heartbeat_seconds: Optional[int] = None):
        self._heartbeat_seconds = heartbeat_seconds or settings.WHATSAPP_HEARTBEAT_SEGUNDOS
        self._scheduler = BackgroundScheduler(daemon=True)
        self._state_lock = threading.Lock()
        self._process_lock = threading.Lock()
        self._background_started = False
        self._running = False
        self._paused = True
        self._next_run_at: Optional[str] = None
        self._last_error: Optional[str] = None

    def ensure_background_worker(self) -> None:
        with self._state_lock:
            if self._background_started:
                return
            self._scheduler.add_job(
                self.process_due_queue,
                "interval",
                seconds=self._heartbeat_seconds,
                id="whatsapp-dispatch-loop",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            self._scheduler.start()
            self._background_started = True

    def start(self) -> Dict:
        self.ensure_background_worker()
        with self._state_lock:
            self._running = True
            self._paused = False
            self._last_error = None
        self.process_due_queue()
        snapshot = self.get_status_snapshot()
        snapshot["enqueued"] = 0
        return snapshot

    def pause(self) -> Dict:
        with self._state_lock:
            self._running = False
            self._paused = True
        return self.get_status_snapshot()

    def sync_pending_queue(self) -> int:
        db_manager.init_db()
        now = _now_local()
        with db_manager.get_connection() as conn:
            leads = db_manager.list_estabelecimentos_para_disparo(conn)
            if not leads:
                return 0

            last_scheduled = _parse_iso(db_manager.get_last_pending_schedule(conn))
            candidate = now
            if last_scheduled:
                candidate = max(candidate, last_scheduled + timedelta(seconds=settings.INTERVALO_ENTRE_ENVIOS))

            return self._enqueue_leads(conn, leads, candidate=candidate, source="manual")

    def enqueue_estabelecimentos(
        self,
        ids: list[int],
        *,
        source: str = "manual",
        approve: bool = True,
    ) -> int:
        clean_ids = [int(item) for item in ids if item is not None]
        if not clean_ids:
            return 0

        db_manager.init_db()
        now = _now_local()
        with db_manager.get_connection() as conn:
            if approve:
                db_manager.update_aprovacao_lote(conn, clean_ids, aprovado=True)

            leads = db_manager.list_estabelecimentos_para_fila_por_ids(conn, clean_ids)
            if not leads:
                return 0

            last_scheduled = _parse_iso(db_manager.get_last_pending_schedule(conn))
            candidate = now
            if last_scheduled:
                candidate = max(candidate, last_scheduled + timedelta(seconds=settings.INTERVALO_ENTRE_ENVIOS))

            return self._enqueue_leads(conn, leads, candidate=candidate, source=source)

    def process_due_queue(self) -> Dict:
        if not self._process_lock.acquire(blocking=False):
            return self.get_status_snapshot()

        try:
            with self._state_lock:
                running = self._running

            if not running:
                return self.get_status_snapshot()

            now = _now_local()
            self.sync_pending_queue()

            if not self._is_inside_business_window(now):
                self._set_next_run(self._align_to_business_window(now))
                return self.get_status_snapshot()

            with db_manager.get_connection() as conn:
                sent_today = db_manager.count_sent_on_date(conn, now.date().isoformat())
                if sent_today >= settings.LIMITE_DIARIO_ENVIOS:
                    self._set_next_run(self._next_business_day_start(now))
                    return self.get_status_snapshot()

                due_item = db_manager.get_next_due_queue_item(conn, _to_iso(now))
                if not due_item:
                    next_schedule = _parse_iso(db_manager.get_next_pending_schedule(conn))
                    self._set_next_run(next_schedule)
                    return self.get_status_snapshot()

                queue_id = int(due_item["id"])
                estabelecimento_id = int(due_item["estabelecimento_id"])
                telefone = str(due_item.get("telefone") or "")
                mensagem = str(due_item.get("mensagem") or "")

                validation = validate_whatsapp_number(telefone)
                if not validation.exists:
                    db_manager.mark_queue_item_sem_whatsapp(
                        conn,
                        queue_id=queue_id,
                        estabelecimento_id=estabelecimento_id,
                        error_text="Numero sem WhatsApp na validacao.",
                    )
                    self._last_error = None
                    next_schedule = _parse_iso(db_manager.get_next_pending_schedule(conn))
                    self._set_next_run(next_schedule)
                    return self.get_status_snapshot()

                try:
                    send_text_message(validation.normalized_number, mensagem)
                except EvolutionSendError as exc:
                    tentativas = int(due_item.get("tentativas") or 0) + 1
                    if tentativas >= settings.MAX_TENTATIVAS:
                        db_manager.mark_queue_item_error(
                            conn,
                            queue_id=queue_id,
                            estabelecimento_id=estabelecimento_id,
                            tentativas=tentativas,
                            error_text=str(exc),
                        )
                    else:
                        retry_slot = self._reserve_retry_slot(conn, now + timedelta(seconds=settings.INTERVALO_ENTRE_ENVIOS))
                        db_manager.mark_queue_item_retry(
                            conn,
                            queue_id=queue_id,
                            tentativas=tentativas,
                            error_text=str(exc),
                            next_schedule_at=_to_iso(retry_slot),
                        )
                    self._last_error = str(exc)
                    next_schedule = _parse_iso(db_manager.get_next_pending_schedule(conn))
                    self._set_next_run(next_schedule)
                    return self.get_status_snapshot()

                db_manager.mark_queue_item_sent(
                    conn,
                    queue_id=queue_id,
                    estabelecimento_id=estabelecimento_id,
                    sent_at=_to_iso(now),
                )
                self._last_error = None
                next_schedule = _parse_iso(db_manager.get_next_pending_schedule(conn))
                self._set_next_run(next_schedule)
                return self.get_status_snapshot()
        except EvolutionValidationError as exc:
            self._last_error = str(exc)
            self._set_next_run(_now_local() + timedelta(seconds=self._heartbeat_seconds))
            return self.get_status_snapshot()
        finally:
            self._process_lock.release()

    def get_status_snapshot(self) -> Dict:
        db_manager.init_db()
        with db_manager.get_connection() as conn:
            sent_today = db_manager.count_sent_on_date(conn, _now_local().date().isoformat())
            pending_items = db_manager.get_pending_queue_count(conn)

        with self._state_lock:
            return {
                "running": self._running,
                "paused": self._paused,
                "next_run_at": self._next_run_at,
                "sent_today": sent_today,
                "pending_items": pending_items,
                "daily_limit": settings.LIMITE_DIARIO_ENVIOS,
                "window_label": f"{settings.JANELA_INICIO_HORA:02d}:00-{settings.JANELA_FIM_HORA:02d}:00 dias uteis",
                "heartbeat_seconds": self._heartbeat_seconds,
                "last_error": self._last_error,
            }

    def shutdown(self) -> None:
        if self._background_started and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        with self._state_lock:
            self._background_started = False
            self._running = False
            self._paused = True
            self._next_run_at = None
            self._last_error = None

    def _enqueue_leads(self, conn, leads: list[Dict], *, candidate: datetime, source: str) -> int:
        created = 0
        day_counts: Dict[str, int] = {}
        normalized_source = "automatico" if source == "automatico" else "manual"
        for lead in leads:
            slot = self._reserve_next_slot(conn, candidate, day_counts)
            db_manager.create_queue_item(
                conn,
                estabelecimento_id=int(lead["id"]),
                telefone=str(lead.get("telefone") or ""),
                mensagem=gerar_mensagem(lead.get("nome") or "", lead.get("categoria") or ""),
                data_agendamento=_to_iso(slot),
                origem_disparo=normalized_source,
            )
            candidate = slot + timedelta(seconds=settings.INTERVALO_ENTRE_ENVIOS)
            created += 1
        return created

    def _set_next_run(self, next_run: Optional[datetime]) -> None:
        with self._state_lock:
            self._next_run_at = _to_iso(next_run) if next_run else None

    def _reserve_retry_slot(self, conn, candidate: datetime) -> datetime:
        last_schedule = _parse_iso(db_manager.get_last_pending_schedule(conn))
        base_candidate = candidate
        if last_schedule:
            base_candidate = max(
                base_candidate,
                last_schedule + timedelta(seconds=settings.INTERVALO_ENTRE_ENVIOS),
            )
        return self._reserve_next_slot(conn, base_candidate, {})

    def _reserve_next_slot(self, conn, candidate: datetime, day_counts: Dict[str, int]) -> datetime:
        slot = self._align_to_business_window(candidate)
        while True:
            date_key = slot.date().isoformat()
            if date_key not in day_counts:
                day_counts[date_key] = (
                    db_manager.count_sent_on_date(conn, date_key)
                    + db_manager.count_pending_scheduled_on_date(conn, date_key)
                )
            if day_counts[date_key] < settings.LIMITE_DIARIO_ENVIOS:
                day_counts[date_key] += 1
                return slot
            slot = self._next_business_day_start(slot)

    @staticmethod
    def _is_inside_business_window(candidate: datetime) -> bool:
        if candidate.weekday() >= 5:
            return False
        start_hour = settings.JANELA_INICIO_HORA
        end_hour = settings.JANELA_FIM_HORA
        return start_hour <= candidate.hour < end_hour

    def _align_to_business_window(self, candidate: datetime) -> datetime:
        normalized = candidate.replace(microsecond=0)
        if normalized.weekday() >= 5:
            return self._next_business_day_start(normalized)

        start = normalized.replace(
            hour=settings.JANELA_INICIO_HORA,
            minute=0,
            second=0,
            microsecond=0,
        )
        end = normalized.replace(
            hour=settings.JANELA_FIM_HORA,
            minute=0,
            second=0,
            microsecond=0,
        )

        if normalized < start:
            return start
        if normalized >= end:
            return self._next_business_day_start(normalized)
        return normalized

    def _next_business_day_start(self, candidate: datetime) -> datetime:
        next_day = candidate + timedelta(days=1)
        next_day = next_day.replace(
            hour=settings.JANELA_INICIO_HORA,
            minute=0,
            second=0,
            microsecond=0,
        )
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
            next_day = next_day.replace(
                hour=settings.JANELA_INICIO_HORA,
                minute=0,
                second=0,
                microsecond=0,
            )
        return next_day


_dispatch_scheduler: Optional[WhatsAppDispatchScheduler] = None


def get_dispatch_scheduler() -> WhatsAppDispatchScheduler:
    global _dispatch_scheduler
    if _dispatch_scheduler is None:
        _dispatch_scheduler = WhatsAppDispatchScheduler()
    return _dispatch_scheduler
