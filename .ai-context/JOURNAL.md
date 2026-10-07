# Journal — dbtidy

<!--
  **Usage — Claude Code** : ce fichier trace l'avancement du projet session par session —
  ce qui a été fait et ce qu'il reste à faire. Contrairement à `CURRENT.md` (état du code
  au moment d'une review), ce journal suit les décisions, les documents créés et les étapes
  franchies. Ajoute une entrée en haut (sous ce bloc) à chaque session de travail
  significative. Ne supprime pas les entrées précédentes.

  Format d'une entrée :

  ## [YYYY-MM-DD] — <titre court de la session>
  ### Fait
  ### Reste à faire
  ### Références
-->

---

## [2026-10-07] — Phase 0 + v0.1 terminée, plan v0.2 rédigé

### Fait

- Cadrage (matin) : revue de `docs/specs/roadmap-sql-oracle-dbt.md`, décisions actées (nom `dbtidy`, Sphinx + furo, MIT, classification par préfixe, seul `error` → exit 1, `noqa` à la ligne, mapping schéma explicite pour `convert`), plans `phase-0-fondations.md` et `v0.1-check.md` créés.
- Plan phase-0-fondations : 9 tâches sur 10 faites, résultats consignés dans la section « Résultats » du plan.
  - Nom `dbtidy` libre sur PyPI (404).
  - `LICENSE` (MIT) ; `license = "MIT"` + `license-files` dans `pyproject.toml` (`setuptools>=77`).
  - Dépendance `sqlglot>=30.21.0` ajoutée. Spike `docs/spikes/sqlglot_oracle.py` : 15/15 requêtes Oracle parsées ; `(+)` = `Column.args["join_mark"]` ; les CTE ressortent comme `exp.Table` ; numéros de ligne sur `Identifier.meta`.
  - Spike `docs/spikes/jinja_substitution.py` : substitution `ref`/`source` par des identifiants complétés par des espaces, `{% %}` et `{{ config() }}` effacés ; lignes et colonnes préservées. Limite : un `ref()` imbriqué dans une macro n'est pas vu par l'AST → STG001/STG004 compteront `ref()`/`source()` par regex sur le texte brut.
  - Règles `dbt-project-evaluator` triées (reprises, candidates v0.2, écartées car nécessitant le manifest).
  - Correctifs du template (validés par l'utilisatrice) : `.gitignore` n'ignore plus `log/` et `config/` mais `*.log` ; packaging `where = ["src"]`, pytest `pythonpath = ["src"]`.
  - `src/dbtidy/log/__init__.py` : docstrings et formatage ; `tests/test_logging.py` créé (couverture 100 %).
  - `.pre-commit-config.yaml` (ruff, mypy ; pytest en pre-push) et `.github/workflows/ci.yml` (`uv sync` + `uv run inv ci`). `pre-commit` en dépendance de dev.
- `uv run inv ci` vert en local (via `uv.exe`, le `.venv` est Windows).
- Plan v0.1-check — Étape « Tâches » : 13/15 faites (périmètre « cœur + 5 règles » choisi par l'utilisatrice).
  - `beartype` ajouté (`uv add beartype`, validé), `@beartype` sur les fonctions publiques.
  - `src/dbtidy/layers.py` (couche par préfixe), `jinja.py` (`substitute` → SQL + mapping nom factice → `JinjaCall` ; `find_calls` par regex sur le texte brut, y compris dans les macros), `rules.py` (STG001-004, ORA001), `check.py` (collecte des `.sql` hors `target/` et `dbt_packages/`, `noqa`, sorties texte/JSON), `__main__.py` (CLI argparse `dbtidy check [paths] [--json]`, défaut `models`) ; script `dbtidy` dans `[project.scripts]`.
  - Décisions : fonctions analytiques `OVER (...)` non signalées par STG003 (grain inchangé) ; STG004 signale tout `ref()` en staging ; `-- noqa` sans code désactive toutes les règles de la ligne ; un fichier non parsable n'arrête pas l'analyse mais donne exit 2 ; plus de `setup_logging` dans `main` (polluerait la sortie `--json`), test correspondant retiré ; stdout forcé en UTF-8 (console Windows cp1252).
  - Tests : `tests/conftest.py`, `test_rules.py`, `test_jinja.py`, `test_check.py` — 35 tests, couverture 99 %.
- Plan v0.1-check — 15/15, plan entièrement coché.
  - `examples/jaffle_shop_oracle/` : jaffle_shop réécrit en Oracle legacy (`(+)`, `NVL`, `DECODE`, `TO_DATE`, `TRUNC(SYSDATE)`), `stg_payments` agrège et joint deux sources comme une vue héritée, `fct_orders` montre un `-- noqa: ORA001`. `check` : 5 fichiers, 10 violations, exit 1 ; résultat figé dans `tests/test_jaffle_shop.py`.
  - `README.md` : utilisation, codes de sortie, tableau des règles, `noqa`, exemple de sortie sur jaffle_shop ; URL de clone corrigée en `github.com/antoanetastoyanova/dbtidy` (supposée d'après le user git).
  - CI locale verte : 36 tests, couverture 99 %.
- Plan v0.2 rédigé : `docs/specs/v0.2-config-pypi.md` et `docs/plans/v0.2-config-pypi.md` (8 étapes, YAML et sévérité d'abord, PyPI en dernier).
  - Décisions : `dbtidy.yml` dans le répertoire courant ou `--config` ; sans fichier, valeurs par défaut = v0.1 ; `prefixes` en liste ; chemins relatifs au fichier de config ; `extra="forbid"` (code de règle inconnu = erreur) ; config invalide → exit 2 ; sévérités `error`/`warning`/`off` (warnings par défaut : ORA002, ORA003, ORA005 ; NAM002 `off`) ; `max_identifier_length` 30 par défaut ; on reste sur argparse ; publication par trusted publishing sur tag.
  - Hors périmètre : règles candidates dbt-project-evaluator (0.2.x), couches personnalisées, typer/rich.

### Reste à faire

- Exécuter docs/plans/v0.2-config-pypi.md — Étape 1 : Modèle de configuration (après commit de v0.1 ; `uv add pydantic pyyaml` à valider).
- Phase 0 : valider l'idée avec le tuteur (seule tâche non cochée, action humaine). Vérifier que la CI GitHub passe au premier push (non poussé).
- Reporter les correctifs `.gitignore` / packaging / `setuptools>=77` dans `python-project-template`.
- Review de v0.1 (`/cr`) puis commit sur develop (pas de push pour l'instant, demande de l'utilisatrice).
- Remote `origin` invalide (`https://github.com/Antoaneta Stoyanova/dbtidy.git`, espace dans l'URL) : à corriger avant le premier push.
- Spikes `docs/spikes/` : à garder comme trace ou supprimer (logique reprise dans `src/dbtidy/jinja.py`).

### Références

- [docs/plans/phase-0-fondations.md](../docs/plans/phase-0-fondations.md)
- [docs/plans/v0.1-check.md](../docs/plans/v0.1-check.md)
- [docs/specs/v0.2-config-pypi.md](../docs/specs/v0.2-config-pypi.md), [docs/plans/v0.2-config-pypi.md](../docs/plans/v0.2-config-pypi.md)
- [docs/specs/roadmap-sql-oracle-dbt.md](../docs/specs/roadmap-sql-oracle-dbt.md)
- [docs/spikes/sqlglot_oracle.py](../docs/spikes/sqlglot_oracle.py), [docs/spikes/jinja_substitution.py](../docs/spikes/jinja_substitution.py)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml), [.pre-commit-config.yaml](../.pre-commit-config.yaml)
- [examples/jaffle_shop_oracle/](../examples/jaffle_shop_oracle/), [README.md](../README.md), [tests/test_jaffle_shop.py](../tests/test_jaffle_shop.py)
- [src/dbtidy/check.py](../src/dbtidy/check.py), [src/dbtidy/rules.py](../src/dbtidy/rules.py), [src/dbtidy/jinja.py](../src/dbtidy/jinja.py), [src/dbtidy/layers.py](../src/dbtidy/layers.py), [src/dbtidy/__main__.py](../src/dbtidy/__main__.py)

