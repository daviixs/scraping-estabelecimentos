CATEGORIAS_QUEIXA = {
    "atendimento": [
        "atendimento",
        "grosseiro",
        "ignorou",
        "mal atendido",
        "rude",
        "funcionário",
        "garçom",
        "recepcionista",
        "educação",
    ],
    "demora": [
        "demora",
        "demorou",
        "espera",
        "fila",
        "lento",
        "tardou",
        "muito tempo",
        "hora",
        "atraso",
    ],
    "sistema": [
        "sistema",
        "app",
        "aplicativo",
        "travou",
        "não funcionou",
        "bug",
        "erro",
        "tecnologia",
        "plataforma",
        "software",
    ],
    "limpeza": [
        "sujo",
        "sujeira",
        "limpeza",
        "higiene",
        "barata",
        "mosquito",
        "cheiro",
        "fedorento",
    ],
    "preco": [
        "caro",
        "preço",
        "valor",
        "cobrado",
        "cobrança",
        "abusivo",
        "não vale",
        "salgado",
    ],
    "qualidade": [
        "qualidade",
        "ruim",
        "péssimo",
        "horrível",
        "decepcionante",
        "não recomendo",
        "nunca mais",
    ],
}


def contar_queixas(comentarios: list[str]) -> dict:
    counts = {cat: 0 for cat in CATEGORIAS_QUEIXA}
    for texto in comentarios:
        if not texto:
            continue
        lower = texto.lower()
        for categoria, termos in CATEGORIAS_QUEIXA.items():
            if any(term in lower for term in termos):
                counts[categoria] += 1
    return counts


def resumo_queixas(counts: dict) -> str:
    itens = [(cat, n) for cat, n in counts.items() if n > 0]
    itens.sort(key=lambda x: x[1], reverse=True)
    return ", ".join(f"{cat} ({n})" for cat, n in itens)


def proporcao_queixas(counts: dict, total_analisados: int) -> float:
    if total_analisados <= 0:
        return 0.0
    return min(sum(counts.values()) / float(total_analisados), 1.0)
