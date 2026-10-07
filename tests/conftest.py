from collections.abc import Callable
from pathlib import Path

import pytest

WriteModel = Callable[[str, str], Path]


@pytest.fixture
def write_model(tmp_path: Path) -> WriteModel:
    def write(name: str, sql: str) -> Path:
        path = tmp_path / "models" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sql, encoding="utf-8")
        return path

    return write
