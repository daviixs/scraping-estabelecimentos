from processor import scorer
from config import settings


def test_prioridade_por_score():
    assert scorer.prioridade_por_score(80) == "ALTA"
    assert scorer.prioridade_por_score(45) == "MÉDIA"
    assert scorer.prioridade_por_score(10) == "BAIXA"


def test_calcular_score_components():
    score = scorer.calcular_score(
        nota_media=4.0,
        total_avaliacoes=settings.VOLUME_MAXIMO_NORM,
        queixas_ratio=0.5,
        queda=True,
        sem_reply=True,
    )
    # Rough expectations: nota_inv=0.25, vol=1, queixas=0.5, queda=1, sem_reply=1
    # weighted => (0.25*0.3)+(1*0.2)+(0.5*0.25)+(1*0.15)+(1*0.1)=0.075+0.2+0.125+0.15+0.1=0.65 => 65
    assert 64.9 <= score <= 65.1
