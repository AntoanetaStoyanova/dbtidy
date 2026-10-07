# Plan — Phase 0 : Étude et fondations

*Rédigé le : 7 octobre 2026*
*Référence : [roadmap-sql-oracle-dbt.md](../specs/roadmap-sql-oracle-dbt.md)*

## Objectif

Lever le risque technique principal (`sqlglot` sur du SQL Oracle + Jinja dbt) et avoir un dépôt propre avant d'écrire la première règle `check`. Durée indicative : 2 à 3 semaines.

## Décisions prises (issues de la discussion de cadrage)

Ces décisions corrigent ou précisent la roadmap et s'appliquent à partir de maintenant :

| Sujet | Décision | Pourquoi |
| --- | --- | --- |
| Nom du projet | `dbtidy`, définitif (plus "à définir") | Déjà le nom du dépôt et du package |
| Documentation | Sphinx + `furo` | Déjà en place via le template cruft, pas `mkdocs-material` |
| Licence | MIT | Permissive, standard pour un outil CLI open source perso |
| Classification de couche (v0.1) | Par **préfixe** (`stg_`, `int_`, `fct_`, `dim_`), codé en dur | Les préfixes sont une convention dbt publique (Kimball), pas un jargon métier confidentiel. Le dossier (`models/staging/`, etc.) sert de vérification secondaire, pas de critère principal — évite l'ambiguïté dossier vs préfixe |
| Sévérité et code de sortie | Seul un code `error` fait échouer la CI (exit 1). Un `warning` s'affiche mais exit 0 | Évite une incohérence quand la sévérité (v0.2) sera introduite après le code de sortie (v0.1) |
| Portée de `-- noqa: CODE` | Ligne courante uniquement | Convention `sqlfluff`, plus précis qu'une désactivation fichier entier |
| Mapping schéma Oracle (`convert`, v0.3) | Flag CLI ou fichier de mapping, pas d'inférence depuis le SQL seul | Une requête legacy ne contient pas le nom de schéma/base cible |

## Tâches

- [ ] Valider l'idée avec le tuteur (projet open source perso, utilisable ensuite par l'équipe)
- [x] Vérifier la disponibilité du nom `dbtidy` sur PyPI
- [x] Ajouter un fichier `LICENSE` (MIT) et le champ `license` dans `pyproject.toml`
- [x] Tester `sqlglot` (dialecte `oracle`) sur 10 à 15 requêtes Oracle typiques : jointures `(+)`, `NVL`, `DECODE`, `ROWNUM`, `CONNECT BY`, `MERGE`
- [x] Tester le parsing d'un modèle dbt contenant du Jinja (`{{ ref() }}`, `{{ source() }}`) après remplacement par des noms factices — vérifier que la substitution préserve les numéros de ligne (même longueur de texte ou padding), sinon les messages d'erreur de `check` pointeront sur la mauvaise ligne
- [x] Lire les règles de `dbt-project-evaluator` et noter celles à reprendre ou à écarter
- [x] Lister les conventions de nommage génériques retenues pour v0.1 : préfixes `stg_` / `int_` / `fct_` / `dim_`, sans rien de confidentiel
- [x] Créer la structure `src/`, `tests/`, `pyproject.toml` (déjà fait via cruft — vérifier que rien ne manque)
- [x] Mettre en place pre-commit (ruff, mypy, pytest)
- [x] Mettre en place la CI GitHub Actions (ruff, mypy, pytest)

## Résultats

### Nom PyPI

`dbtidy` est libre au 7 octobre 2026 (`https://pypi.org/pypi/dbtidy/json` renvoie 404). Le nom n'est pas réservé tant que rien n'est publié.

### `sqlglot` sur Oracle — `docs/spikes/sqlglot_oracle.py`

`sqlglot` 30.21, 15/15 requêtes parsées : `(+)`, `NVL`, `NVL2`, `DECODE`, `ROWNUM`, `CONNECT BY`, `MERGE`, `SYSDATE`, `TO_DATE`, schéma.table, `HAVING`, fonctions analytiques, `WITH`, hints, `FETCH FIRST`.

- `(+)` : porté par `exp.Column` avec `args["join_mark"] = True` → ORA001 est une simple recherche dans l'AST. La génération vers un autre dialecte émet un warning « Outer join syntax using the (+) operator is not supported ».
- Une jointure par virgule (`FROM a, b`) produit un `exp.Join` → STG002 la détecte sans traitement particulier.
- Les noms de CTE ressortent comme `exp.Table` : il faut les exclure en croisant avec les `exp.CTE` du modèle.
- Les agrégations sont des sous-classes de `exp.AggFunc` (STG003). Les fonctions analytiques (`ROW_NUMBER`) n'en sont pas.
- Les numéros de ligne et de colonne sont sur `exp.Identifier.meta` (`line`, `col`), pas sur `exp.Column`.
- Le round-trip n'est pas identique au texte : `TRUNC(SYSDATE)` → `TRUNC(SYSDATE, 'DD')`, les commentaires `--` deviennent `/* */`. À prendre en compte pour `convert`.
- Le PL/SQL (`BEGIN … END;`) n'est pas parsé : `ParseError`.

