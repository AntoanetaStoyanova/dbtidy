"""Configuration des logs du projet."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    project_name: str, log_dir: Path = Path("logs"), level: int = logging.INFO
) -> logging.Logger:
    """
    Configure un logger qui écrit sur la console et dans un fichier horodaté.

    Parameters
    ----------
    project_name : str
        Nom du logger et préfixe du fichier de log.
    log_dir : Path
        Dossier des fichiers de log, créé si absent.
    level : int
        Niveau minimal des messages.

    Returns
    -------
    logging.Logger
        Le logger configuré.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{project_name}_{timestamp}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(project_name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
