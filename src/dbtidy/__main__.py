"""Point d'entrée en ligne de commande de dbtidy."""

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path

from beartype import beartype

from dbtidy import __version__
from dbtidy.bin.check import format_json, format_text, run_check
from dbtidy.config import CONFIG_FILE, ConfigError, load_config

PROJECT_NAME = "dbtidy"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROJECT_NAME,
        description="Linter de projets dbt sur Oracle, attentif aux couches.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Vérifie l'architecture des modèles.")
    check.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("models")],
        help="Fichiers ou dossiers .sql (défaut : models).",
    )
    check.add_argument("--json", action="store_true", help="Sortie JSON pour la CI.")
    check.add_argument(
        "--config",
        type=Path,
        help=f"Fichier de configuration (défaut : {CONFIG_FILE} s'il existe).",
    )
    validate = commands.add_parser(
        "validate-config", help="Valide un fichier de configuration."
    )
    validate.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path(CONFIG_FILE),
        help=f"Fichier à valider (défaut : {CONFIG_FILE}).",
    )
    return parser


def _validate_config(path: Path) -> int:
    try:
        load_config(path)
    except ConfigError as error:
        sys.stderr.write(f"{PROJECT_NAME}: {error}\n")
        return 2
    sys.stdout.write(f"{path}: Configuration valide\n")
    return 0


@beartype
def main(argv: Sequence[str] | None = None) -> int:
    """
    Exécute la commande demandée.

    Parameters
    ----------
    argv : Sequence[str] | None
        Arguments de la ligne de commande, `sys.argv[1:]` par défaut.

    Returns
    -------
    int
        `0` conforme, `1` violation, `2` erreur de configuration ou de parsing.
    """
    args = _parser().parse_args(argv)
    if args.command == "validate-config":
        return _validate_config(args.path)
    try:
        report = run_check(args.paths, load_config(args.config))
    except (ConfigError, FileNotFoundError) as error:
        sys.stderr.write(f"{PROJECT_NAME}: {error}\n")
        return 2
    output = format_json(report) if args.json else format_text(report)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(output + "\n")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
