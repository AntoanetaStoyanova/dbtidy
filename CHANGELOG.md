# Changelog

Toutes les évolutions notables de dbtidy sont listées ici.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet
respecte le [versionnage sémantique](https://semver.org/lang/fr/).

## [0.2.0] — 2026-10-09

### Ajouté

- Configuration `dbtidy.yml`, lue dans le répertoire courant ou via `check --config PATH` :
  dossiers et préfixes des couches, casse des colonnes, longueur maximale des
  identifiants Oracle et sévérité de chaque règle.
- Sévérités `error`, `warning` et `off` : seul un `error` fait sortir `check` en 1.
  Les avertissements sont marqués `[warning]` dans la sortie texte et portent un champ
  `severity` dans la sortie JSON.
- Commande `dbtidy validate-config [PATH]`.
- Règles Oracle :
  - ORA002 : `NVL` → `COALESCE` ;
  - ORA003 : `DECODE` → `CASE` ;
  - ORA004 : comparaison à `''` ;
  - ORA005 : identifiant trop long.
- Règles de nommage :
  - NAM001 : le préfixe du fichier ne correspond pas au dossier de sa couche ;
  - NAM002 : casse des alias de colonnes.
- Hook pre-commit `dbtidy` (`.pre-commit-hooks.yaml`).
- Deux configurations d'exemple sur `examples/jaffle_shop_oracle` (stricte et tolérante).
- Documentation Sphinx : ligne de commande, configuration et règles.

### Modifié

- STG003 ignore les agrégations d'un `SELECT` qui lit `{{ this }}`, comme le filtre
  `{% if is_incremental() %}` d'un modèle incrémental ; `{{ this }}` reçoit son
  propre nom factice.
- Le résumé distingue les violations (`error`), les avertissements et les erreurs :
  `N fichier(s) analysé(s), N violation(s), N avertissement(s), N erreur(s).`
- Une configuration invalide sort en 2, avec la clé fautive et la raison en français.
- Sans configuration, ORA002 et ORA003 ajoutent des avertissements aux résultats de la
  0.1.0 ; les violations `error` sont inchangées.
- Les codes de règle de `dbtidy.yml` sont acceptés en minuscules (`stg002: off`).
- Un fichier illisible (encodage, droits) est signalé « fichier illisible » et non plus
  « SQL non analysable ».

### Corrigé

- ORA004 plantait sur `'' = ''`.
- Un `ref()` ou `source()` dans un commentaire Jinja `{# #}` était compté (faux
  STG001/STG004).
- `-- noqa: STG002 explication` : le texte après les codes empêchait le `noqa`.
- Un modèle sans SQL (vide, ou seulement du Jinja et des commentaires) sortait en 2.

## [0.1.0] — 2026-10-07

### Ajouté

- Commande `dbtidy check` sur des fichiers ou des dossiers `.sql`, avec sortie texte ou
  `--json`, et codes de sortie `0` (conforme), `1` (violation) ou `2` (erreur).
- Classification des modèles en couches d'après le préfixe du fichier (`stg_`, `int_`,
  `fct_`/`dim_`).
- Règles de staging STG001 à STG004 et règle Oracle ORA001 (jointure `(+)`).
- Neutralisation du Jinja dbt avant le parsing (`ref()`, `source()`, blocs `{% %}`).
- Suppression ciblée par `-- noqa` ou `-- noqa: CODE`.
- Exemple `examples/jaffle_shop_oracle`.

[0.2.0]: https://github.com/AntoanetaStoyanova/dbtidy/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/AntoanetaStoyanova/dbtidy/releases/tag/v0.1.0
