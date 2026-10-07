import pytest

from dbtidy.check import check_file
from tests.conftest import WriteModel

CLEAN_STAGING = """select
    id as client_id,
    nvl(nom, 'inconnu') as nom,
    row_number() over (partition by id order by maj desc) as rang
from {{ source('erp', 'clients') }}
"""


def codes(write_model: WriteModel, name: str, sql: str) -> list[tuple[str, int]]:
    return [(v.code, v.line) for v in check_file(write_model(name, sql))]


def test_clean_staging_has_no_violation(write_model: WriteModel) -> None:
    assert codes(write_model, "stg_clients.sql", CLEAN_STAGING) == []


def test_stg001_two_sources(write_model: WriteModel) -> None:
    sql = """select * from {{ source('erp', 'clients') }}
union all
select * from {{ source('crm', 'clients') }}
"""
    assert codes(write_model, "stg_clients.sql", sql) == [("STG001", 3)]


def test_stg001_same_source_twice_is_fine(write_model: WriteModel) -> None:
    sql = """select * from {{ source('erp', 'clients') }} where actif = 1
union all
select * from {{ source('erp', 'clients') }} where actif = 0
"""
    assert codes(write_model, "stg_clients.sql", sql) == []


def test_stg002_ansi_join(write_model: WriteModel) -> None:
    sql = """with c as (select * from {{ source('erp', 'clients') }})
select c.id
from c
left join pays p on p.code = c.pays
"""
    (violation,) = check_file(write_model("stg_clients.sql", sql))
    assert (violation.code, violation.line) == ("STG002", 4)
    assert "pays" in violation.message


def test_stg002_names_the_dbt_target(write_model: WriteModel) -> None:
    sql = """select *
from {{ source('erp', 'clients') }} c
join {{ source('erp', 'pays') }} p on p.code = c.pays
"""
    violations = check_file(write_model("stg_clients.sql", sql))
    assert "source('erp.pays')" in violations[-1].message


def test_stg002_oracle_join(write_model: WriteModel) -> None:
    sql = """select c.id
from {{ source('erp', 'clients') }} c, pays p
where c.pays = p.code(+)
"""
    assert codes(write_model, "stg_clients.sql", sql) == [
        ("STG002", 2),
        ("ORA001", 3),
    ]


def test_stg002_ignored_outside_staging(write_model: WriteModel) -> None:
    sql = "select * from {{ ref('stg_a') }} a join {{ ref('stg_b') }} b on a.id = b.id"
    assert codes(write_model, "int_ab.sql", sql) == []


@pytest.mark.parametrize(
    ("expression", "label"),
    [
        ("count(*) as n", "COUNT"),
        ("sum(montant) as total", "SUM"),
        ("distinct id", "DISTINCT"),
    ],
)
def test_stg003_aggregation(
    write_model: WriteModel, expression: str, label: str
) -> None:
    sql = f"select {expression}\nfrom {{{{ source('erp', 'ventes') }}}}\n"
    (violation,) = check_file(write_model("stg_ventes.sql", sql))
    assert (violation.code, violation.line) == ("STG003", 1)
    assert label in violation.message


def test_stg003_group_by(write_model: WriteModel) -> None:
    sql = """select client_id
from {{ source('erp', 'ventes') }}
group by
    client_id
"""
    assert codes(write_model, "stg_ventes.sql", sql) == [("STG003", 4)]


def test_stg003_window_function_is_fine(write_model: WriteModel) -> None:
    sql = """select sum(montant) over (partition by client_id) as cumul
from {{ source('erp', 'ventes') }}
"""
    assert codes(write_model, "stg_ventes.sql", sql) == []


def test_stg004_ref_in_staging(write_model: WriteModel) -> None:
    sql = "select *\nfrom {{ ref('stg_clients') }}\n"
    (violation,) = check_file(write_model("stg_clients_actifs.sql", sql))
    assert (violation.code, violation.line) == ("STG004", 2)
    assert "stg_clients" in violation.message


def test_stg004_ref_nested_in_macro(write_model: WriteModel) -> None:
    sql = """select
    {{ dbt_utils.star(ref('stg_clients')) }}
from {{ source('erp', 'clients') }}
"""
    assert codes(write_model, "stg_clients.sql", sql) == [("STG004", 2)]


def test_ora001_any_layer(write_model: WriteModel) -> None:
    sql = """select c.id, p.libelle
from {{ ref('stg_clients') }} c, {{ ref('stg_pays') }} p
where c.pays = p.code(+)
"""
    (violation,) = check_file(write_model("fct_ventes.sql", sql))
    assert (violation.code, violation.line) == ("ORA001", 3)
    assert "LEFT JOIN" in violation.fix


def test_ora001_ansi_join_is_fine(write_model: WriteModel) -> None:
    sql = """select c.id, p.libelle
from {{ ref('stg_clients') }} c
left join {{ ref('stg_pays') }} p on c.pays = p.code
"""
    assert codes(write_model, "dim_clients.sql", sql) == []


def test_unknown_layer_only_gets_oracle_rules(write_model: WriteModel) -> None:
    sql = "select count(*) from {{ ref('a') }} a join {{ ref('b') }} b on a.id = b.id"
    assert codes(write_model, "clients.sql", sql) == []
