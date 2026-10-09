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
pip install dbtidy
dbtidy --version
```

Documentation : <https://antoanetastoyanova.github.io/dbtidy/>. Évolutions : [CHANGELOG.md](CHANGELOG.md).

Pour développer :

```bash
git clone https://github.com/AntoanetaStoyanova/dbtidy.git
cd dbtidy
uv sync
```

## Utilisation

```bash
uv run dbtidy check            # analyse models/
uv run dbtidy check chemin/vers/models --json
uv run dbtidy check --config conventions.yml
uv run dbtidy validate-config  # valide dbtidy.yml sans analyser de modèle
```

Codes de sortie : `0` conforme, `1` violation de sévérité `error`, `2` erreur (chemin introuvable, configuration invalide, SQL non analysable).

### Configuration

`dbtidy.yml` est lu dans le répertoire courant, ou depuis `--config`. Sans fichier, les valeurs par défaut ci-dessous s'appliquent ; un fichier partiel les complète.

```yaml
layers:                      # chemins relatifs au fichier de configuration
  staging:
    path: models/staging
    prefixes: [stg_]
  intermediate:
    path: models/intermediate
    prefixes: [int_]
  mart:
    path: models/marts
    prefixes: [fct_, dim_]
columns_case: null           # lower, upper ou null
oracle:
  max_identifier_length: 30
rules:                       # error (exit 1), warning (affiché, exit 0) ou off
  STG001: error
  STG002: error
  STG003: error
  STG004: error
  ORA001: error
  ORA002: warning
  ORA003: warning
  ORA004: error
  ORA005: warning
  NAM001: error
  NAM002: off
```

Une clé, une sévérité ou un code de règle inconnu est une erreur (exit 2), avec la clé fautive dans le message. `dbtidy validate-config [PATH]` (défaut `dbtidy.yml`) fait la même vérification seule : exit 0 si le fichier est valide, exit 2 s'il est invalide ou absent.

### Règles

| Code | Règle |
| --- | --- |
| STG001 | Un modèle staging ne lit qu'une seule source |
| STG002 | Pas de jointure dans le staging |
| STG003 | Pas d'agrégation dans le staging (`GROUP BY`, `SUM`, `COUNT`, `DISTINCT`…), hors fonctions analytiques et filtre incrémental sur `{{ this }}` |
| STG004 | Le staging lit une source, pas un autre modèle (`ref()`) |
| ORA001 | Jointure Oracle `(+)`, toutes couches |
| ORA002 | `NVL` à remplacer par `COALESCE` |
| ORA003 | `DECODE` à remplacer par `CASE` |
| ORA004 | Comparaison à `''` (`=`, `<>`, `!=`), qu'Oracle traite comme `NULL` : utiliser `IS NULL` / `IS NOT NULL` |
| ORA005 | Alias, CTE ou colonne plus long que `oracle.max_identifier_length` (noms factices de `ref()`/`source()` exclus) |
| NAM001 | Fichier rangé dans le dossier d'une couche (`layers.*.path`) sans en avoir le préfixe |
| NAM002 | Alias du `SELECT` externe dans une casse différente de `columns_case` (inactive si `null`) |

La couche est déduite du préfixe du fichier, défini par `layers.*.prefixes` dans la configuration ; le dossier ne sert qu'à NAM001.
Pour ignorer une règle sur une ligne : `-- noqa: STG002` (ou `-- noqa` pour toutes) ; un texte libre peut suivre les codes.

### Exemple de sortie

Sur [`examples/jaffle_shop_oracle`](examples/jaffle_shop_oracle), le projet jaffle_shop réécrit en Oracle legacy :

```text
$ uv run dbtidy check examples/jaffle_shop_oracle/models
examples/jaffle_shop_oracle/models/marts/dim_customers.sql:25: ORA002 [warning] NVL dans NVL(co.number_of_orders, 0).
    → Remplacez NVL par COALESCE (norme ANSI, accepte plus de deux arguments).
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

5 fichier(s) analysé(s), 10 violation(s), 12 avertissement(s), 0 erreur(s).
```

Avec `--json`, la même information sort sous forme d'objet (`files`, `violations` avec leur `severity`, `errors`, `exit_code`) pour la CI.

### Deux configurations sur jaffle_shop

`examples/jaffle_shop_oracle/` contient deux configurations à comparer :

```bash
uv run dbtidy check examples/jaffle_shop_oracle/models --config examples/jaffle_shop_oracle/dbtidy.yml          # stricte : 22 violations, exit 1
uv run dbtidy check examples/jaffle_shop_oracle/models --config examples/jaffle_shop_oracle/dbtidy.lenient.yml  # tolérante : 22 avertissements, exit 0
```

### Hook pre-commit

```yaml
repos:
  - repo: https://github.com/AntoanetaStoyanova/dbtidy
    rev: v0.2.0
    hooks:
      - id: dbtidy
```

Le hook lance `dbtidy check` sur les fichiers `.sql` modifiés, avec le `dbtidy.yml` de la racine du dépôt s'il existe.

## Mettre à jour depuis le template

```bash
cruft update
```
