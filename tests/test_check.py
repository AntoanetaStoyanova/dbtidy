import json
from pathlib import Path

import pytest

from dbtidy.__main__ import main
from dbtidy.check import check_file, collect_files
from tests.conftest import WriteModel

JOIN_STAGING = """select c.id
from {{ source('erp', 'clients') }} c
join pays p on p.code = c.pays
"""


def test_noqa_disables_one_code(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa: STG002\n")
    assert check_file(write_model("stg_clients.sql", sql)) == []


def test_noqa_other_code_keeps_violation(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa: ORA001, STG003\n")
    assert [v.code for v in check_file(write_model("stg_clients.sql", sql))] == [
        "STG002"
    ]


def test_bare_noqa_disables_all(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa\n")
    assert check_file(write_model("stg_clients.sql", sql)) == []


def test_collect_files_skips_generated_dirs(tmp_path: Path) -> None:
    for rel in ["models/stg_a.sql", "target/run/stg_a.sql", "models/notes.md"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("select 1", encoding="utf-8")
    assert collect_files([tmp_path]) == [tmp_path / "models" / "stg_a.sql"]


def test_cli_conforming_project_exits_0(
    write_model: WriteModel, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_model("stg_a.sql", "select id from {{ source('erp', 'a') }}")
    assert main(["check", str(path.parent)]) == 0
    assert "1 fichier(s) analysé(s), 0 violation(s)" in capsys.readouterr().out


def test_cli_violation_exits_1_with_location_and_fix(
    write_model: WriteModel, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    assert main(["check", str(path)]) == 1
    out = capsys.readouterr().out
    assert f"{path}:3: STG002 " in out
    assert "→ Déplacez la jointure" in out


def test_cli_json(write_model: WriteModel, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    assert main(["check", "--json", str(path)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == 1
    assert payload["violations"][0] | {"message": "", "fix": ""} == {
        "path": str(path),
        "line": 3,
        "code": "STG002",
        "message": "",
        "fix": "",
    }


def test_cli_parse_error_exits_2(
    write_model: WriteModel, capsys: pytest.CaptureFixture[str]
) -> None:
    ok = write_model("stg_ok.sql", JOIN_STAGING)
    write_model("stg_ko.sql", "begin dbms_output.put_line('x'); end;")
    assert main(["check", "--json", str(ok.parent)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"] == 2
    assert len(payload["violations"]) == 1
    assert payload["errors"][0]["message"].startswith("SQL non analysable")


def test_cli_missing_path_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", str(tmp_path / "absent")]) == 2
    assert "Chemin introuvable" in capsys.readouterr().err
