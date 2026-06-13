"""Cache disque des plans candidats de la passe 1.

Round-trip JSONL : une passe 1 (lente, signal/zones) genere les candidats une
seule fois ; on les relit pour iterer le filtre d'entree sans re-streamer les
ticks. Memes conventions que le journal (append/load, un objet par ligne)."""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from .models import OrderPlan


def save_plans(path: str | Path, plans: Iterable[OrderPlan]) -> None:
    """Ecrit les plans en JSONL (ecrase). Cree le dossier parent au besoin."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for plan in plans:
            f.write(json.dumps(asdict(plan)) + "\n")


def load_plans(path: str | Path) -> list[OrderPlan]:
    """Relit un cache JSONL. Fichier absent -> liste vide."""
    p = Path(path)
    if not p.exists():
        return []
    return [OrderPlan(**json.loads(line))
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()]
