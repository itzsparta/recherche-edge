import json
from dataclasses import asdict
from pathlib import Path

from orderflow_bot.models import ClosedTrade


class TradeJournal:
    """JSONL append-only : un trade ferme par ligne, avec tout son contexte
    (plan, meta zone/trigger/bias, fills detailles)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, ct: ClosedTrade) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ct)) + "\n")

    @staticmethod
    def load(path: str | Path) -> list[dict]:
        p = Path(path)
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip()]
