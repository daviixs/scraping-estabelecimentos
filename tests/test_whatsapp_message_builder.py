from whatsapp.message_builder import gerar_mensagem


def test_gerar_mensagem_inclui_nome_e_categoria(monkeypatch):
    monkeypatch.setattr("whatsapp.message_builder.random.choice", lambda values: values[0])
    mensagem = gerar_mensagem("Padaria Aurora", "padarias")

    assert "Padaria Aurora" in mensagem
    assert "padarias" in mensagem
    assert "Gustavo" in mensagem
