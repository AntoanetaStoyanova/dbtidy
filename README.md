# dbtidy

Linter et convertisseur de projets dbt sur Oracle, attentif aux couches.

## Auteur

Antoaneta Stoyanova

## Prérequis

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)
- [cruft](https://cruft.github.io/cruft/) — pour mettre à jour le template

## Installation

```bash
git clone https://github.com/antoanetastoyanova/dbtidy.git
cd dbtidy
uv sync
```

## Utilisation

```bash
uv run dbtidy check            # analyse models/
uv run dbtidy check chemin/vers/models --json
```

Codes de sortie : `0` conforme, `1` violation, `2` erreur (chemin introuvable, SQL non analysable).

### Règles

| Code | Règle |
| --- | --- |
| STG001 | Un modèle staging ne lit qu'une seule source |
| STG002 | Pas de jointure dans le staging |
| STG003 | Pas d'agrégation dans le staging (`GROUP BY`, `SUM`, `COUNT`, `DISTINCT`…) |
| STG004 | Le staging lit une source, pas un autre modèle (`ref()`) |
| ORA001 | Jointure Oracle `(+)`, toutes couches |

La couche est déduite du préfixe du fichier : `stg_` (staging), `int_` (intermediate), `fct_` / `dim_` (mart).
Pour ignorer une règle sur une ligne : `-- noqa: STG002` (ou `-- noqa` pour toutes).

### Exemple de sortie

Sur [`examples/jaffle_shop_oracle`](examples/jaffle_shop_oracle), le projet jaffle_shop réécrit en Oracle legacy :

```text
$ uv run dbtidy check examples/jaffle_shop_oracle/models
examples/jaffle_shop_oracle/models/marts/dim_customers.sql:28: ORA001 Jointure Oracle (+) sur co.customer_id (+).
    → Réécrivez-la en LEFT JOIN ... ON ... (syntaxe ANSI), plus lisible et portable.
examples/jaffle_shop_oracle/models/staging/stg_payments.sql:4: STG003 Agrégation (SUM) dans un modèle staging.
    → Gardez le grain de la source en staging et agrégez dans un modèle intermediate (int_) ou mart (fct_).
[...]
examples/jaffle_shop_oracle/models/staging/stg_payments.sql:9: STG001 Le modèle staging lit 2 sources (jaffle.raw_payments, jaffle.raw_orders).
    → Créez un modèle staging par source, puis combinez-les dans un modèle intermediate (int_).
examples/jaffle_shop_oracle/models/staging/stg_payments.sql:9: STG002 Jointure avec source('jaffle.raw_orders') dans un modèle staging.
    → Déplacez la jointure dans un modèle intermediate (int_) ; le staging se limite à renommer, typer et nettoyer une source.
examples/jaffle_shop_oracle/models/staging/stg_payments.sql:10: ORA001 Jointure Oracle (+) sur o.id (+).
    → Réécrivez-la en LEFT JOIN ... ON ... (syntaxe ANSI), plus lisible et portable.
examples/jaffle_shop_oracle/models/staging/stg_payments.sql:11: STG003 Agrégation (GROUP BY) dans un modèle staging.
    → Gardez le grain de la source en staging et agrégez dans un modèle intermediate (int_) ou mart (fct_).

5 fichier(s) analysé(s), 10 violation(s), 0 erreur(s).
```

Avec `--json`, la même information sort sous forme d'objet (`files`, `violations`, `errors`, `exit_code`) pour la CI.

## Mettre à jour depuis le template

```bash
cruft update
```
