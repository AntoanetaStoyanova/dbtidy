import logging
from pathlib import Path

from dbtidy.log import setup_logging


def test_setup_logging_writes_to_file(tmp_path: Path) -> None:
    logger = setup_logging("demo", log_dir=tmp_path / "logs", level=logging.DEBUG)
    logger.debug("bonjour")
    for handler in logger.handlers:
        handler.flush()

    (log_file,) = (tmp_path / "logs").glob("demo_*.log")
    assert "bonjour" in log_file.read_text(encoding="utf-8")
    assert logger.level == logging.DEBUG
