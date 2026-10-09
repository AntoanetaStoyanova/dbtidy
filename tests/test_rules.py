from pathlib import Path
from typing import Literal

import pytest

from dbtidy.bin.check import check_file
from dbtidy.config import Config, OracleConfig, Severity
from tests.conftest import WriteModel

CLEAN_STAGING = """select
    id as client_id,
    coalesce(nom, 'inconnu') as nom,
    row_number() over (partition by id order by maj desc) as rang
from {{ source('erp', 'clients') }}
"""


def codes(write_model: WriteModel, name: str, sql: str) -> list[tuple[str, int]]:
    return [(v.code, v.line) for v in check_file(write_model(name, sql), Config())]


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
    (violation,) = check_file(write_model("stg_clients.sql", sql), Config())
    assert (violation.code, violation.line) == ("STG002", 4)
    assert "pays" in violation.message


def test_stg002_names_the_dbt_target(write_model: WriteModel) -> None:
    sql = """select *
from {{ source('erp', 'clients') }} c
join {{ source('erp', 'pays') }} p on p.code = c.pays
"""
    violations = check_file(write_model("stg_clients.sql", sql), Config())
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
    (violation,) = check_file(write_model("stg_ventes.sql", sql), Config())
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


def test_stg003_incremental_filter_on_this_is_fine(write_model: WriteModel) -> None:
    sql = """{{ config(materialized='incremental') }}
select id, date_maj
from {{ source('erp', 'produits') }}
{% if is_incremental() %}
where date_maj > (select max(date_maj) from {{this}})
{% endif %}
"""
    assert codes(write_model, "stg_produits.sql", sql) == []


def test_stg003_aggregation_outside_this_subquery_still_flagged(
    write_model: WriteModel,
) -> None:
    sql = """select count(*) as n
from {{ source('erp', 'produits') }}
where date_maj > (select max(date_maj) from {{ this }})
"""
    assert codes(write_model, "stg_produits.sql", sql) == [("STG003", 1)]


def test_stg004_ref_in_staging(write_model: WriteModel) -> None:
    sql = "select *\nfrom {{ ref('stg_clients') }}\n"
    (violation,) = check_file(write_model("stg_clients_actifs.sql", sql), Config())
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
    (violation,) = check_file(write_model("fct_ventes.sql", sql), Config())
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


def test_ora002_nvl_is_a_warning(write_model: WriteModel) -> None:
    sql = "select\n    nvl(c.nom, 'inconnu') as nom\nfrom {{ ref('stg_clients') }} c\n"
    (violation,) = check_file(write_model("int_clients.sql", sql), Config())
    assert (violation.code, violation.line) == ("ORA002", 2)
    assert violation.severity is Severity.WARNING
    assert "COALESCE" in violation.fix


def test_ora002_coalesce_is_fine(write_model: WriteModel) -> None:
    sql = "select coalesce(c.nom, 'inconnu') as nom from {{ ref('stg_clients') }} c"
    assert codes(write_model, "int_clients.sql", sql) == []


def test_ora003_decode_is_a_warning(write_model: WriteModel) -> None:
    sql = """select
    decode(c.statut, 'A', 'actif', 'inactif') as statut
from {{ ref('stg_clients') }} c
"""
    (violation,) = check_file(write_model("int_clients.sql", sql), Config())
    assert (violation.code, violation.line) == ("ORA003", 2)
    assert violation.severity is Severity.WARNING
    assert "CASE" in violation.fix


def test_ora003_case_is_fine(write_model: WriteModel) -> None:
    sql = """select case when c.statut = 'A' then 'actif' else 'inactif' end as statut
from {{ ref('stg_clients') }} c
"""
    assert codes(write_model, "int_clients.sql", sql) == []


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("c.nom = ''", "IS NULL"),
        ("c.nom <> ''", "IS NOT NULL"),
        ("c.nom != ''", "IS NOT NULL"),
        ("'' = c.nom", "IS NULL"),
    ],
)
def test_ora004_empty_string(
    write_model: WriteModel, condition: str, expected: str
) -> None:
    sql = f"select c.id\nfrom {{{{ ref('stg_clients') }}}} c\nwhere {condition}\n"
    (violation,) = check_file(write_model("int_clients.sql", sql), Config())
    assert (violation.code, violation.line) == ("ORA004", 3)
    assert violation.severity is Severity.ERROR
    assert expected in violation.fix


def test_ora004_both_sides_empty(write_model: WriteModel) -> None:
    sql = "select c.id from {{ ref('stg_clients') }} c where '' = ''"
    (violation,) = check_file(write_model("int_clients.sql", sql), Config())
    assert violation.code == "ORA004"
    assert violation.fix == "Écrivez '' IS NULL."


