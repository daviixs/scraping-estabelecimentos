from processor import nlp_comments


def test_contar_queixas():
    comentarios = [
        "O atendimento foi muito ruim e demorado",
        "Sistema travou e o app não funcionou",
        "Preço caro",
    ]
    counts = nlp_comments.contar_queixas(comentarios)
    assert counts["atendimento"] >= 1
    assert counts["demora"] >= 1
    assert counts["sistema"] >= 1
    assert counts["preco"] >= 1


def test_resumo():
    counts = {"atendimento": 2, "demora": 1, "sistema": 0, "limpeza": 0, "preco": 0, "qualidade": 0}
    resumo = nlp_comments.resumo_queixas(counts)
    assert "atendimento (2)" in resumo
    assert "demora (1)" in resumo