### Jinja dbt — `docs/spikes/jinja_substitution.py`

Stratégie validée, numéros de ligne et de colonne préservés :

- `{{ ref('x') }}` / `{{ source('a', 'b') }}` → identifiant factice (`ref__x`, `source__a__b`) complété par des espaces jusqu'à la longueur d'origine. Le factice est toujours plus court que l'appel Jinja.
- `{% … %}`, `{# … #}` et `{{ config(…) }}` → remplacés par des espaces, sauts de ligne conservés. Un `{{ config() }}` remplacé par un identifiant casse le parsing.
- Les autres `{{ … }}` → `__jinja_expr` complété par des espaces (utilisable en position d'expression).

Limites, à traiter en v0.1 :

- Un `ref()` imbriqué dans une macro (`{{ dbt_utils.star(ref('x')) }}`) n'est pas capturé comme table. STG001 et STG004 doivent compter `ref()` / `source()` par regex sur le texte brut, pas dans l'AST.
- `{% if %} … {% else %} … {% endif %}` : les deux branches restent, ce qui peut donner un SQL invalide. En cas de `ParseError`, signaler le modèle sans planter.

### `dbt-project-evaluator`

Source : https://dbt-labs.github.io/dbt-project-evaluator/latest/rules/

| Règle evaluator | Décision dbtidy |
| --- | --- |
| `fct_staging_dependent_on_staging` | Reprise → STG004 |
| `fct_staging_dependent_on_marts_or_intermediate` | Reprise → STG004 (toute `ref()` en staging) |
| `fct_multiple_sources_joined` | Reprise → STG001 (plus strict : une source par staging) |
| `fct_marts_or_intermediate_dependent_on_source` | Candidate v0.2 (INT/MRT : pas de `source()`) |
| `fct_direct_join_to_source` | Candidate v0.2 |
| `fct_model_naming_conventions` | Reprise → classification par préfixe |
| `fct_hard_coded_references` | Candidate v0.2 (`schema.table` en dur au lieu de `ref`/`source`), utile pour du legacy Oracle |
| `fct_too_many_joins` | Candidate v0.2, seuil configurable |
| `fct_model_directories` | Vérification secondaire (dossier vs préfixe) |
| Fanout, `fct_rejoining_of_upstream_concepts`, `fct_root_models`, `fct_unused_sources`, `fct_duplicate_sources` | Écartées : nécessitent le DAG complet (manifest), hors périmètre d'un linter fichier par fichier |
| Tests, documentation, performance, gouvernance | Écartées : relèvent des YAML / du manifest, pas du SQL |

Ce qu'apporte dbtidy en plus : les règles sur la syntaxe Oracle (ORA*) et les règles internes au SQL (jointures et agrégations en staging), qu'evaluator ne voit pas (il travaille sur le graphe, pas sur le SQL).

### Conventions de nommage v0.1

| Préfixe | Couche | Dossier attendu (vérification secondaire) |
| --- | --- | --- |
| `stg_` | staging | `models/staging/` |
| `int_` | intermediate | `models/intermediate/` |
| `fct_` | mart (faits) | `models/marts/` |
| `dim_` | mart (dimensions) | `models/marts/` |

Un modèle sans préfixe connu : couche inconnue, aucune règle de couche appliquée.

### Structure et outillage

Correctifs appliqués au projet généré (à reporter dans `python-project-template` pour que `cruft update` ne les réintroduise pas) :

- `.gitignore` ignorait `src/dbtidy/log/` et `src/dbtidy/config/` : ces paquets n'étaient pas versionnés, alors que `__main__.py` importe `dbtidy.log`. Remplacé par `*.log`.
- Packaging : `where = ["."]` + `include = ["src*"]` exposait `src.dbtidy`. Remplacé par `where = ["src"]` ; pytest `pythonpath = ["src"]`.
- `setuptools>=77` requis pour `license = "MIT"` (PEP 639).
- `uv.lock` est ignoré par le template : la CI fait `uv sync` sans `--locked`.

pre-commit : ruff format, ruff check et mypy au commit, pytest au push. Installation : `uv run pre-commit install --hook-type pre-commit --hook-type pre-push`.

## Terminé quand

- Un script de 20 lignes parse une requête Oracle legacy et affiche ses tables, jointures et agrégations.
- La CI est verte.
- Le fichier `LICENSE` est présent et référencé dans `pyproject.toml`.
- Les décisions ci-dessus sont reportées dans la roadmap (`docs/specs/roadmap-sql-oracle-dbt.md`).

## Hors scope

- Toute logique de `check`, `convert` ou `explain` (voir les plans v0.1+ à venir).
