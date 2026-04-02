import csv
from pathlib import Path
from typing import Dict, List


def import_from_csv(path: str) -> List[Dict]:
    """
    Lê um CSV com colunas mínimas: nome, url, cidade.
    Retorna lista de dicionários compatíveis com o pipeline.
    """
    rows: List[Dict] = []
    with open(Path(path), newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("nome"):
                continue
            rows.append(
                {
                    "nome": row.get("nome"),
                    "categoria": row.get("categoria"),
                    "cidade": row.get("cidade"),
                    "bairro": row.get("bairro"),
                    "telefone": row.get("telefone"),
                    "site": row.get("site"),
                    "nota_media": None,
                    "total_avaliacoes": 0,
                    "link_origem": row.get("url") or row.get("link"),
                    "fonte": "manual",
                    "data_coleta": None,
                    "dono_responde": 0,
                    "comentarios": [],
                }
            )
    return rows


if __name__ == "__main__":
    print(import_from_csv("exemplo.csv"))
