"""Tâches d'automatisation — exécutées via `inv <commande>`."""

from invoke import Context, task


# ---------------------------------------------------------------------------
# Qualité du code
# ---------------------------------------------------------------------------


@task
def lint(c: Context) -> None:
    """Vérifie le code avec Ruff (lint)."""
    c.run("uv run ruff check .")


@task
def fmt(c: Context) -> None:
    """Formate le code avec Ruff."""
    c.run("uv run ruff format .")


@task
def typecheck(c: Context) -> None:
    """Vérifie les types avec mypy."""
    c.run("uv run mypy src/dbtidy")


@task(pre=[lint, typecheck])  # type: ignore[misc]
def check(c: Context) -> None:
    """Lance lint + typecheck en séquence."""


@task
def test(c: Context) -> None:
    """Lance les tests pytest avec coverage."""
    c.run("uv run pytest")


@task(pre=[check, test])  # type: ignore[misc]
def ci(c: Context) -> None:
    """Lance la suite complète CI : lint, typecheck, tests."""


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


@task
def docs(c: Context) -> None:
    """Génère la documentation Sphinx dans docs/_build/html/."""
    c.run("uv run sphinx-build -b html docs docs/_build/html")
    print("Documentation disponible dans docs/_build/html/index.html")


@task
def docs_clean(c: Context) -> None:
    """Supprime la documentation générée."""
    c.run("rm -rf docs/_build")


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


@task
def push_develop(c: Context) -> None:
    """Pousse la branche courante vers origin/develop."""
    c.run("git push origin develop")


@task
def push_main(c: Context) -> None:
    """Pousse la branche courante vers origin/main (confirmation requise)."""
    answer = input("Push vers main — confirmer ? [o/n] ").strip().lower()
    if answer == "o":
        c.run("git push origin main")
    else:
        print("Push annulé.")
