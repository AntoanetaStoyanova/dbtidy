# Feuille de route — outil SQL Oracle → dbt

*Mise à jour : 2 octobre 2026*

## Vision

Un outil en ligne de commande, déterministe et gratuit, qui aide une équipe Oracle à passer du SQL legacy à dbt sans casser l'architecture ni les standards. Nom : `dbtidy`.

**Problèmes résolus**

| Problème observé | Réponse de l'outil | Commande |
| --- | --- | --- |
| L'assistant IA met des transformations dans le staging | Règles d'architecture vérifiées dans le SQL | `check` |
| Le code généré ne respecte pas les standards | Conventions de l'équipe décrites en YAML et appliquées | `check`, `convert` |
| Migrer le SQL legacy est long et répétitif | Découpage automatique en couches + `sources.yml` | `convert` |
| Les débutants ont peur des erreurs | Erreurs dbt et Oracle expliquées en français simple | `explain` |

**Principes**

- Déterministe : même entrée, même résultat, sans LLM.
- Configurable : aucune règle de nommage codée en dur, tout passe par un fichier YAML.
- Local : aucune connexion réseau ni base de données nécessaire pour `check` et `convert`.
- Intégrable : codes de sortie clairs (0 conforme, 1 violations, 2 erreur de configuration), sortie `--json` pour la CI.
- Pensé pour les débutants : chaque message dit quoi corriger, pas seulement ce qui ne va pas.

**Différence avec dbt-project-evaluator** : il analyse le DAG et ne prend pas en charge Oracle. Cet outil analyse le contenu du SQL, fonctionne sur Oracle et ajoute la conversion et les explications.

## Stack technique

Tout est gratuit et open source ; rien ne nécessite de compte payant.

| Besoin | Outil | Pourquoi |
| --- | --- | --- |
| Gestion du projet et des dépendances | `uv` + `pyproject.toml` | Standard moderne, rapide |
| Parsing et réécriture SQL | `sqlglot` (dialecte `oracle`) | Cœur de l'outil : arbre syntaxique du SQL |
| Interface en ligne de commande | `typer` | Simple, typé, aide générée |
| Configuration | `pyyaml` + `pydantic` | Validation stricte du fichier de conventions |
| Affichage console | `rich` | Messages lisibles pour les débutants |
| Tests | `pytest` | Fichiers SQL d'exemple en entrée, résultat attendu en sortie |
| Qualité du code | `ruff`, `mypy`, `pre-commit` | Mêmes standards que les projets sérieux |
| CI | GitHub Actions | Gratuit pour un dépôt public |
| Documentation | Sphinx + `furo` + GitHub Pages | Déjà en place via le template cruft, doc en ligne générée |
| Publication | PyPI | `pip install <nom>` |
| Validation de bout en bout (plus tard) | Oracle Free dans Docker + `dbt-oracle` | Uniquement à partir de la v0.3 |

Données de test : SQL écrit par toi et projets publics (`jaffle_shop`, requêtes TPC-H) réécrits en style Oracle legacy. Jamais de SQL ni de données de la banque.

## Calendrier indicatif

| Période | Étape | Contenu |
| --- | --- | --- |
| oct. 2026 | Phase 0 — Étude et fondations | Tester sqlglot sur du SQL Oracle, créer le dépôt et la CI |
| nov. – déc. 2026 | v0.1 — `check` | 5 règles d'architecture sur le staging, tests, README |
| janv. – fév. 2027 | v0.2 — Conventions en YAML | Configuration, règles Oracle, première publication sur PyPI |
| | **Jalon : publié sur PyPI** | |
| mars – mai 2027 | v0.3 — `convert` | SQL legacy vers modèles en couches, validé sur Oracle Free |
| | **Jalon : résultats identiques sur Oracle** | |
| juin – juil. 2027 | v0.4 — `explain` | Catalogue d'erreurs dbt et Oracle expliquées en français |
| août – sept. 2027 | Finalisation | Documentation, démo, bonus MCP — fin d'alternance en septembre |

Rythme pensé pour du temps libre, avec de la marge : si une étape déborde, c'est le bonus MCP qui saute, pas `explain`.

## Phase 0 — Étude et fondations

