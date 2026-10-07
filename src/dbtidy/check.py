"""Commande `check` : analyse des fichiers `.sql` d'un projet dbt."""

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import sqlglot
from beartype import beartype
from sqlglot.errors import SqlglotError

from dbtidy.jinja import find_calls, substitute
from dbtidy.layers import layer_of
from dbtidy.rules import Model, Violation, apply_rules

EXCLUDED_DIRS = {"target", "dbt_packages"}
_NOQA = re.compile(r"--\s*noqa\b(?:\s*:\s*(?P<codes>[\w\s,]+))?", re.I)


@dataclass(frozen=True)
class CheckError:
    """Fichier qui n'a pas pu être analysé.

    Attributes:
        path: Fichier concerné.
        message: Cause de l'échec.
    """

    path: Path
    message: str


@dataclass
class Report:
    """Résultat d'un `check` sur un ensemble de fichiers.

    Attributes:
        files: Nombre de fichiers analysés.
        violations: Violations trouvées.
        errors: Fichiers illisibles ou non parsables.
    """

    files: int = 0
    violations: list[Violation] = field(default_factory=list)
    errors: list[CheckError] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        """`2` si une erreur, sinon `1` si une violation, sinon `0`."""
        if self.errors:
            return 2
        return 1 if self.violations else 0


@beartype
def collect_files(paths: Iterable[Path]) -> list[Path]:
    """Liste les fichiers `.sql` à analyser.

    Args:
        paths: Fichiers ou dossiers ; les dossiers sont parcourus récursivement,
            sans `target/` ni `dbt_packages/`.

    Returns:
        Les fichiers triés, sans doublon.

    Raises:
        FileNotFoundError: Si un chemin n'existe pas.
    """
    files: set[Path] = set()
    for path in paths:
        if path.is_file():
            files.add(path)
        elif path.is_dir():
            files.update(
                f
                for f in path.rglob("*.sql")
                if not EXCLUDED_DIRS.intersection(f.relative_to(path).parts)
            )
        else:
            raise FileNotFoundError(f"Chemin introuvable : {path}")
    return sorted(files)


def _noqa(raw: str) -> dict[int, set[str] | None]:
    """Ligne → codes désactivés (`None` : tous les codes)."""
    result: dict[int, set[str] | None] = {}
    for number, line in enumerate(raw.splitlines(), 1):
        match = _NOQA.search(line)
        if match:
            codes = match.group("codes")
            result[number] = (
                {c.strip().upper() for c in codes.split(",") if c.strip()}
                if codes
                else None
            )
    return result


def _ignored(violation: Violation, noqa: dict[int, set[str] | None]) -> bool:
    if violation.line not in noqa:
        return False
    codes = noqa[violation.line]
    return codes is None or violation.code in codes


@beartype
def check_file(path: Path) -> list[Violation]:
    """Analyse un modèle et renvoie ses violations, hors lignes `-- noqa`.

    Args:
        path: Fichier `.sql` du modèle.

    Returns:
        Les violations restantes.

    Raises:
        OSError: Si le fichier est illisible.
        SqlglotError: Si le SQL ne peut pas être parsé.
    """
    raw = path.read_text(encoding="utf-8")
    substitution = substitute(raw)
    tree = sqlglot.parse_one(substitution.sql, dialect="oracle")
    model = Model(
        path, layer_of(path), raw, tree, find_calls(raw), substitution.mapping
    )
    noqa = _noqa(raw)
    return [v for v in apply_rules(model) if not _ignored(v, noqa)]


@beartype
def run_check(paths: Iterable[Path]) -> Report:
    """Analyse tous les fichiers `.sql` désignés.

    Args:
        paths: Fichiers ou dossiers à analyser.

    Returns:
        Le rapport complet ; un fichier en erreur n'arrête pas l'analyse.

    Raises:
        FileNotFoundError: Si un chemin n'existe pas.
    """
    report = Report()
    for path in collect_files(paths):
        report.files += 1
        try:
            report.violations.extend(check_file(path))
        except (OSError, UnicodeDecodeError, SqlglotError) as error:
            first_line = str(error).splitlines()[0] if str(error) else repr(error)
            report.errors.append(CheckError(path, f"SQL non analysable : {first_line}"))
    return report


@beartype
def format_text(report: Report) -> str:
    """Met en forme le rapport pour la console.

    Args:
        report: Rapport à afficher.

    Returns:
        Une violation par bloc (position, code, message, piste), puis un résumé.
    """
    lines = []
    for v in report.violations:
        lines.append(f"{v.path}:{v.line}: {v.code} {v.message}")
        lines.append(f"    → {v.fix}")
    for e in report.errors:
        lines.append(f"{e.path}: ERREUR {e.message}")
    if report.violations or report.errors:
        lines.append("")
    lines.append(
        f"{report.files} fichier(s) analysé(s), "
        f"{len(report.violations)} violation(s), {len(report.errors)} erreur(s)."
    )
    return "\n".join(lines)


@beartype
def format_json(report: Report) -> str:
    """Met en forme le rapport en JSON pour la CI.

    Args:
        report: Rapport à sérialiser.

    Returns:
        Un objet JSON avec `files`, `violations`, `errors` et `exit_code`.
    """
    payload = {
        "files": report.files,
        "violations": [asdict(v) | {"path": str(v.path)} for v in report.violations],
        "errors": [asdict(e) | {"path": str(e.path)} for e in report.errors],
        "exit_code": report.exit_code,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
