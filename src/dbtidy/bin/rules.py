"""Règles d'architecture appliquées à un modèle dbt parsé."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from beartype import beartype
from sqlglot import exp

from dbtidy.bin.jinja import THIS, JinjaCall
from dbtidy.bin.layers import Layer, folder_layer
from dbtidy.config import Config, Severity


@dataclass(frozen=True)
class Model:
    """
    Modèle dbt prêt à être vérifié.

    Attributes
    ----------
    path : Path
        Chemin du fichier `.sql`.
    layer : Layer
        Couche déduite du préfixe.
    raw : str
        Contenu brut du fichier.
    tree : exp.Expr
        Arbre sqlglot du SQL après substitution du Jinja.
    calls : list[JinjaCall]
        Tous les `ref()`/`source()` du texte brut.
    mapping : dict[str, JinjaCall]
        Nom factice → appel Jinja, issu de la substitution.
    config : Config
        Configuration appliquée.
    """

    path: Path
    layer: Layer
    raw: str
    tree: exp.Expr
    calls: list[JinjaCall]
    mapping: dict[str, JinjaCall]
    config: Config


@dataclass(frozen=True)
class Violation:
    """
    Non-respect d'une règle.

    Attributes
    ----------
    path : Path
        Fichier concerné.
    line : int
        Ligne concernée (à partir de 1).
    code : str
        Code de la règle, par exemple `STG002`.
    message : str
        Ce qui ne va pas.
    fix : str
        Piste de correction.
    severity : Severity
        Sévérité issue de la configuration.
    """

    path: Path
    line: int
    code: str
    message: str
    fix: str
    severity: Severity = Severity.ERROR


Rule = Callable[[Model], Iterator[Violation]]


def _line(node: exp.Expr) -> int:
    for child in node.walk():
        line = child.meta.get("line")
        if isinstance(line, int):
            return line
    return 1


def _table_label(model: Model, node: exp.Expr) -> str:
    table = node if isinstance(node, exp.Table) else node.find(exp.Table)
    if table is None:
        return "une sous-requête"
    call = model.mapping.get(table.name)
    if call is None:
        return table.sql(dialect="oracle")
    return f"{call.kind}('{call.target}')"


def stg001_single_source(model: Model) -> Iterator[Violation]:
    """STG001 : un modèle staging ne lit qu'une seule source."""
    if model.layer is not Layer.STAGING:
        return
    seen: dict[str, JinjaCall] = {}
    for call in model.calls:
        if call.kind == "source":
            seen.setdefault(call.target, call)
    if len(seen) > 1:
        names = ", ".join(seen)
        yield Violation(
            model.path,
            list(seen.values())[1].line,
            "STG001",
            f"Le modèle staging lit {len(seen)} sources ({names}).",
            "Créez un modèle staging par source, puis combinez-les dans un "
            "modèle intermediate (int_).",
        )


def stg002_no_join(model: Model) -> Iterator[Violation]:
    """STG002 : pas de jointure dans le staging."""
    if model.layer is not Layer.STAGING:
        return
    for join in model.tree.find_all(exp.Join):
        yield Violation(
            model.path,
            _line(join),
            "STG002",
            f"Jointure avec {_table_label(model, join.this)} dans un modèle staging.",
            "Déplacez la jointure dans un modèle intermediate (int_) ; le "
            "staging se limite à renommer, typer et nettoyer une source.",
        )


def _reads_this(node: exp.Expr) -> bool:
    """Vrai si le `SELECT` du nœud lit `{{ this }}` (filtre incrémental)."""
    select = node if isinstance(node, exp.Select) else node.find_ancestor(exp.Select)
    source = select.args.get("from_") if select else None
    tables = source.find_all(exp.Table) if source else ()
    return any(table.name == THIS for table in tables)


def stg003_no_aggregation(model: Model) -> Iterator[Violation]:
    """STG003 : pas d'agrégation en staging, hors analytiques et filtre `{{ this }}`."""
    if model.layer is not Layer.STAGING:
        return
    for node in model.tree.walk():
        if _reads_this(node):
            continue
        if isinstance(node, exp.Group):
            what = "GROUP BY"
        elif isinstance(node, exp.Distinct):
            what = "DISTINCT"
        elif isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Window):
            what = node.sql_name()
        else:
            continue
        yield Violation(
            model.path,
            _line(node),
            "STG003",
            f"Agrégation ({what}) dans un modèle staging.",
            "Gardez le grain de la source en staging et agrégez dans un "
            "modèle intermediate (int_) ou mart (fct_).",
        )


def stg004_no_ref(model: Model) -> Iterator[Violation]:
    """STG004 : le staging lit une source, pas un autre modèle."""
    if model.layer is not Layer.STAGING:
        return
    for call in model.calls:
        if call.kind == "ref":
            yield Violation(
                model.path,
                call.line,
                "STG004",
                f"Le modèle staging lit un autre modèle (ref('{call.target}')).",
                "Lisez la donnée brute avec source() ; pour réutiliser un "
                "modèle, passez par un modèle intermediate (int_).",
            )


def ora001_outer_join_mark(model: Model) -> Iterator[Violation]:
    """ORA001 : jointure Oracle `(+)`, toutes couches."""
    for column in model.tree.find_all(exp.Column):
        if column.args.get("join_mark"):
            yield Violation(
                model.path,
                _line(column),
                "ORA001",
                f"Jointure Oracle (+) sur {column.sql(dialect='oracle')}.",
                "Réécrivez-la en LEFT JOIN ... ON ... (syntaxe ANSI), plus "
                "lisible et portable.",
            )