Objectif : lever le risque technique principal et avoir un dépôt propre avant d'écrire la première règle. Durée indicative : 2 à 3 semaines.

- [x] ~~Valider l'idée avec le tuteur (projet open source perso, utilisable ensuite par l'équipe)~~ — abandonnée (décision du 9 octobre 2026)
- [x] Tester `sqlglot` sur 10 à 15 requêtes Oracle typiques : jointures `(+)`, `NVL`, `DECODE`, `ROWNUM`, `CONNECT BY`, `MERGE`
- [x] Tester le parsing d'un modèle dbt contenant du Jinja (`{{ ref() }}`, `{{ source() }}`) après remplacement par des noms factices
- [x] Lire les règles de dbt-project-evaluator et noter celles à reprendre ou à écarter
- [x] Lister les conventions de l'équipe (préfixes, dossiers, casse) sous une forme générique, sans rien de confidentiel
- [x] Créer le dépôt : structure `src/`, `tests/`, `pyproject.toml`, pre-commit, CI qui lance ruff, mypy et pytest
- [x] Vérifier que `dbtidy` est libre sur PyPI
- [x] Ajouter une licence (MIT) au dépôt

**Terminé quand** : un script de 20 lignes parse une requête Oracle legacy et affiche ses tables, jointures et agrégations, et la CI est verte.

## v0.1 — `check` : premières règles

Objectif : une commande qui analyse les modèles staging d'un projet dbt et bloque la CI si l'architecture n'est pas respectée. Durée indicative : 4 à 6 semaines.

**Règles de départ**

| Code | Règle | Exemple détecté |
| --- | --- | --- |
| STG001 | Un modèle staging ne lit qu'une seule source | Deux `source()` dans le même modèle |
| STG002 | Pas de jointure dans le staging | `JOIN` ou jointure `(+)` |
| STG003 | Pas d'agrégation dans le staging | `GROUP BY`, `SUM`, `COUNT`, `DISTINCT` |
| STG004 | Le staging lit une source, pas un autre modèle | `ref('stg_...')` dans un staging |
| ORA001 | Jointure Oracle `(+)` détectée (toutes couches) | `a.id = b.id(+)` → suggérer `LEFT JOIN` |

**Fonctionnement**

1. Trouver les modèles staging par préfixe (`stg_`, `int_`, `fct_`, `dim_`, en dur pour cette version ; configurables depuis la v0.2) ; le dossier (`models/staging/`, etc.) n'est qu'une vérification secondaire, pas le critère de classification.
2. Remplacer les appels Jinja `ref()` et `source()` par des noms factices de même longueur, en gardant la trace de ce qu'ils désignaient, pour que les numéros de ligne rapportés restent corrects.
3. Parser le SQL avec `sqlglot` (dialecte Oracle) et appliquer chaque règle sur l'arbre syntaxique.
4. Afficher chaque violation : fichier, ligne, code, message en français, piste de correction. Seul un code `error` fait échouer la commande (exit 1) ; un `warning` s'affiche sans faire échouer.

**Options** : `--json` pour la CI, désactivation ponctuelle par commentaire `-- noqa: STG002` sur la ligne concernée (convention `sqlfluff`).

**Terminé quand** : les 5 règles sont couvertes par des tests (un cas conforme et un cas en violation chacune), la commande tourne sur `jaffle_shop` et le dépôt a un README avec un exemple de sortie.

## v0.2 — Conventions en YAML et publication PyPI

Objectif : rendre l'outil utilisable par n'importe quelle équipe, puis le publier. Durée indicative : 4 à 5 semaines.

- Fichier de conventions validé par `pydantic` : couches et leurs dossiers, préfixes (`stg_`, `int_`, `fct_`, `dim_`), casse des colonnes, règles activées et leur sévérité (erreur ou avertissement).
- Nouvelles règles Oracle : `NVL` → `COALESCE`, `DECODE` → `CASE`, comparaison `= ''` (toujours fausse en Oracle), identifiant trop long.
- Règles de nommage pilotées par la configuration (préfixe attendu selon le dossier).
- Commande `validate-config` pour vérifier le fichier YAML seul.
- Hook pre-commit prêt à l'emploi.
- Documentation en ligne et première publication sur PyPI (`0.2.0`), CHANGELOG à jour.

