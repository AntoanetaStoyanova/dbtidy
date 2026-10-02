# État du projet — dbtidy

> **Usage — Claude Code** : ce fichier est ta mémoire vivante du projet.
> À chaque fois que l'utilisateur demande une review de code, ajoute une nouvelle entrée
> en haut du fichier (sous ce bloc), avec la date du jour, l'état réel du code,
> et les améliorations concrètes à faire. Ne supprime pas les entrées précédentes —
> elles servent à tracer l'évolution du projet dans le temps.
>
> Format d'une entrée :
>
> ## [YYYY-MM-DD] — <titre court décrivant l'état>
> ### État actuel
> ### Améliorations suggérées

---

## [2026-10-02] — Initialisation du projet

### État actuel

- Projet généré depuis le template cruft
- Structure de base en place : `src/`, `tests/`, `config/`, `log/`, `data/`, `notebook/`
- Environnement Python 3.13 configuré avec uv
- Outils configurés : Ruff (lint + format), mypy (strict), pytest + coverage (seuil 88%)
- Aucune logique métier implémentée — projet vide prêt à démarrer
- Branche active : `develop`

### Améliorations suggérées

- Définir la logique métier dans `src/dbtidy/`
- Écrire un premier test dans `tests/` pour valider le setup
- Configurer les logs dans `log/__init__.py` (ex. : `logging.basicConfig`)
- Documenter le cas d'usage principal dans `README.md`
