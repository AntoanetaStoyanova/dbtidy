from pathlib import Path

from dbtidy.bin.check import run_check
from dbtidy.config import Config, Severity, load_config

PROJECT = Path(__file__).parents[1] / "examples" / "jaffle_shop_oracle"
MODELS = PROJECT / "models"


def test_check_on_jaffle_shop_oracle() -> None:
    report = run_check([MODELS], Config())
    found = [
        (v.path.name, v.line, v.code)
        for v in report.violations
        if v.severity is Severity.ERROR
    ]
    warnings = [
        (v.path.name, v.line, v.code)
        for v in report.violations
        if v.severity is Severity.WARNING
    ]
    assert report.files == 5
    assert report.errors == []
    assert report.exit_code == 1
    assert found == [
        ("dim_customers.sql", 28, "ORA001"),
        *[("stg_payments.sql", line, "STG003") for line in range(4, 9)],
        ("stg_payments.sql", 9, "STG001"),
        ("stg_payments.sql", 9, "STG002"),
        ("stg_payments.sql", 10, "ORA001"),
        ("stg_payments.sql", 11, "STG003"),
    ]
    assert warnings == [
        ("dim_customers.sql", 25, "ORA002"),
        *[("fct_orders.sql", line, "ORA002") for line in range(6, 11)],
        ("stg_orders.sql", 7, "ORA003"),
        *[("stg_payments.sql", line, "ORA003") for line in range(4, 8)],
        ("stg_payments.sql", 8, "ORA002"),
    ]


def test_strict_and_lenient_configs_differ() -> None:
    strict = run_check([MODELS], load_config(PROJECT / "dbtidy.yml"))
    lenient = run_check([MODELS], load_config(PROJECT / "dbtidy.lenient.yml"))
    assert (strict.count(Severity.ERROR), strict.count(Severity.WARNING)) == (22, 0)
    assert (lenient.count(Severity.ERROR), lenient.count(Severity.WARNING)) == (0, 22)
    assert (strict.exit_code, lenient.exit_code) == (1, 0)
