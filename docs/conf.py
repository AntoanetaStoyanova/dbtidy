"""Configuration Sphinx pour dbtidy."""

project = "dbtidy"
author = "Antoaneta Stoyanova"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

html_theme = "furo"
