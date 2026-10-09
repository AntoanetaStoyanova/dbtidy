"""Configuration Sphinx pour dbtidy."""

from dbtidy import __version__

project = "dbtidy"
author = "Antoaneta Stoyanova"
release = __version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

html_theme = "furo"

# Les docstrings utilisent `x` (style Markdown) pour du code.
default_role = "literal"
