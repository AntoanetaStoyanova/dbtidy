from pathlib import Path

from dbtidy.check import run_check

MODELS = Path(__file__).parents[1] / "examples" / "jaffle_shop_oracle" / "models"


def test_check_on_jaffle_shop_oracle() -> None:
    report = run_check([MODELS])
    found = [(v.path.name, v.line, v.code) for v in report.violations]
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