Exemple de configuration visé :

```yaml
layers:
  staging:
    path: models/staging
    prefix: stg_
  intermediate:
    path: models/intermediate
    prefix: int_
rules:
  STG002: error
  ORA002: warning
```

**Terminé quand** : `pip install <nom>` fonctionne, et deux configurations différentes donnent deux résultats différents sur le même projet.

## v0.3 — `convert` : du SQL legacy aux modèles dbt

Objectif : transformer une requête Oracle en modèles dbt en couches, conformes aux conventions dès leur création. C'est la version la plus ambitieuse. Durée indicative : 8 à 10 semaines.

1. Repérer les tables sources et générer `sources.yml` ; le schéma/base Oracle cible n'est pas déductible du SQL seul, il vient du mapping de `dbtidy.yml` (décision v0.3, voir [v0.3-convert.md](v0.3-convert.md)).
2. Créer un modèle staging par table source : seulement les colonnes utilisées, renommées selon les conventions.
3. Placer jointures et logique métier dans des modèles intermediate, avec des `ref()`.
4. Placer le `SELECT` final dans un modèle marts.
5. Moderniser au passage : `(+)` → `LEFT JOIN`, `NVL` → `COALESCE`, `DECODE` → `CASE`.
6. Passer le résultat dans `check` : un modèle généré doit toujours être conforme.
7. Marquer d'un commentaire `-- TODO` tout ce qui ne se convertit pas automatiquement, au lieu de deviner.

**Validation de bout en bout** (première utilisation d'Oracle) : lancer Oracle Free dans Docker, exécuter l'ancienne requête et les nouveaux modèles avec `dbt-oracle`, et vérifier que les résultats sont identiques.

**Terminé quand** : 10 requêtes de test sont converties, passent `check` et donnent le même résultat que l'original sur Oracle.

## v0.4 — `explain` : les erreurs en français simple

Objectif : qu'un débutant comprenne une erreur dbt ou Oracle sans avoir peur de la lire. Durée indicative : 4 à 6 semaines.

- Catalogue d'erreurs en YAML : motif de reconnaissance, explication, cause probable, correction suggérée.
- 15 à 20 erreurs courantes pour commencer : modèle introuvable, colonne ambiguë, YAML mal indenté, `ORA-00904` (identifiant invalide), `ORA-00942` (table inexistante), `ORA-00979` (pas une expression GROUP BY).
- Suggestion du nom le plus proche quand un modèle ou une colonne est introuvable (`difflib`, sans dépendance).
- Deux usages : `explain "<message>"` ou `dbt run | explain` pour lire directement la sortie de dbt.
- Erreur inconnue : le dire franchement et afficher le message d'origine, sans inventer.

**Terminé quand** : chaque erreur du catalogue a un test, et un collègue débutant comprend l'explication sans aide.

**Bonus après la v0.4** : exposer `check` et `explain` comme serveur MCP, pour que l'assistant IA vérifie lui-même le code qu'il génère.

## Risques et préparation entretien

| Risque | Parade |
| --- | --- |
| `sqlglot` parse mal certaines syntaxes Oracle | Tester dès la phase 0 ; contribuer un correctif à `sqlglot` si besoin (très valorisant) |
| Le Jinja des modèles dbt empêche le parsing | Remplacer `ref()` et `source()` par des noms factices ; ignorer proprement les macros complexes |
| Proximité avec le travail (propriété du code) | Accord du tuteur, développement sur temps libre, aucun code ni SQL de la banque |
| `convert` trop ambitieux | Accepter les `-- TODO` : un outil honnête vaut mieux qu'un outil qui devine |
| Perte de motivation | Publier tôt (v0.2) et faire tester par l'équipe dès que possible |

**Pour l'entretien**

- README avec le problème, une capture de sortie et l'installation en une ligne.
- Un fichier de décisions : pourquoi `sqlglot`, pourquoi déterministe plutôt qu'un LLM, pourquoi pas dbt-project-evaluator.
- Un journal des difficultés rencontrées et de leur solution : ce sont les meilleures anecdotes.
- Si l'équipe l'utilise : un chiffre concret (nombre de modèles vérifiés, de corrections évitées).
