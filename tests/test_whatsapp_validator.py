from whatsapp import validator as validator_module
from whatsapp.validator import EvolutionValidationError, sanitize_phone_number, validate_whatsapp_number


class FakeResponse:
    def __init__(self, payload, should_raise: bool = False):
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self):
        if self._should_raise:
            raise validator_module.requests.HTTPError("boom")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.called_with = None

    def post(self, url, headers=None, json=None, timeout=None):
        self.called_with = {
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        }
        return self.response


def test_sanitize_phone_number_prefixa_codigo_pais():
    assert sanitize_phone_number("(16) 99999-0000") == "5516999990000"


def test_validate_whatsapp_number_returns_exists():
    session = FakeSession(FakeResponse([{"number": "5516999990000", "exists": True}]))
    result = validate_whatsapp_number("(16) 99999-0000", session=session)

    assert result.exists is True
    assert result.normalized_number == "5516999990000"
    assert session.called_with["json"]["numbers"] == ["5516999990000"]


def test_validate_whatsapp_number_raises_on_http_error():
    session = FakeSession(FakeResponse({}, should_raise=True))

    try:
        validate_whatsapp_number("5516999990000", session=session)
    except EvolutionValidationError as exc:
        assert "Falha ao validar numero" in str(exc)
    else:
        raise AssertionError("Era esperado EvolutionValidationError")
