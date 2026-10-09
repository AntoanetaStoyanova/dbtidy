"""Conventions du projet analysé, lues depuis `dbtidy.yml`."""

from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from beartype import beartype
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

CONFIG_FILE = "dbtidy.yml"


class Severity(StrEnum):
    """Sévérité d'une règle : seul `error` fait échouer `check`."""

    ERROR = "error"
    WARNING = "warning"
    OFF = "off"


DEFAULT_SEVERITY: dict[str, Severity] = {
    "STG001": Severity.ERROR,
    "STG002": Severity.ERROR,
    "STG003": Severity.ERROR,
    "STG004": Severity.ERROR,
    "ORA001": Severity.ERROR,
    "ORA002": Severity.WARNING,
    "ORA003": Severity.WARNING,
    "ORA004": Severity.ERROR,
    "ORA005": Severity.WARNING,
    "NAM001": Severity.ERROR,
    "NAM002": Severity.OFF,
}

KNOWN_RULES: frozenset[str] = frozenset(DEFAULT_SEVERITY)


class ConfigError(Exception):
    """Configuration illisible ou invalide."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LayerConfig(_Strict):
    """
    Dossier et préfixes d'une couche.

    Attributes
    ----------
    path : Path
        Dossier de la couche, relatif au fichier de configuration.
    prefixes : list[str]
        Préfixes de nom de fichier qui classent un modèle dans la couche.
    """

    path: Path
    prefixes: list[str]

    @field_validator("path")
    @classmethod
    def _resolve(cls, value: Path, info: ValidationInfo) -> Path:
        """Résout le chemin par rapport au dossier du fichier de configuration."""
        base = info.context.get("base") if info.context else None
        return base / value if base else value


class LayersConfig(_Strict):
    """Les trois couches reconnues."""

    staging: LayerConfig = LayerConfig(path=Path("models/staging"), prefixes=["stg_"])
    intermediate: LayerConfig = LayerConfig(
        path=Path("models/intermediate"), prefixes=["int_"]
    )
    mart: LayerConfig = LayerConfig(
        path=Path("models/marts"), prefixes=["fct_", "dim_"]
    )


class OracleConfig(_Strict):
    """Contraintes propres à la version d'Oracle ciblée."""

    max_identifier_length: int = Field(default=30, gt=0)


class Config(_Strict):
    """
    Configuration complète ; les valeurs par défaut reproduisent la v0.1.

    Attributes
    ----------
    layers : LayersConfig
        Dossier et préfixes de chaque couche.
    columns_case : Literal["lower", "upper"] | None
        Casse attendue des alias de colonnes, `None` pour ne rien imposer.
    oracle : OracleConfig
        Contraintes Oracle.
    rules : dict[str, Severity]
        Sévérité de chaque règle connue.

    Examples
    --------
    >>> Config().layers.mart.prefixes
    ['fct_', 'dim_']
    >>> Config().rules["STG002"]
    <Severity.ERROR: 'error'>
    """

    layers: LayersConfig = LayersConfig()
    columns_case: Literal["lower", "upper"] | None = None
    oracle: OracleConfig = OracleConfig()
    rules: dict[str, Severity] = Field(default_factory=lambda: dict(DEFAULT_SEVERITY))

    @field_validator("rules", mode="before")
    @classmethod
    def _off_from_yaml(cls, value: object) -> object:
        """Convertit `off` non quoté, que YAML 1.1 lit comme `False`."""
        if isinstance(value, dict):
            return {k: Severity.OFF if v is False else v for k, v in value.items()}
        return value

    @field_validator("rules")
    @classmethod
    def _known_codes(cls, value: dict[str, Severity]) -> dict[str, Severity]:
        """Rejette les codes inconnus et complète avec les sévérités par défaut."""
        unknown = sorted(set(value) - KNOWN_RULES)
        if unknown:
            known = ", ".join(sorted(KNOWN_RULES))
            raise ValueError(
                f"code de règle inconnu : {', '.join(unknown)} (connus : {known})"
            )
        return DEFAULT_SEVERITY | value


def _merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    """Fusionne récursivement `override` dans `base`."""
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _describe(error: ValidationError) -> str:
    """Une ligne par erreur pydantic : clé fautive puis raison."""
    return "\n".join(
        f"  {'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    )


@beartype
def load_config(path: Path | None) -> Config:
    """
    Charge la configuration.

    Parameters
    ----------
    path : Path | None
        Fichier à lire. Si `None`, `dbtidy.yml` du répertoire courant est lu
        s'il existe.

    Returns
    -------
    Config
        La configuration du fichier fusionnée avec les valeurs par défaut, ou les
        valeurs par défaut si aucun fichier n'est trouvé.

    Raises
    ------
    ConfigError
        Fichier explicite introuvable, YAML mal formé ou contenu
        invalide (le message cite la clé fautive et la raison).
    """
    if path is None:
        path = Path.cwd() / CONFIG_FILE
        if not path.is_file():
            return Config()
    elif not path.is_file():
        raise ConfigError(f"{path}: fichier de configuration introuvable")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: YAML invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: le fichier doit contenir un dictionnaire de clés")

    merged = _merge(Config().model_dump(mode="json"), data)
    try:
        return Config.model_validate(merged, context={"base": path.parent})
    except ValidationError as exc:
        raise ConfigError(f"{path}: configuration invalide\n{_describe(exc)}") from exc
