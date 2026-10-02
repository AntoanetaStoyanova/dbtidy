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
git clone https://github.com//dbtidy.git
cd dbtidy
uv sync
```

## Utilisation

```bash
uv run python -m dbtidy
```

## Mettre à jour depuis le template

```bash
cruft update
```
