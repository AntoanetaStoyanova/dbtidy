# jaffle_shop — version Oracle legacy

Réécriture du projet d'exemple [jaffle_shop](https://github.com/dbt-labs/jaffle_shop) dans le style
d'un code Oracle hérité : jointures `(+)`, `NVL`, `DECODE`, `TO_DATE`, et une agrégation faite
trop tôt dans le staging. Sert à valider `dbtidy check` en conditions réalistes :

```bash
uv run dbtidy check examples/jaffle_shop_oracle/models
```
