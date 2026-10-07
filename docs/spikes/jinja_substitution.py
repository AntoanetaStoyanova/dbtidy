"""Spike Phase 0 : parser un modèle dbt après substitution du Jinja."""

import re

import sqlglot
from sqlglot import exp

MODEL = """{{ config(materialized='view') }}

{% set statuts = ['A', 'I'] %}

with src as (
    select * from {{ source('erp', 'clients') }}
),
cmd as (
    select * from {{ ref('stg_commandes') }}
)
select
    src.id,
    {{ dbt_utils.star(ref('stg_commandes')) }},
    nvl(cmd.total, 0) as total
from src
left join cmd on src.id = cmd.client_id
where src.statut in ('A', 'I')
"""

CALL = re.compile(r"\{\{\s*(ref|source)\(([^)]*)\)\s*\}\}")
EXPR = re.compile(r"\{\{.*?\}\}", re.S)
STMT = re.compile(r"\{%.*?%\}|\{#.*?#\}|\{\{\s*config\(.*?\)\s*\}\}", re.S)


def _pad(text: str, width: int) -> str:
    return text.ljust(width) if len(text) <= width else text


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def substitute(sql: str) -> tuple[str, dict[str, str]]:
    """Remplace ref/source par des identifiants factices de même longueur."""
    mapping: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        args = [a.strip().strip("'\"") for a in m.group(2).split(",")]
        fake = "__".join([m.group(1), *args])
        mapping[fake] = m.group(0)
        return _pad(fake, len(m.group(0)))

    sql = CALL.sub(repl, sql)
    sql = STMT.sub(_blank, sql)
    sql = EXPR.sub(lambda m: _pad("__jinja_expr", len(m.group(0))), sql)
    return sql, mapping


clean, mapping = substitute(MODEL)
assert clean.count("\n") == MODEL.count("\n")
print(clean)
print(mapping)
tree = sqlglot.parse_one(clean, dialect="oracle")
for t in tree.find_all(exp.Table):
    print(t.name, "ligne", t.this.meta.get("line"), "->", mapping.get(t.name, "(cte)"))
for line_no, line in enumerate(MODEL.splitlines(), 1):
    if "ref(" in line or "source(" in line:
        print(f"source ligne {line_no}: {line.strip()}")