def ora002_nvl(model: Model) -> Iterator[Violation]:
    """ORA002 : `NVL`, toutes couches."""
    for node in model.tree.find_all(exp.Coalesce):
        if node.args.get("is_nvl"):
            yield Violation(
                model.path,
                _line(node),
                "ORA002",
                f"NVL dans {node.sql(dialect='oracle')}.",
                "Remplacez NVL par COALESCE (norme ANSI, accepte plus de deux "
                "arguments).",
            )


def ora003_decode(model: Model) -> Iterator[Violation]:
    """ORA003 : `DECODE`, toutes couches."""
    for node in model.tree.find_all(exp.DecodeCase):
        yield Violation(
            model.path,
            _line(node),
            "ORA003",
            f"DECODE dans {node.sql(dialect='oracle')}.",
            "Réécrivez-le en CASE WHEN ... THEN ... END, plus lisible et portable.",
        )


def _is_empty_string(node: exp.Expr) -> bool:
    return isinstance(node, exp.Literal) and node.is_string and node.name == ""


def ora004_empty_string(model: Model) -> Iterator[Violation]:
    """ORA004 : comparaison à `''`, qu'Oracle traite comme `NULL`."""
    for node in model.tree.find_all(exp.EQ, exp.NEQ):
        sides = (node.this, node.expression)
        if not any(_is_empty_string(side) for side in sides):
            continue
        other = next((s for s in sides if not _is_empty_string(s)), node.this)
        test = "IS NULL" if isinstance(node, exp.EQ) else "IS NOT NULL"
        yield Violation(
            model.path,
            _line(node),
            "ORA004",
            f"Comparaison à '' ({node.sql(dialect='oracle')}) : Oracle traite '' "
            "comme NULL, la condition n'est jamais vraie.",
            f"Écrivez {other.sql(dialect='oracle')} {test}.",
        )


_NAMED = (exp.Alias, exp.TableAlias, exp.Column)


def ora005_identifier_length(model: Model) -> Iterator[Violation]:
    """ORA005 : alias, CTE ou colonne plus long que la limite Oracle."""
    limit = model.config.oracle.max_identifier_length
    first: dict[str, int] = {}
    for node in model.tree.find_all(exp.Identifier):
        name = node.name
        if (
            len(name) > limit
            and isinstance(node.parent, _NAMED)
            and name not in model.mapping
        ):
            first[name] = min(first.get(name, _line(node)), _line(node))
    for name, line in first.items():
        yield Violation(
            model.path,
            line,
            "ORA005",
            f"Identifiant {name} trop long ({len(name)} caractères, limite {limit}).",
            f"Raccourcissez-le à {limit} caractères au plus, ou relevez "
            "oracle.max_identifier_length si la base est en Oracle 12.2 ou plus.",
        )


def nam001_prefix_matches_folder(model: Model) -> Iterator[Violation]:
    """NAM001 : le préfixe du fichier correspond à la couche de son dossier."""
    folder = folder_layer(model.path, model.config)
    if folder is None or folder == model.layer:
        return
    prefixes = ", ".join(getattr(model.config.layers, folder).prefixes)
    actual = (
        "n'est celui d'aucune couche"
        if model.layer is Layer.UNKNOWN
        else f"est celui de la couche {model.layer}"
    )
    yield Violation(
        model.path,
        1,
        "NAM001",
        f"{model.path.name} est dans le dossier {folder} mais son préfixe {actual}.",
        f"Renommez le fichier avec un préfixe {folder} ({prefixes}) ou "
        "déplacez-le dans le dossier de sa couche.",
    )


def nam002_column_case(model: Model) -> Iterator[Violation]:
    """NAM002 : casse des alias du SELECT le plus externe."""
    case = model.config.columns_case
    if case is None or not isinstance(model.tree, exp.Query):
        return
    for node in model.tree.selects:
        if not isinstance(node, exp.Alias):
            continue
        name = node.alias
        expected = name.lower() if case == "lower" else name.upper()
        if name != expected:
            yield Violation(
                model.path,
                _line(node),
                "NAM002",
                f"L'alias {name} n'est pas en casse {case}.",
                f"Renommez-le {expected}.",
            )


RULES: dict[str, Rule] = {
    "STG001": stg001_single_source,
    "STG002": stg002_no_join,
    "STG003": stg003_no_aggregation,
    "STG004": stg004_no_ref,
    "ORA001": ora001_outer_join_mark,
    "ORA002": ora002_nvl,
    "ORA003": ora003_decode,
    "ORA004": ora004_empty_string,
    "ORA005": ora005_identifier_length,
    "NAM001": nam001_prefix_matches_folder,
    "NAM002": nam002_column_case,
}


@beartype
def apply_rules(model: Model) -> list[Violation]:
    """
    Applique les règles actives à un modèle, avec leur sévérité.

    Parameters
    ----------
    model : Model
        Modèle parsé ; `model.config.rules` donne la sévérité de chaque
        règle, et celles en `off` ne sont pas exécutées.

    Returns
    -------
    list[Violation]
        Les violations, triées par ligne puis par code, sans doublon.
    """
    found = {
        replace(v, severity=severity)
        for code, rule in RULES.items()
        if (severity := model.config.rules[code]) is not Severity.OFF
        for v in rule(model)
    }
    return sorted(found, key=lambda v: (v.line, v.code, v.message))
