"""Commande `check` : analyse des fichiers `.sql` d'un projet dbt."""

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import sqlglot
from beartype import beartype
from sqlglot.errors import SqlglotError

from dbtidy.bin.jinja import find_calls, substitute
from dbtidy.bin.layers import layer_of
from dbtidy.bin.rules import Model, Violation, apply_rules
from dbtidy.config import Config, Severity

EXCLUDED_DIRS = {"target", "dbt_packages"}
_NOQA = re.compile(
    r"--\s*noqa\b(?:\s*:\s*(?P<codes>[a-z]+\d+(?:\s*,\s*[a-z]+\d+)*))?", re.I
)


@dataclass(frozen=True)
class CheckError:
    """
    Fichier qui n'a pas pu être analysé.

    Attributes
    ----------
    path : Path
        Fichier concerné.
    message : str
        Cause de l'échec.
    """

    path: Path
    message: str


@dataclass
class Report:
    """
    Résultat d'un `check` sur un ensemble de fichiers.

    Attributes
    ----------
    files : int
        Nombre de fichiers analysés.
    violations : list[Violation]
        Violations trouvées.
    errors : list[CheckError]
        Fichiers illisibles ou non parsables.
    """

    files: int = 0
    violations: list[Violation] = field(default_factory=list)
    errors: list[CheckError] = field(default_factory=list)

    def count(self, severity: Severity) -> int:
        """Nombre de violations de la sévérité donnée."""
        return sum(v.severity is severity for v in self.violations)

    @property
    def exit_code(self) -> int:
        """`2` si une erreur, sinon `1` si une violation `error`, sinon `0`."""
        if self.errors:
            return 2
        return 1 if self.count(Severity.ERROR) else 0


@beartype
def collect_files(paths: Iterable[Path]) -> list[Path]:
    """
    Liste les fichiers `.sql` à analyser.

    Parameters
    ----------
    paths : Iterable[Path]
        Fichiers ou dossiers ; les dossiers sont parcourus récursivement,
        sans `target/` ni `dbt_packages/`.

    Returns
    -------
    list[Path]
        Les fichiers triés, sans doublon.

    Raises
    ------
    FileNotFoundError
        Si un chemin n'existe pas.
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
def check_file(path: Path, config: Config) -> list[Violation]:
    """
    Analyse un modèle et renvoie ses violations, hors lignes `-- noqa`.

    Un modèle sans SQL (vide, ou seulement du Jinja et des commentaires) n'a
    aucune violation.

    Parameters
    ----------
    path : Path
        Fichier `.sql` du modèle.
    config : Config
        Configuration appliquée.

    Returns
    -------
    list[Violation]
        Les violations restantes.

    Raises
    ------
    OSError
        Si le fichier est illisible.
    SqlglotError
        Si le SQL ne peut pas être parsé.
    """
    raw = path.read_text(encoding="utf-8")
    substitution = substitute(raw)
    if not sqlglot.tokenize(substitution.sql, dialect="oracle"):
        return []
    tree = sqlglot.parse_one(substitution.sql, dialect="oracle")
    model = Model(
        path,
        layer_of(path, config),
        raw,
        tree,
        find_calls(raw),
        substitution.mapping,
        config,
    )
    noqa = _noqa(raw)
    return [v for v in apply_rules(model) if not _ignored(v, noqa)]


@beartype
def run_check(paths: Iterable[Path], config: Config) -> Report:
    """
    Analyse tous les fichiers `.sql` désignés.

    Parameters
    ----------
    paths : Iterable[Path]
        Fichiers ou dossiers à analyser.
    config : Config
        Configuration appliquée.

    Returns
    -------
    Report
        Le rapport complet ; un fichier en erreur n'arrête pas l'analyse.

    Raises
    ------
    FileNotFoundError
        Si un chemin n'existe pas.
    """
    report = Report()
    for path in collect_files(paths):
        report.files += 1
        try:
            report.violations.extend(check_file(path, config))
        except (OSError, UnicodeDecodeError) as error:
            report.errors.append(CheckError(path, f"fichier illisible : {error}"))
        except SqlglotError as error:
            first_line = str(error).splitlines()[0] if str(error) else repr(error)
            report.errors.append(CheckError(path, f"SQL non analysable : {first_line}"))
    return report


@beartype
def format_text(report: Report) -> str:
    """
    Met en forme le rapport pour la console.

    Parameters
    ----------
    report : Report
        Rapport à afficher.

    Returns
    -------
    str
        Une violation par bloc (position, code, sévérité si `warning`, message,
        piste), puis un résumé.
    """
    lines = []
    for v in report.violations:
        tag = " [warning]" if v.severity is Severity.WARNING else ""
        lines.append(f"{v.path}:{v.line}: {v.code}{tag} {v.message}")
        lines.append(f"    → {v.fix}")
    for e in report.errors:
        lines.append(f"{e.path}: ERREUR {e.message}")
    if report.violations or report.errors:
        lines.append("")
    lines.append(
        f"{report.files} fichier(s) analysé(s), "
        f"{report.count(Severity.ERROR)} violation(s), "
        f"{report.count(Severity.WARNING)} avertissement(s), "
        f"{len(report.errors)} erreur(s)."
    )
    return "\n".join(lines)


@beartype
def format_json(report: Report) -> str:
    """
    Met en forme le rapport en JSON pour la CI.

    Parameters
    ----------
    report : Report
        Rapport à sérialiser.

    Returns
    -------
    str
        Un objet JSON avec `files`, `violations` (dont `severity`), `errors` et
        `exit_code`.
    """
    payload = {
        "files": report.files,
        "violations": [asdict(v) | {"path": str(v.path)} for v in report.violations],
        "errors": [asdict(e) | {"path": str(e.path)} for e in report.errors],
        "exit_code": report.exit_code,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