def test_ora004_is_null_is_fine(write_model: WriteModel) -> None:
    sql = "select c.id from {{ ref('stg_clients') }} c where c.nom is null"
    assert codes(write_model, "int_clients.sql", sql) == []


LONG_NAMES = """with clients_actifs_avec_commandes_recentes as (
    select c.id as identifiant_client_dans_le_referentiel,
        c.date_de_derniere_modification_fiche
    from {{ ref('stg_clients') }} c
)
select a.identifiant_client_dans_le_referentiel
from clients_actifs_avec_commandes_recentes a
"""


def test_ora005_names_longer_than_30(write_model: WriteModel) -> None:
    found = check_file(write_model("int_clients.sql", LONG_NAMES), Config())
    assert {(v.code, v.line) for v in found} == {
        ("ORA005", 1),
        ("ORA005", 2),
        ("ORA005", 3),
    }
    assert all(v.severity is Severity.WARNING for v in found)
    assert "30" in found[0].message


def test_ora005_limit_128(write_model: WriteModel) -> None:
    config = Config(oracle=OracleConfig(max_identifier_length=128))
    assert check_file(write_model("int_clients.sql", LONG_NAMES), config) == []


def test_ora005_ignores_jinja_fake_names(write_model: WriteModel) -> None:
    sql = """select s.id
from {{ source('erp_referentiel_commercial', 'clients_actifs_historises') }} s
"""
    assert codes(write_model, "stg_clients.sql", sql) == []


@pytest.fixture
def in_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


STAGING_SQL = "select c.id from {{ source('erp', 'clients') }} c"


@pytest.mark.usefixtures("in_project")
def test_nam001_prefix_of_another_layer(write_model: WriteModel) -> None:
    sql = "select c.id from {{ ref('stg_clients') }} c"
    (violation,) = check_file(write_model("staging/int_x.sql", sql), Config())
    assert (violation.code, violation.line) == ("NAM001", 1)
    assert "couche intermediate" in violation.message
    assert "stg_" in violation.fix


@pytest.mark.usefixtures("in_project")
def test_nam001_unknown_prefix_in_layer_folder(write_model: WriteModel) -> None:
    sql = "select c.id from {{ ref('stg_clients') }} c"
    (violation,) = check_file(write_model("marts/clients.sql", sql), Config())
    assert violation.code == "NAM001"
    assert "aucune couche" in violation.message
    assert "fct_, dim_" in violation.fix


@pytest.mark.usefixtures("in_project")
def test_nam001_matching_prefix_is_fine(write_model: WriteModel) -> None:
    assert codes(write_model, "staging/stg_x.sql", STAGING_SQL) == []


@pytest.mark.usefixtures("in_project")
def test_nam001_subfolder_of_layer(write_model: WriteModel) -> None:
    assert codes(write_model, "staging/erp/stg_x.sql", STAGING_SQL) == []
    assert codes(write_model, "staging/erp/x.sql", STAGING_SQL) == [("NAM001", 1)]


@pytest.mark.usefixtures("in_project")
def test_nam001_outside_layer_folders_is_fine(write_model: WriteModel) -> None:
    assert codes(write_model, "autres/int_x.sql", STAGING_SQL) == []


CASED = """select
    c.id as client_id,
    c.nom as NOM_CLIENT,
    c.ville
from {{ ref('stg_clients') }} c
"""


def nam002(case: Literal["lower", "upper"]) -> Config:
    return Config(columns_case=case, rules={"NAM002": Severity.WARNING})


def test_nam002_lower(write_model: WriteModel) -> None:
    found = check_file(write_model("int_clients.sql", CASED), nam002("lower"))
    assert [(v.code, v.line) for v in found] == [("NAM002", 3)]
    assert "nom_client" in found[0].fix


def test_nam002_upper(write_model: WriteModel) -> None:
    found = check_file(write_model("int_clients.sql", CASED), nam002("upper"))
    assert [(v.code, v.line) for v in found] == [("NAM002", 2)]


def test_nam002_only_outer_select(write_model: WriteModel) -> None:
    sql = """with x as (select c.id as Client_Id from {{ ref('stg_clients') }} c)
select x.client_id as client_id from x
"""
    assert check_file(write_model("int_clients.sql", sql), nam002("lower")) == []


def test_nam002_off_by_default(write_model: WriteModel) -> None:
    assert codes(write_model, "int_clients.sql", CASED) == []
    config = Config(rules={"NAM002": Severity.WARNING})
    assert check_file(write_model("int_clients.sql", CASED), config) == []
