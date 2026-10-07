from dbtidy.jinja import JinjaCall, find_calls, substitute

MODEL = """{{ config(materialized='view') }}
{% set statuts = ['A', 'I'] %}
{# commentaire #}
select
    {{ dbt_utils.star(ref('stg_commandes')) }},
    {{ var('seuil') }} as seuil
from {{ source('erp', 'clients') }}
"""


def test_substitute_keeps_lines_and_columns() -> None:
    result = substitute(MODEL)
    assert [len(line) for line in result.sql.splitlines()] == [
        len(line) for line in MODEL.splitlines()
    ]
    assert result.sql.splitlines()[6] == "from source__erp__clients" + " " * 10
    assert "{" not in result.sql


def test_substitute_mapping() -> None:
    result = substitute(MODEL)
    assert result.mapping == {
        "source__erp__clients": JinjaCall("source", ("erp", "clients"), 7)
    }


def test_substitute_multiline_call_keeps_line_count() -> None:
    for raw in [
        "select * from {{ ref(\n'x'\n) }}\nwhere 1 = 1",
        "select * from {{ref(\n'stg_clients')}}\nwhere 1 = 1",
    ]:
        result = substitute(raw)
        assert result.sql.count("\n") == raw.count("\n")
        assert next(iter(result.mapping)) in result.sql


def test_find_calls_includes_nested_refs() -> None:
    assert find_calls(MODEL) == [
        JinjaCall("ref", ("stg_commandes",), 5),
        JinjaCall("source", ("erp", "clients"), 7),
    ]


def test_find_calls_ignores_plain_sql() -> None:
    assert find_calls("select ref(x) from t -- ref('y')") == []
