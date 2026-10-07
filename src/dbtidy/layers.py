"""Classification des modèles dbt en couches, d'après le préfixe du fichier."""

from enum import StrEnum
from pathlib import Path

from beartype import beartype


class Layer(StrEnum):
    """Couche d'un modèle dbt."""

    STAGING = "staging"
    INTERMEDIATE = "intermediate"
    MART = "mart"
    UNKNOWN = "unknown"


PREFIXES: dict[str, Layer] = {
    "stg_": Layer.STAGING,
    "int_": Layer.INTERMEDIATE,
    "fct_": Layer.MART,
    "dim_": Layer.MART,
}


@beartype
def layer_of(path: Path) -> Layer:
    """Déduit la couche d'un modèle à partir du préfixe de son nom de fichier.

    Args:
        path: Chemin du fichier `.sql` du modèle.

    Returns:
        La couche correspondant au préfixe, ou `Layer.UNKNOWN`.

    Examples:
        >>> layer_of(Path("models/staging/stg_clients.sql"))
        <Layer.STAGING: 'staging'>
        >>> layer_of(Path("clients.sql"))
        <Layer.UNKNOWN: 'unknown'>
    """
    for prefix, layer in PREFIXES.items():
        if path.stem.startswith(prefix):
            return layer
    return Layer.UNKNOWN
