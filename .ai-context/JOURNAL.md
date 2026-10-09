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

## [2026-10-09] — v0.2 : configuration, règles ORA/NAM, hook pre-commit, doc et packaging

### Fait

- Session ouverte (`/workspace-init`). Constat : v0.1 déjà commitée (`0937c00`).
- Plan v0.2-config-pypi — Étape 1 : Modèle de configuration (4/4).
  - `uv add pydantic pyyaml` et `uv add --dev types-PyYAML` (validé).
  - `src/dbtidy/config/__init__.py` : `Severity`, `LayerConfig`, `LayersConfig` (`staging`, `intermediate`, `mart`), `OracleConfig`, `Config`, `DEFAULT_SEVERITY`, `KNOWN_RULES`, `ConfigError`, `load_config`.
  - `tests/test_config.py` : 18 tests.
  - Décisions :
    - les couches sont un sous-modèle à trois champs, pas un `dict` : une couche inconnue est rejetée par `extra="forbid"`, et `config` n'importe pas `layers` (évite l'import circulaire de l'étape 2) ;
    - le chemin par défaut de mart est `models/marts` (comme jaffle_shop) ;
    - fichier partiel : fusion récursive du YAML sur `Config().model_dump()` avant validation ; les chemins sont résolus par rapport au dossier du fichier via le contexte de validation pydantic (un chemin absolu est conservé) ;
    - `off` non quoté (lu `False` par YAML 1.1) est converti en `Severity.OFF` ;
    - `KNOWN_RULES` ne contient pour l'instant que les 5 codes de la v0.1 ; les suivants sont ajoutés aux étapes 5 et 6 ;
    - un `--config` explicite qui n'existe pas lève déjà `ConfigError` ; un fichier vide donne les valeurs par défaut ;
    - pas de `@beartype` sur les modèles pydantic, qui valident déjà à l'exécution.
