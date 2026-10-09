"""Classification des modèles dbt en couches, d'après le préfixe du fichier."""

from enum import StrEnum
from pathlib import Path

from beartype import beartype

from dbtidy.config import Config


class Layer(StrEnum):
    """Couche d'un modèle dbt."""

    STAGING = "staging"
    INTERMEDIATE = "intermediate"
    MART = "mart"
    UNKNOWN = "unknown"


@beartype
def layer_of(path: Path, config: Config) -> Layer:
    """
    Déduit la couche d'un modèle à partir du préfixe de son nom de fichier.

    Parameters
    ----------
    path : Path
        Chemin du fichier `.sql` du modèle.
    config : Config
        Configuration qui définit les préfixes de chaque couche.

    Returns
    -------
    Layer
        La première couche dont un préfixe correspond, ou `Layer.UNKNOWN`.

    Examples
    --------
    >>> layer_of(Path("models/staging/stg_clients.sql"), Config())
    <Layer.STAGING: 'staging'>
    >>> layer_of(Path("clients.sql"), Config())
    <Layer.UNKNOWN: 'unknown'>
    """
    for name, layer_config in config.layers:
        if path.stem.startswith(tuple(layer_config.prefixes)):
            return Layer(name)
    return Layer.UNKNOWN


@beartype
def folder_layer(path: Path, config: Config) -> Layer | None:
    """
    Trouve la couche dont le dossier contient le modèle.

    Un chemin de couche relatif s'entend depuis le répertoire courant ; le plus
    profond l'emporte si plusieurs dossiers contiennent le fichier.

    Parameters
    ----------
    path : Path
        Chemin du fichier `.sql` du modèle.
    config : Config
        Configuration qui définit le dossier de chaque couche.

    Returns
    -------
    Layer | None
        La couche du dossier, ou `None` si le fichier n'est sous aucun dossier.
    """
    resolved = path.resolve()
    matches = [
        (len(folder.parts), Layer(name))
        for name, layer_config in config.layers
        if resolved.is_relative_to(folder := layer_config.path.resolve())
    ]
    return max(matches)[1] if matches else None
