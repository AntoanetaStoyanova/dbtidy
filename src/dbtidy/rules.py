"""Règles d'architecture appliquées à un modèle dbt parsé."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from sqlglot import exp

from dbtidy.jinja import JinjaCall
from dbtidy.layers import Layer


@dataclass(frozen=True)
class Model:
    """Modèle dbt prêt à être vérifié.

    Attributes:
        path: Chemin du fichier `.sql`.
        layer: Couche déduite du préfixe.
        raw: Contenu brut du fichier.
        tree: Arbre sqlglot du SQL après substitution du Jinja.
        calls: Tous les `ref()`/`source()` du texte brut.
        mapping: Nom factice → appel Jinja, issu de la substitution.
    """

    path: Path
    layer: Layer
    raw: str
    tree: exp.Expr
    calls: list[JinjaCall]
    mapping: dict[str, JinjaCall]


@dataclass(frozen=True)
class Violation:
    """Non-respect d'une règle.

    Attributes:
        path: Fichier concerné.
        line: Ligne concernée (à partir de 1).
        code: Code de la règle, par exemple `STG002`.
        message: Ce qui ne va pas.
        fix: Piste de correction.
    """

    path: Path
    line: int
    code: str
    message: str
    fix: str


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


def stg003_no_aggregation(model: Model) -> Iterator[Violation]:
    """STG003 : pas d'agrégation dans le staging, hors fonctions analytiques."""
    if model.layer is not Layer.STAGING:
        return
    for node in model.tree.walk():
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


RULES: list[Rule] = [
    stg001_single_source,
    stg002_no_join,
    stg003_no_aggregation,
    stg004_no_ref,
    ora001_outer_join_mark,
]


@beartype
def apply_rules(model: Model) -> list[Violation]:
    """Applique toutes les règles à un modèle.

    Args:
        model: Modèle parsé.

    Returns:
        Les violations, triées par ligne puis par code, sans doublon.
    """
    found = {v for rule in RULES for v in rule(model)}
    return sorted(found, key=lambda v: (v.line, v.code, v.message))
