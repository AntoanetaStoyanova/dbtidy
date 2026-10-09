Ligne de commande
=================

``dbtidy check``
----------------

.. code-block:: bash

   dbtidy check                      # analyse models/
   dbtidy check chemin/vers/models   # fichiers ou dossiers .sql
   dbtidy check --json               # sortie JSON pour la CI
   dbtidy check --config conventions.yml

Sans ``--config``, ``dbtidy.yml`` est lu dans le répertoire courant s'il existe ;
sinon les valeurs par défaut s'appliquent (voir :doc:`configuration`).

Chaque violation est affichée sous la forme ``chemin:ligne: CODE message``, suivie
d'une piste de correction. Une violation de sévérité ``warning`` porte la mention
``[warning]`` après son code. Une ligne de résumé termine la sortie :

.. code-block:: text

   5 fichier(s) analysé(s), 10 violation(s), 12 avertissement(s), 0 erreur(s).

Avec ``--json``, la sortie est un objet ``files``, ``violations`` (``path``,
``line``, ``code``, ``message``, ``fix``, ``severity``), ``errors`` et
``exit_code``.

Pour ignorer une règle sur une ligne, ajoutez un commentaire ``-- noqa: STG002``,
ou ``-- noqa`` pour toutes les règles.

``dbtidy validate-config``
--------------------------

.. code-block:: bash

   dbtidy validate-config            # valide dbtidy.yml
   dbtidy validate-config conventions.yml

Valide un fichier de configuration sans analyser de modèle. Le chemin par défaut
est ``dbtidy.yml`` ; un fichier absent est une erreur.

Codes de sortie
---------------

.. list-table::
   :header-rows: 1

   * - Code
     - Signification
   * - ``0``
     - Conforme : aucune violation ``error`` (des ``warning`` peuvent être affichés),
       ou configuration valide.
   * - ``1``
     - Au moins une violation de sévérité ``error``.
   * - ``2``
     - Erreur : chemin introuvable, configuration invalide, SQL non analysable.

Hook pre-commit
---------------

.. code-block:: yaml

   repos:
     - repo: https://github.com/AntoanetaStoyanova/dbtidy
       rev: v0.2.0
       hooks:
         - id: dbtidy

Le hook lance ``dbtidy check`` sur les fichiers ``.sql`` modifiés, avec le
``dbtidy.yml`` de la racine du dépôt s'il existe.
