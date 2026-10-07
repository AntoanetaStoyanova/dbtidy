"""Point d'entrée en ligne de commande de dbtidy."""

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path

from beartype import beartype

from dbtidy import __version__
from dbtidy.check import format_json, format_text, run_check

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
    return parser


@beartype
def main(argv: Sequence[str] | None = None) -> int:
    """Exécute la commande demandée.

    Args:
        argv: Arguments de la ligne de commande, `sys.argv[1:]` par défaut.

    Returns:
        `0` conforme, `1` violation, `2` erreur de configuration ou de parsing.
    """
    args = _parser().parse_args(argv)
    try:
        report = run_check(args.paths)
    except FileNotFoundError as error:
        sys.stderr.write(f"{PROJECT_NAME}: {error}\n")
        return 2
    output = format_json(report) if args.json else format_text(report)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(output + "\n")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
