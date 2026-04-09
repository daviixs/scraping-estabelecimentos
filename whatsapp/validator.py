from dataclasses import dataclass
import re
from typing import Any, Dict, Optional

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


class EvolutionValidationError(RuntimeError):
    pass


@dataclass
class ValidationResult:
    input_number: str
    normalized_number: str
    exists: bool
    raw_response: Any = None


def sanitize_phone_number(number: Optional[str]) -> str:
    digits = re.sub(r"\D", "", number or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) in {10, 11}:
        digits = f"55{digits}"
    return digits


def _headers() -> Dict[str, str]:
    return {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }


def validate_whatsapp_number(number: str, session=None) -> ValidationResult:
    normalized = sanitize_phone_number(number)
    if len(normalized) < 12:
        return ValidationResult(
            input_number=number or "",
            normalized_number=normalized,
            exists=False,
            raw_response={"reason": "invalid_phone"},
        )

    client = session or requests
    url = f"{settings.EVOLUTION_BASE_URL}/chat/whatsappNumbers/{settings.EVOLUTION_INSTANCE}"

    try:
        response = client.post(
            url,
            headers=_headers(),
            json={"numbers": [normalized]},
            timeout=settings.EVOLUTION_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise EvolutionValidationError(f"Falha ao validar numero no Evolution: {exc}") from exc

    payload: Any = response.json()
    first_item = payload[0] if isinstance(payload, list) and payload else {}
    exists = bool(first_item.get("exists"))
    return ValidationResult(
        input_number=number or "",
        normalized_number=normalized,
        exists=exists,
        raw_response=payload,
    )
