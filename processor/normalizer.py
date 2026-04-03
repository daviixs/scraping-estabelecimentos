from typing import Dict, Optional

from config import settings


def _clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_city(value: Optional[str]) -> str:
    # SQLite considera NULL distinto em UNIQUE, entao usamos string vazia
    # como fallback estavel quando a fonte nao informa a cidade.
    return _clean_str(value) or ""


def classify_nota(nota_media: Optional[float]) -> Optional[str]:
    if nota_media is None:
        return None
    if nota_media >= settings.FAIXA_MUITO_BOM:
        return "MUITO BOM"
    if nota_media >= settings.FAIXA_MEDIO:
        return "MÉDIO"
    return "MUITO RUIM"


def normalize_estabelecimento(raw: Dict) -> Dict:
    data = dict(raw)
    data["nome"] = _clean_str(data.get("nome"))
    data["categoria"] = _clean_str(data.get("categoria"))
    data["cidade"] = _clean_city(data.get("cidade"))
    data["bairro"] = _clean_str(data.get("bairro"))
    data["telefone"] = _clean_str(data.get("telefone"))
    data["site"] = _clean_str(data.get("site"))
    data["link_origem"] = _clean_str(data.get("link_origem"))
    try:
        data["nota_media"] = float(data["nota_media"]) if data.get("nota_media") is not None else None
    except (TypeError, ValueError):
        data["nota_media"] = None
    try:
        data["total_avaliacoes"] = int(data["total_avaliacoes"]) if data.get("total_avaliacoes") is not None else 0
    except (TypeError, ValueError):
        data["total_avaliacoes"] = 0
    data["faixa_classificacao"] = classify_nota(data.get("nota_media"))
    return data
