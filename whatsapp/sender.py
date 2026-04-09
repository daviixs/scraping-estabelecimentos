from dataclasses import dataclass
from typing import Any

try:
    import requests
except ImportError:
    class _RequestsFallback:
        class RequestException(Exception):
            pass

        class HTTPError(RequestException):
            pass

        @staticmethod
        def post(*args, **kwargs):
            raise RuntimeError("A biblioteca `requests` nao esta instalada.")

    requests = _RequestsFallback()

from config import settings
from .validator import sanitize_phone_number


class EvolutionSendError(RuntimeError):
    pass


@dataclass
class SendResult:
    normalized_number: str
    success: bool
    raw_response: Any = None


def _headers():
    return {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }


def send_text_message(number: str, text: str, session=None) -> SendResult:
    normalized = sanitize_phone_number(number)
    if len(normalized) < 12:
        raise EvolutionSendError("Numero invalido para envio.")

    client = session or requests
    url = f"{settings.EVOLUTION_BASE_URL}/message/sendText/{settings.EVOLUTION_INSTANCE}"

    try:
        response = client.post(
            url,
            headers=_headers(),
            json={"number": normalized, "text": text},
            timeout=settings.EVOLUTION_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise EvolutionSendError(f"Falha ao enviar mensagem pelo Evolution: {exc}") from exc

    return SendResult(
        normalized_number=normalized,
        success=True,
        raw_response=response.json(),
    )
