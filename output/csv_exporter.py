import csv
from typing import Dict, List


def export_csv(registros: List[Dict], filepath: str) -> None:
    if not registros:
        return
    fieldnames = list(registros[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in registros:
            writer.writerow(row)
