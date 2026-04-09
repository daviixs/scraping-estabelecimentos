import random


VARIACOES_ABERTURA = [
    "Ola, tudo bem?",
    "Oi, tudo certo?",
    "Ola! Boa tarde.",
    "Oi! Tudo bem por ai?",
]


def gerar_mensagem(nome: str, categoria: str) -> str:
    abertura = random.choice(VARIACOES_ABERTURA)
    nome_seguro = (nome or "pessoal").strip()
    categoria_segura = (categoria or "negocios locais").strip()
    return (
        f"{abertura} Falo com {nome_seguro}? Aqui e o Gustavo, da InovaSociety.\n\n"
        f"Estamos desenvolvendo solucoes para ajudar {categoria_segura} a organizar "
        f"processos, prazos e rotinas operacionais de forma mais eficiente.\n\n"
        "Antes de construir qualquer ferramenta, estamos conversando com alguns "
        "estabelecimentos para entender os desafios reais do dia a dia.\n\n"
        "Podemos conversar?"
    )
