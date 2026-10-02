# Contributing to dbtidy

Standards de développement du projet. Ces règles s'appliquent à tout contributeur humain ou IA (Claude Code inclus).

---

## Type hints

Obligatoires partout — arguments, valeurs de retour, variables ambiguës.

```python
def process(data: list[str], limit: int = 10) -> dict[str, int]:
    ...
```

- `mypy --strict` doit passer sans erreur
- Pas de `Any` sauf cas justifié par un commentaire

---

## Docstrings

Obligatoires sur tous les modules, classes et fonctions publiques. Format Google style :

```python
def fetch(url: str, timeout: int = 30) -> bytes:
    """Télécharge le contenu d'une URL.

    Args:
        url: URL cible.
        timeout: Délai max en secondes.

    Returns:
        Contenu brut de la réponse.

    Raises:
        ValueError: Si l'URL est invalide.
    """
```

Fonctions privées (`_nom`) : docstring courte en une ligne suffit.

---

## Style & formatage

Outil unique : **Ruff** (formatage + lint).

```bash
uv run ruff format .   # formate
uv run ruff check .    # lint
```

- Longueur de ligne : 88 caractères
- Guillemets doubles
- Imports triés automatiquement (isort via Ruff)

---

## Tests

```bash
uv run pytest          # lance tous les tests + coverage
```

- Couverture minimale : **88%** (bloquant en CI)
- Les doctests comptent (`--doctest-modules` activé)
- Un test = un comportement précis, pas une fonction
- Nommage : `test_<comportement>.py`, fonctions `test_<ce_qui_est_verifie>()`

---

## Organisation du code

```
src/dbtidy/
├── __main__.py     # uniquement : from . import main; main()
├── bin/            # scripts d'entrée CLI
├── config/         # constantes et paramètres
├── data/           # chargement / sauvegarde de données
├── log/            # configuration des logs (jamais print() en production)
└── notebook/       # utilitaires pour notebooks Jupyter
```

---

## Git

- Branche de développement : `develop`
- Format des commits — **Conventional Commits** :

| Préfixe | Usage |
|---------|-------|
| `feat:` | nouvelle fonctionnalité |
| `fix:` | correction de bug |
| `refactor:` | réécriture sans changement de comportement |
| `test:` | ajout ou correction de tests |
| `docs:` | documentation uniquement |
| `chore:` | maintenance, dépendances, config |

---

## Règles générales

- Commenter le **pourquoi**, jamais le **quoi** (le code doit se lire seul)
- Pas de code mort commenté — git conserve l'historique
- Pas de `print()` en production — passer par `log/`
- Pas de gestion d'erreurs pour des cas impossibles — ne pas sur-défendre le code
- Pas d'abstraction prématurée — trois lignes similaires valent mieux qu'une abstraction inutile
