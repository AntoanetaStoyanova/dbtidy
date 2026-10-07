"""Neutralisation du Jinja dbt pour rendre un modèle parsable par sqlglot.

Chaque remplacement garde la même longueur et les mêmes sauts de ligne, pour
que les positions rapportées par sqlglot correspondent au fichier d'origine.
"""

import re
from dataclasses import dataclass

from beartype import beartype

_BLOCK = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
_CALL_IN_BLOCK = re.compile(r"\b(ref|source)\s*\(([^)]*)\)")
_TOP_CALL = re.compile(r"\{\{-?\s*(ref|source)\s*\(([^)]*)\)\s*-?\}\}")
_ERASED = re.compile(r"\{%.*?%\}|\{#.*?#\}|\{\{-?\s*config\s*\(.*?\)\s*-?\}\}", re.S)
_EXPR = re.compile(r"\{\{.*?\}\}", re.S)
_EXPR_PLACEHOLDER = "__jinja_expr"


@dataclass(frozen=True)
class JinjaCall:
    """Appel `ref()` ou `source()` trouvé dans un modèle.

    Attributes:
        kind: `"ref"` ou `"source"`.
        args: Arguments sans guillemets, par exemple `("erp", "clients")`.
        line: Ligne de l'appel dans le fichier (à partir de 1).
    """

    kind: str
    args: tuple[str, ...]
    line: int

    @property
    def target(self) -> str:
        """Nom lisible de la cible, par exemple `erp.clients`."""
        return ".".join(self.args)


@dataclass(frozen=True)
class Substitution:
    """Résultat de la neutralisation du Jinja.

    Attributes:
        sql: SQL parsable, de même nombre de lignes que l'original.
        mapping: Nom factice → appel Jinja qu'il remplace.
    """

    sql: str
    mapping: dict[str, JinjaCall]


def _args(raw: str) -> tuple[str, ...]:
    return tuple(a.strip().strip("'\"") for a in raw.split(",") if a.strip())


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _fill(fake: str, original: str) -> str:
    blank = re.sub(r"[^\n]", " ", original)
    first_line = original.split("\n", 1)[0]
    if len(fake) <= len(first_line):
        return fake + blank[len(fake) :]
    return fake + "\n" * original.count("\n")


@beartype
def find_calls(raw: str) -> list[JinjaCall]:
    """Liste tous les `ref()`/`source()` du texte brut, y compris dans les macros.

    Args:
        raw: Contenu du fichier `.sql`.

    Returns:
        Les appels dans l'ordre d'apparition.

    Examples:
        >>> find_calls("select * from {{ ref('stg_a') }}")
        [JinjaCall(kind='ref', args=('stg_a',), line=1)]
    """
    calls = []
    for block in _BLOCK.finditer(raw):
        for call in _CALL_IN_BLOCK.finditer(block.group(0)):
            line = _line_at(raw, block.start() + call.start())
            calls.append(JinjaCall(call.group(1), _args(call.group(2)), line))
    return calls


@beartype
def substitute(raw: str) -> Substitution:
    """Remplace le Jinja par du SQL neutre de même longueur.

    `{{ ref() }}` et `{{ source() }}` deviennent des identifiants factices,
    `{% %}`, `{# #}` et `{{ config() }}` sont effacés, les autres `{{ }}`
    deviennent un identifiant générique.

    Args:
        raw: Contenu du fichier `.sql`.

    Returns:
        Le SQL obtenu et la table de correspondance des noms factices.

    Examples:
        >>> s = substitute("select * from {{ ref('stg_a') }}")
        >>> s.sql
        'select * from ref__stg_a        '
        >>> s.mapping["ref__stg_a"].kind
        'ref'
    """
    mapping: dict[str, JinjaCall] = {}

    def replace_call(m: re.Match[str]) -> str:
        args = _args(m.group(2))
        fake = re.sub(r"\W", "_", "__".join([m.group(1), *args]))
        mapping[fake] = JinjaCall(m.group(1), args, _line_at(raw, m.start()))
        return _fill(fake, m.group(0))

    sql = _TOP_CALL.sub(replace_call, raw)
    sql = _ERASED.sub(lambda m: _fill("", m.group(0)), sql)
    sql = _EXPR.sub(lambda m: _fill(_EXPR_PLACEHOLDER, m.group(0)), sql)
    return Substitution(sql, mapping)
