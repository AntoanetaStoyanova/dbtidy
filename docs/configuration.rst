Configuration
=============

dbtidy lit ``dbtidy.yml`` dans le répertoire courant, ou le fichier passé à
``--config``. Sans fichier, les valeurs par défaut ci-dessous s'appliquent ; un
fichier partiel les complète clé par clé.

Valeurs par défaut
------------------

.. code-block:: yaml

   layers:                      # chemins relatifs au fichier de configuration
     staging:
       path: models/staging
       prefixes: [stg_]
     intermediate:
       path: models/intermediate
       prefixes: [int_]
     mart:
       path: models/marts
       prefixes: [fct_, dim_]
   columns_case: null           # lower, upper ou null
   oracle:
     max_identifier_length: 30
   rules:                       # error, warning ou off
     STG001: error
     STG002: error
     STG003: error
     STG004: error
     ORA001: error
     ORA002: warning
     ORA003: warning
     ORA004: error
     ORA005: warning
     NAM001: error
     NAM002: off

Clés
----

``layers``
   Les trois couches reconnues : ``staging``, ``intermediate`` et ``mart``.
   ``prefixes`` décide de la couche d'un modèle d'après le début du nom de son
   fichier (la première couche qui correspond l'emporte). ``path`` est le dossier
   de la couche ; il ne sert qu'à NAM001. Un chemin relatif s'entend depuis le
   dossier du fichier de configuration, ou depuis le répertoire courant sans
   fichier.

``columns_case``
   Casse attendue des alias de colonnes du ``SELECT`` externe (``lower`` ou
   ``upper``), contrôlée par NAM002. ``null`` n'impose rien.

``oracle.max_identifier_length``
   Longueur maximale des identifiants (ORA005) : ``30`` pour une base en
   compatibilité Oracle 12.1 ou antérieure, ``128`` à partir d'Oracle 12.2.

``rules``
   Sévérité de chaque règle (voir :doc:`rules`) :

   - ``error`` : la violation est affichée et ``check`` sort en 1 ;
   - ``warning`` : la violation est affichée avec ``[warning]``, sans changer le
     code de sortie ;
   - ``off`` : la règle n'est pas exécutée.

Exemple
-------

Un projet legacy en migration, qui préfixe son staging en ``src_`` et tolère
encore les jointures en staging :

.. code-block:: yaml

   layers:
     staging:
       prefixes: [src_]
   oracle:
     max_identifier_length: 128
   rules:
     STG002: warning
     ORA002: off

Erreurs
-------

Une clé inconnue, une sévérité inconnue ou un code de règle inconnu est une erreur
de configuration : ``check`` et ``validate-config`` sortent en 2 et le message cite
la clé fautive.

.. code-block:: text

   $ dbtidy validate-config
   dbtidy: dbtidy.yml: configuration invalide
     rules.STG002: Input should be 'error', 'warning' or 'off'
