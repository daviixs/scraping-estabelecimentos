from whatsapp import sender as sender_module
from whatsapp.sender import EvolutionSendError, send_text_message


class FakeResponse:
    def __init__(self, payload, should_raise: bool = False):
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self):
        if self._should_raise:
            raise sender_module.requests.HTTPError("boom")

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


def test_send_text_message_normaliza_numero():
    session = FakeSession(FakeResponse({"key": {"id": "abc"}}))
    result = send_text_message("(16) 99999-0000", "teste", session=session)

    assert result.success is True
    assert result.normalized_number == "5516999990000"
    assert session.called_with["json"]["number"] == "5516999990000"


def test_send_text_message_raises_on_http_error():
    session = FakeSession(FakeResponse({}, should_raise=True))

    try:
        send_text_message("5516999990000", "teste", session=session)
    except EvolutionSendError as exc:
        assert "Falha ao enviar mensagem" in str(exc)
    else:
        raise AssertionError("Era esperado EvolutionSendError")
