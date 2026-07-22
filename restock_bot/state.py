import json
from pathlib import Path


class StateStore:
    """Tracks which product keys were seen in stock on the last run, so we
    only alert once per restock instead of every time the checker runs.
    """

    def __init__(self, path: str = "state/seen_in_stock.json") -> None:
        self.path = Path(path)

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        return set(json.loads(self.path.read_text()))

    def save(self, keys: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(keys), indent=2) + "\n")