- `uv run inv ci` vert : 55 tests, couverture 98 %.
- Plan v0.2-config-pypi — Étape 2 : Couches pilotées par la configuration (4/4).
  - `layers.py` : `PREFIXES` supprimé ; `layer_of(path, config)` parcourt `config.layers` (première couche dont un préfixe correspond, dans l'ordre staging, intermediate, mart).
  - `rules.py` : `Model.config` ; `check.py` : `check_file(path, config)` et `run_check(paths, config)`, avec `config` obligatoire (pas de valeur par défaut, les tests passent `Config()`).
  - `__main__.py` : `check --config PATH` ; sans l'option, `load_config(None)` lit `dbtidy.yml` du répertoire courant. `ConfigError` → stderr et exit 2, sans rien sur stdout.
  - Tests ajoutés dans `tests/test_check.py` : préfixe `src_`, `stg_` retiré de la config → aucune règle, `dbt_` → `UNKNOWN`, `--config`, `dbtidy.yml` du répertoire courant, config invalide → exit 2.
- `uv run inv ci` vert : 61 tests, couverture 98 %.
- Plan v0.2-config-pypi — Étape 3 : Sévérité et code de sortie (3/3).
  - `rules.py` : `Violation.severity` (défaut `error`, remplacé dans `apply_rules`) ; `RULES` devient un `dict` code → règle, ce qui permet de ne pas exécuter les règles en `off`.
  - `check.py` : `Report.count(severity)` ; exit 1 seulement si une violation `error` ; texte `CODE [warning] message` ; résumé `N violation(s), M avertissement(s), K erreur(s)` (« violation(s) » ne compte plus que les `error`) ; `severity` dans le JSON.
  - `README.md` : ligne de résumé et codes de sortie mis à jour.
  - Tests ajoutés dans `tests/test_check.py` ; `test_cli_json` attend désormais `severity`.
- `uv run inv ci` vert : 66 tests, couverture 98 %. jaffle_shop sans config : 10 violations, inchangé.
- `README.md` : option `--config`, section « Configuration » (format, valeurs par défaut, sévérités, erreurs), champ `severity` du JSON. La doc Sphinx reste pour l'étape 8.
- Déplacement des modules (correction demandée par l'utilisatrice) : `check.py`, `jinja.py`, `layers.py` et `rules.py` passent dans `src/dbtidy/bin/` (imports en `dbtidy.bin.<module>`). Convention : les modules fonctionnels vont dans `bin/`, alors que `config/` et `log/` restent à part et que `__main__.py` reste dans `src/dbtidy/`. CI verte (66 tests).
- `CONTRIBUTING.md` (projet et `python-project-template` : `{{cookiecutter.project_slug}}/CONTRIBUTING.md` et `README.md`, validé par l'utilisatrice) : `bin/` décrit comme « modules métier (fonctions) » au lieu de « scripts d'entrée CLI ». Modification non commitée dans le template.
- Session arrêtée après l'étape 3, à la demande de l'utilisatrice : il reste les étapes 4 à 8.
- Plan v0.2-config-pypi — Étape 4 : Commande `validate-config` (2/2).
  - `__main__.py` : sous-commande `validate-config [PATH]` (défaut `dbtidy.yml`) qui passe toujours le chemin à `load_config`. Un fichier absent sort donc en 2, même avec le défaut : sans fichier, il n'y a rien à valider.
  - Exit 0 avec `<chemin>: Configuration valide` sur stdout ; sinon la `ConfigError` est écrite sur stderr et la commande sort en 2.
  - `tests/test_config.py` : 4 tests (fichier valide, défaut lu dans le répertoire courant, clé citée dans le message, fichier absent explicite ou par défaut).
  - `README.md` : commande ajoutée.
- `uv run inv ci` vert : 70 tests, couverture 98 %.
- Plan v0.2-config-pypi — Étape 5 : Règles Oracle ORA002 à ORA005 (4/4).
  - Représentation sqlglot 30.21 en dialecte Oracle :
    - `NVL(a, b)` devient `exp.Coalesce` avec `args["is_nvl"] = True` ; un `COALESCE` écrit tel quel n'a pas `is_nvl` ;
    - `DECODE(...)` devient `exp.DecodeCase`, sans `meta` de ligne (on la prend sur un enfant via `_line`) ;
    - `= ''` donne `exp.EQ` et `<>` / `!=` donnent `exp.NEQ`, avec un `exp.Literal` (`is_string`, `name == ""`) d'un côté ou de l'autre.
  - `rules.py` : `ora002_nvl`, `ora003_decode`, `ora004_empty_string` (le fix propose `<expr> IS NULL` ou `IS NOT NULL`), `ora005_identifier_length`.
  - Décisions pour ORA005 :
    - on ne regarde que les identifiants dont le parent est `Alias`, `TableAlias` (CTE et alias de table) ou `Column` ; les tables du `FROM` sont ignorées, car le CTE est déjà signalé à sa définition ;
    - chaque nom est signalé une fois, à sa première ligne ;
    - les noms de `model.mapping` sont exclus.
  - `config` : sévérités par défaut ORA002, ORA003 et ORA005 en `warning`, ORA004 en `error` (spec) ; ajoutées à `KNOWN_RULES`.
  - Tests :
    - `tests/test_rules.py` : 13 tests ; `CLEAN_STAGING` passe de `nvl` à `coalesce` ;
    - `tests/test_jaffle_shop.py` : les erreurs sont inchangées par rapport à la v0.1, et 11 warnings ORA002/ORA003 sont ajoutés (critère d'acceptation) ;
    - `test_defaults_reproduce_v01` ne vérifie plus que les 5 codes de la v0.1.
  - `README.md` : tableau des règles et YAML par défaut.
- `uv run inv ci` vert : 82 tests, couverture 99 %.
- Plan v0.2-config-pypi — Étape 6 : Règles de nommage NAM001 et NAM002 (2/2).
  - `layers.py` : `folder_layer(path, config)` renvoie la couche dont le dossier contient le fichier (le plus profond l'emporte), ou `None`.
  - `rules.py` : `nam001_prefix_matches_folder` signale en ligne 1 un fichier rangé dans le dossier d'une couche qui n'en a pas le préfixe, ou qui n'a le préfixe d'aucune couche ; le fix liste les préfixes attendus. `nam002_column_case` contrôle les alias (`exp.Alias`) des `selects` de la requête externe (pour un `UNION`, la première branche).
  - `config` : NAM001 en `error`, NAM002 en `off` par défaut (spec) ; NAM002 reste aussi inactive tant que `columns_case` est nul.
  - Décision : sans fichier de configuration, les chemins de couche par défaut sont relatifs au répertoire courant, résolus avec `Path.resolve()`. Sur jaffle_shop lancé depuis la racine du dépôt, `models/staging` ne correspond donc à rien : aucun NAM001 et aucun changement. Les deux configurations sur jaffle_shop sont pour l'étape 7.
  - Tests : 9 tests ajoutés dans `tests/test_rules.py` (fixture `in_project` qui fait un `chdir` dans `tmp_path`).
  - `README.md` : règles NAM et YAML par défaut.
- `uv run inv ci` vert : 91 tests, couverture 99 %.
- Plan v0.2-config-pypi — Étape 7 : Deux configurations sur jaffle_shop et hook pre-commit (4/4).
  - `examples/jaffle_shop_oracle/dbtidy.yml` (stricte) : `columns_case: lower`, NAM002, ORA002 et ORA003 en `error` → 22 violations, exit 1. NAM002 ne trouve rien, car les alias de jaffle_shop sont déjà en minuscules.
  - `examples/jaffle_shop_oracle/dbtidy.lenient.yml` (tolérante) : STG001, STG002, STG003 et ORA001 en `warning` → 22 avertissements, exit 0. Écart au plan : avec seulement STG002 et STG003, l'exit restait à 1 (STG001 et ORA001) ; le plan a été corrigé.
  - `tests/test_jaffle_shop.py` : `test_strict_and_lenient_configs_differ` (nombre d'erreurs, de warnings et exit code).
  - `.pre-commit-hooks.yaml` : hook `dbtidy` (`entry: dbtidy check`, `language: python`, `files: \.sql$`).
  - Vérification manuelle : `uv run pre-commit try-repo . dbtidy --verbose --files <5 modèles jaffle_shop>`. L'environnement s'installe et le hook s'exécute (fichiers répartis en deux lots : 4 fichiers avec 10 violations et 7 avertissements, puis 1 fichier avec 5 avertissements) ; exit 1, attendu sans configuration. `try-repo` ignore les fichiers non suivis ; `.pre-commit-hooks.yaml` et les deux YAML d'exemple ont donc été indexés (`git add`, sans commit).
  - `README.md` : sections « Deux configurations sur jaffle_shop » et « Hook pre-commit ». URL du dépôt : `https://github.com/AntoanetaStoyanova/dbtidy` (le remote `origin` est désormais correct).
- `uv run inv ci` vert : 92 tests, couverture 99 %.
- Plan v0.2-config-pypi — Étape 8 : Documentation, CHANGELOG et publication PyPI (6/7, les actions humaines restent à l'utilisatrice, qui s'en charge).
  - Version :
    - `pyproject.toml` passe en `0.2.0` et reçoit `authors`, `keywords`, `classifiers` et `[project.urls]` ; l'URL de la doc est `https://antoanetastoyanova.github.io/dbtidy/` ;
    - `__version__` est lu avec `importlib.metadata.version("dbtidy")`, ce qui fait de `pyproject.toml` la source unique ; `docs/conf.py` utilise `release = __version__` ;
    - test `test_cli_version_follows_package_metadata` ajouté.
  - Doc Sphinx :
    - `docs/index.rst` (toctree), `docs/cli.rst`, `docs/configuration.rst` et `docs/rules.rst` (tableau des 11 règles et exemples) ;
    - les blocs de code utilisent le lexer `sql+jinja`, car `sql` lève un warning sur `{{ }}` ;
    - `sphinx-build -W` passe, et la tâche `inv docs` utilise désormais `-W`.
  - `CHANGELOG.md` (Keep a Changelog, sections 0.2.0 du 2026-10-09 et 0.1.0 du 2026-10-07).
  - `README.md` : `pip install dbtidy`, lien vers la doc et le CHANGELOG, exemple de sortie mis à jour (12 avertissements).
  - Workflows :
    - `.github/workflows/docs.yml` : build `-W` et déploiement Pages sur `main` ou à la main ;
    - `.github/workflows/publish.yml` : sur un tag `v*`, CI, vérification que le tag égale `v<__version__>`, `uv build`, puis `pypa/gh-action-pypi-publish` dans l'environnement `pypi` (trusted publishing, sans jeton).
  - Vérification locale :
    - `uv build` produit le wheel et le sdist ; le wheel ne contient que `dbtidy/` (ni `tests/` ni `docs/`), le sdist contient les tests ;
    - wheel installé dans un venv vierge : `dbtidy --version` donne `0.2.0`, et `check models` lancé depuis `examples/jaffle_shop_oracle` lit le `dbtidy.yml` local (22 violations) ; `validate-config` répond « Configuration valide ».
- `uv run inv ci` vert : 93 tests, couverture 99 %. Plan v0.2 terminé côté code ; seules les actions humaines restent.
- Docstrings passées du format Google au format NumPy (demande de l'utilisatrice) :
  - format : `"""` seul sur sa ligne, résumé à la ligne suivante ; sections `Parameters`, `Returns`, `Raises`, `Attributes` et `Examples` soulignées, avec `nom : type` repris de la signature ;
  - 20 docstrings converties par script (`ast`) dans `__main__.py`, `bin/*.py`, `config/__init__.py` et `log/__init__.py` ; les docstrings d'une ligne sont inchangées ;
  - `find_calls` contenait le modèle brut (`_summary_`) : la docstring est remplie et le doctest rétabli ;
  - `CONTRIBUTING.md` du projet : règle et exemple en NumPy ;
  - CI verte (93 tests), `sphinx-build -W` OK (napoleon lit les deux formats).
  - Même règle reportée (validé par l'utilisatrice) dans `python-project-template/{{cookiecutter.project_slug}}/CONTRIBUTING.md` (non commité), dans `~/.claude/workspace/CONTRIBUTING.md` et dans le skill `~/.claude/skills/workspace-dev/SKILL.md`.
- Doc Sphinx reconstruite :
  - `docs/api.rst` ajouté (référence de l'API générée par `automodule` sur `config`, `bin.check`, `bin.rules`, `bin.layers` et `bin.jinja`) et lié depuis `index.rst` ; l'`automodule` du template avait disparu à la réécriture de l'index ;
  - `docs/conf.py` : `default_role = "literal"`, parce que les docstrings mettent le code entre backticks simples ; sans ce réglage, `-- noqa` s'affichait « – noqa » en italique ;
  - `inv docs` (`-W`) OK, sans warning.

### Reste à faire

- Actions humaines de l'étape 8 (prises en charge par l'utilisatrice) :
  1. commiter (sur demande), puis pousser `develop` et `main` ;
  2. sur pypi.org, ajouter un « pending publisher » (dépôt `AntoanetaStoyanova/dbtidy`, workflow `publish.yml`, environnement `pypi`) ;
  3. GitHub Settings → Pages → Source : GitHub Actions ;
  4. taguer et pousser `v0.2.0` ;
  5. vérifier `pip install dbtidy` (0.2.0), puis cocher le dernier critère du plan.
- Phase 0 : valider l'idée avec le tuteur (seule tâche non cochée, action humaine). Vérifier que la CI GitHub passe au premier push (non poussé).
- Reporter les correctifs `.gitignore` / packaging / `setuptools>=77` dans `python-project-template`.
- Commit de la v0.2 (non commitée). Des modifications sans rapport sont en attente dans `.cruft.json`, `.cruftignore`, `CONTRIBUTING.md`, `docs/conf.py`, `docs/index.rst`, `src/dbtidy/__init__.py` et `tasks/__init__.py` : uniquement des fins de ligne (CRLF/LF), à ne pas inclure dans le commit.
- Spikes `docs/spikes/` : à garder comme trace ou supprimer (logique reprise dans `src/dbtidy/bin/jinja.py`).

### Références

- [docs/plans/v0.2-config-pypi.md](../docs/plans/v0.2-config-pypi.md), [docs/specs/v0.2-config-pypi.md](../docs/specs/v0.2-config-pypi.md)
- [src/dbtidy/config/__init__.py](../src/dbtidy/config/__init__.py), [tests/test_config.py](../tests/test_config.py)
- [src/dbtidy/bin/layers.py](../src/dbtidy/bin/layers.py), [src/dbtidy/bin/check.py](../src/dbtidy/bin/check.py), [src/dbtidy/__main__.py](../src/dbtidy/__main__.py), [tests/test_check.py](../tests/test_check.py), [src/dbtidy/bin/rules.py](../src/dbtidy/bin/rules.py), [README.md](../README.md)

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

