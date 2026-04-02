from config import settings


def prioridade_por_score(score: float) -> str:
    if score >= settings.SCORE_PRIORIDADE_ALTA:
        return "ALTA"
    if score >= settings.SCORE_PRIORIDADE_MEDIA:
        return "MÉDIA"
    return "BAIXA"


def calcular_score(
    nota_media: float,
    total_avaliacoes: int,
    queixas_ratio: float,
    queda: bool,
    sem_reply: bool,
) -> float:
    nota_inv = (5.0 - float(nota_media)) / 4.0 if nota_media is not None else 0.0
    vol_norm = min(total_avaliacoes / settings.VOLUME_MAXIMO_NORM, 1.0)
    queixas = min(max(queixas_ratio, 0.0), 1.0)
    queda_val = 1.0 if queda else 0.0
    sem_reply_val = 1.0 if sem_reply else 0.0

    score = (
        nota_inv * settings.PESO_NOTA_INVERTIDA
        + vol_norm * settings.PESO_VOLUME_REVIEWS
        + queixas * settings.PESO_QUEIXAS
        + queda_val * settings.PESO_QUEDA_REPUTACAO
        + sem_reply_val * settings.PESO_SEM_REPLY
    ) * 100.0
    return round(min(max(score, 0.0), 100.0), 2)
