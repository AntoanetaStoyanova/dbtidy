from pathlib import Path

import pytest

from dbtidy.__main__ import main
from dbtidy.config import Config, ConfigError, Severity, load_config

FULL = """layers:
  staging:
    path: sql/stg
    prefixes: [src_]
  intermediate:
    path: sql/int
    prefixes: [int_, tmp_]
  mart:
    path: sql/mart
    prefixes: [fct_]
columns_case: lower
oracle:
  max_identifier_length: 128
rules:
  STG001: error
  STG002: warning
  STG003: off
  STG004: error
  ORA001: warning
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "dbtidy.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_defaults_reproduce_v01() -> None:
    config = Config()
    assert config.layers.staging.prefixes == ["stg_"]
    assert config.layers.intermediate.prefixes == ["int_"]
    assert config.layers.mart.prefixes == ["fct_", "dim_"]
    assert config.columns_case is None
    assert config.oracle.max_identifier_length == 30
    v01 = ["STG001", "STG002", "STG003", "STG004", "ORA001"]
    assert {config.rules[code] for code in v01} == {Severity.ERROR}


def test_full_file(tmp_path: Path) -> None:
    config = load_config(_write(tmp_path, FULL))
    assert config.layers.staging.path == tmp_path / "sql/stg"
    assert config.layers.intermediate.prefixes == ["int_", "tmp_"]
    assert config.columns_case == "lower"
    assert config.oracle.max_identifier_length == 128
    assert config.rules["STG003"] is Severity.OFF
    assert config.rules["ORA001"] is Severity.WARNING


def test_partial_file_merged_with_defaults(tmp_path: Path) -> None:
    content = "layers:\n  staging:\n    prefixes: [src_]\nrules:\n  STG002: off\n"
    config = load_config(_write(tmp_path, content))
    assert config.layers.staging.prefixes == ["src_"]
    assert config.layers.staging.path == tmp_path / "models/staging"
    assert config.layers.mart.prefixes == ["fct_", "dim_"]
    assert config.rules["STG002"] is Severity.OFF
    assert config.rules["STG001"] is Severity.ERROR


def test_empty_file_gives_defaults(tmp_path: Path) -> None:
    assert load_config(_write(tmp_path, "")).rules == Config().rules


def test_absolute_layer_path_kept(tmp_path: Path) -> None:
    absolute = tmp_path / "ailleurs"
    content = f"layers:\n  staging:\n    path: {absolute.as_posix()}\n"
    assert load_config(_write(tmp_path, content)).layers.staging.path == absolute


def test_cwd_file_used_when_no_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "rules:\n  STG004: warning\n")
    monkeypatch.chdir(tmp_path)
    config = load_config(None)
    assert config.rules["STG004"] is Severity.WARNING
    assert config.layers.staging.path == tmp_path / "models/staging"


def test_missing_cwd_file_gives_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_config(None) == Config()


def test_missing_explicit_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="introuvable"):
        load_config(tmp_path / "absent.yml")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("colonnes: lower\n", "colonnes"),
        ("layers:\n  staging:\n    prefix: stg_\n", r"layers\.staging\.prefix"),
        ("layers:\n  raw:\n    prefixes: [raw_]\n", r"layers\.raw"),
        ("rules:\n  STG002: fatal\n", r"rules\.STG002"),
        ("rules:\n  STG999: error\n", "STG999"),
        ("columns_case: camel\n", "columns_case"),
        ("oracle:\n  max_identifier_length: 0\n", "max_identifier_length"),
    ],
)
def test_invalid_config_names_key(tmp_path: Path, content: str, expected: str) -> None:
    with pytest.raises(ConfigError, match=expected):
        load_config(_write(tmp_path, content))


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="YAML invalide"):
        load_config(_write(tmp_path, "rules: [STG001\n"))


def test_non_mapping_root_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="dictionnaire"):
        load_config(_write(tmp_path, "- STG001\n"))


def test_error_message_names_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "colonnes: lower\n")
    with pytest.raises(ConfigError, match="dbtidy.yml"):
        load_config(path)


def test_validate_config_valid_exits_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate-config", str(_write(tmp_path, FULL))]) == 0
    assert "Configuration valide" in capsys.readouterr().out


def test_validate_config_default_reads_cwd_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, FULL)
    monkeypatch.chdir(tmp_path)
    assert main(["validate-config"]) == 0


def test_validate_config_invalid_exits_2_naming_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "rules:\n  STG002: fatal\n")
    assert main(["validate-config", str(path)]) == 2
    captured = capsys.readouterr()
    assert "rules.STG002" in captured.err
    assert captured.out == ""


def test_validate_config_missing_file_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate-config", str(tmp_path / "absent.yml")]) == 2
    assert "introuvable" in capsys.readouterr().err
    monkeypatch.chdir(tmp_path)
    assert main(["validate-config"]) == 2
