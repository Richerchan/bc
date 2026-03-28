from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_data_file(filename: str) -> dict[str, Any]:
    data_path = Path(__file__).resolve().parent / "data" / filename
    return json.loads(data_path.read_text(encoding="utf-8"))
