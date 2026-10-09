import json
from importlib.metadata import version
from pathlib import Path

import pytest

from dbtidy.__main__ import main
from dbtidy.bin.check import (
    check_file,
    collect_files,
    format_json,
    format_text,
    run_check,
)
from dbtidy.bin.layers import Layer, layer_of
from dbtidy.config import Config, Severity
from tests.conftest import WriteModel

JOIN_STAGING = """select c.id
from {{ source('erp', 'clients') }} c
join pays p on p.code = c.pays
"""


def test_noqa_disables_one_code(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa: STG002\n")
    assert check_file(write_model("stg_clients.sql", sql), Config()) == []


def test_noqa_other_code_keeps_violation(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa: ORA001, STG003\n")
    assert [
        v.code for v in check_file(write_model("stg_clients.sql", sql), Config())
    ] == ["STG002"]


def test_bare_noqa_disables_all(write_model: WriteModel) -> None:
    sql = JOIN_STAGING.replace("c.pays\n", "c.pays  -- noqa\n")
    assert check_file(write_model("stg_clients.sql", sql), Config()) == []


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
        "severity": "error",
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


SRC_STAGING = Config.model_validate(
    {"layers": {"staging": {"path": "models/staging", "prefixes": ["src_"]}}}
)


def test_custom_prefix_triggers_staging_rules(write_model: WriteModel) -> None:
    path = write_model("src_clients.sql", JOIN_STAGING)
    assert [v.code for v in check_file(path, SRC_STAGING)] == ["STG002"]


def test_prefix_removed_from_config_is_unknown(write_model: WriteModel) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    assert check_file(path, SRC_STAGING) == []


def test_undeclared_prefix_is_unknown() -> None:
    assert layer_of(Path("models/dbt_clients.sql"), Config()) is Layer.UNKNOWN


def test_cli_config_option_applies(
    write_model: WriteModel, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_model("src_clients.sql", JOIN_STAGING)
    config = tmp_path / "conf.yml"
    config.write_text("layers:\n  staging:\n    prefixes: [src_]\n", encoding="utf-8")
    assert main(["check", str(path), "--config", str(config)]) == 1
    assert "STG002" in capsys.readouterr().out


def test_cli_reads_dbtidy_yml_from_cwd(
    write_model: WriteModel,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = write_model("src_clients.sql", JOIN_STAGING)
    (tmp_path / "dbtidy.yml").write_text(
        "layers:\n  staging:\n    prefixes: [src_]\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert main(["check", str(path)]) == 1
    capsys.readouterr()


def test_cli_invalid_config_exits_2(
    write_model: WriteModel, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    config = tmp_path / "conf.yml"
    config.write_text("rules:\n  STG002: fatal\n", encoding="utf-8")
    assert main(["check", str(path), "--config", str(config)]) == 2
    captured = capsys.readouterr()
    assert "rules.STG002" in captured.err
    assert captured.out == ""


# STG002 ligne 3, STG003 ligne 1.
JOIN_AND_DISTINCT = JOIN_STAGING.replace("select c.id", "select distinct c.id")


def _with_rules(**rules: str) -> Config:
    return Config.model_validate({"rules": rules})


def test_off_rule_not_reported(write_model: WriteModel) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    assert check_file(path, _with_rules(STG002="off")) == []


def test_severity_attached_to_violation(write_model: WriteModel) -> None:
    path = write_model("stg_clients.sql", JOIN_AND_DISTINCT)
    violations = check_file(path, _with_rules(STG003="warning"))
    assert [(v.code, v.severity) for v in violations] == [
        ("STG003", Severity.WARNING),
        ("STG002", Severity.ERROR),
    ]


def test_warning_only_exits_0(
    write_model: WriteModel, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_model("stg_clients.sql", JOIN_STAGING)
    report = run_check([path], _with_rules(STG002="warning"))
    assert report.exit_code == 0
    text = format_text(report)
    assert f"{path}:3: STG002 [warning] Jointure" in text
    assert "0 violation(s), 1 avertissement(s), 0 erreur(s)." in text


def test_warning_and_error_exits_1(write_model: WriteModel) -> None:
    path = write_model("stg_clients.sql", JOIN_AND_DISTINCT)
    report = run_check([path], _with_rules(STG003="warning"))
    assert report.exit_code == 1
    text = format_text(report)
    assert f"{path}:3: STG002 Jointure" in text
    assert "1 violation(s), 1 avertissement(s), 0 erreur(s)." in text


def test_json_contains_severity(write_model: WriteModel) -> None:
    path = write_model("stg_clients.sql", JOIN_AND_DISTINCT)
    payload = json.loads(format_json(run_check([path], _with_rules(STG003="warning"))))
    assert [v["severity"] for v in payload["violations"]] == ["warning", "error"]
    assert payload["exit_code"] == 1


def test_cli_version_follows_package_metadata(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == version("dbtidy")
