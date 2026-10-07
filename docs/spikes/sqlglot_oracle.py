"""Spike Phase 0 : robustesse de sqlglot (dialecte oracle) sur du SQL legacy."""

import sqlglot
from sqlglot import exp

QUERIES: dict[str, str] = {
    "jointure (+)": """
        SELECT c.id, o.total
        FROM clients c, commandes o
        WHERE c.id = o.client_id(+)
    """,
    "NVL": "SELECT NVL(remise, 0) AS remise FROM commandes",
    "NVL2": "SELECT NVL2(remise, 'oui', 'non') AS a_remise FROM commandes",
    "DECODE": """
        SELECT DECODE(statut, 'A', 'Actif', 'I', 'Inactif', 'Inconnu') AS lib
        FROM clients
    """,
    "ROWNUM": """
        SELECT * FROM (SELECT * FROM ventes ORDER BY montant DESC) WHERE ROWNUM <= 10
    """,
    "CONNECT BY": """
        SELECT employe_id, manager_id, LEVEL
        FROM employes
        START WITH manager_id IS NULL
        CONNECT BY PRIOR employe_id = manager_id
    """,
    "MERGE": """
        MERGE INTO cible t
        USING source s ON (t.id = s.id)
        WHEN MATCHED THEN UPDATE SET t.val = s.val
        WHEN NOT MATCHED THEN INSERT (id, val) VALUES (s.id, s.val)
    """,
    "SYSDATE / TRUNC": "SELECT TRUNC(SYSDATE) - 1 AS hier FROM dual",
    "TO_DATE / TO_CHAR": """
        SELECT TO_CHAR(TO_DATE('2024-01-31', 'YYYY-MM-DD'), 'DD/MM/YYYY') FROM dual
    """,
    "schéma.table + alias": """
        SELECT a.col1, b.col2
        FROM dwh.table_a a JOIN dwh.table_b b ON a.id = b.id
    """,
    "agrégation + HAVING": """
        SELECT region, SUM(montant) AS total, COUNT(*) AS nb
        FROM ventes GROUP BY region HAVING SUM(montant) > 1000
    """,
    "analytique": """
        SELECT id, ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY dt DESC) AS rn
        FROM commandes
    """,
    "WITH + sous-requête": """
        WITH recent AS (SELECT * FROM commandes WHERE dt > SYSDATE - 30)
        SELECT client_id, MAX(dt) FROM recent GROUP BY client_id
    """,
    "hint optimiseur": "SELECT /*+ PARALLEL(v, 4) */ * FROM ventes v",
    "FETCH FIRST": "SELECT * FROM ventes ORDER BY dt FETCH FIRST 5 ROWS ONLY",
}


def describe(sql: str) -> str:
    tree = sqlglot.parse_one(sql, dialect="oracle")
    tables = sorted({t.sql(dialect="oracle") for t in tree.find_all(exp.Table)})
    joins = len(list(tree.find_all(exp.Join)))
    aggs = sorted({type(a).__name__ for a in tree.find_all(exp.AggFunc)})
    roundtrip = tree.sql(dialect="oracle")
    return f"tables={tables} joins={joins} aggs={aggs}\n    -> {roundtrip}"


for name, sql in QUERIES.items():
    try:
        print(f"OK   {name}: {describe(sql)}")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL {name}: {type(e).__name__}: {e}")
