Règles
======

La couche d'un modèle est déduite du préfixe de son fichier (voir
:doc:`configuration`). Les règles STG ne s'appliquent qu'au staging ; les règles
ORA et NAM s'appliquent à toutes les couches.

.. list-table::
   :header-rows: 1
   :widths: 10 15 75

   * - Code
     - Sévérité par défaut
     - Règle
   * - STG001
     - error
     - Un modèle staging ne lit qu'une seule source.
   * - STG002
     - error
     - Pas de jointure dans le staging.
   * - STG003
     - error
     - Pas d'agrégation dans le staging (``GROUP BY``, ``SUM``, ``COUNT``,
       ``DISTINCT``…), hors fonctions analytiques.
   * - STG004
     - error
     - Le staging lit une source, pas un autre modèle (``ref()``).
   * - ORA001
     - error
     - Jointure Oracle ``(+)``.
   * - ORA002
     - warning
     - ``NVL`` à remplacer par ``COALESCE``.
   * - ORA003
     - warning
     - ``DECODE`` à remplacer par ``CASE``.
   * - ORA004
     - error
     - Comparaison à ``''``, qu'Oracle traite comme ``NULL``.
   * - ORA005
     - warning
     - Alias, CTE ou colonne plus long que ``oracle.max_identifier_length``.
   * - NAM001
     - error
     - Fichier rangé dans le dossier d'une couche sans en avoir le préfixe.
   * - NAM002
     - off
     - Alias de colonne dans une casse différente de ``columns_case``.

Staging
-------

STG001 — une seule source
   .. code-block:: sql+jinja

      select * from {{ source('erp', 'clients') }}
      union all
      select * from {{ source('crm', 'clients') }}   -- STG001

   Créez un modèle staging par source, puis combinez-les dans un modèle
   intermediate.

STG002 — pas de jointure
   .. code-block:: sql+jinja

      select c.id, p.libelle
      from {{ source('erp', 'clients') }} c
      join {{ source('erp', 'pays') }} p on p.code = c.pays   -- STG002

STG003 — pas d'agrégation
   .. code-block:: sql+jinja

      select client_id, sum(montant) as total                -- STG003
      from {{ source('erp', 'paiements') }}
      group by client_id

   ``row_number() over (...)`` et les autres fonctions analytiques restent
   autorisées.

STG004 — pas de ``ref()``
   .. code-block:: sql+jinja

      select * from {{ ref('stg_clients') }}                 -- STG004

Oracle
------

ORA001 — jointure ``(+)``
   .. code-block:: sql+jinja

      select c.id, p.libelle
      from clients c, pays p
      where c.pays = p.code(+)                               -- ORA001

   Réécrivez-la en ``LEFT JOIN ... ON ...``.

ORA002 — ``NVL``
   .. code-block:: sql+jinja

      select nvl(c.nom, 'inconnu') as nom                    -- ORA002
      select coalesce(c.nom, 'inconnu') as nom               -- conforme

ORA003 — ``DECODE``
   .. code-block:: sql+jinja

      select decode(c.statut, 'A', 'actif', 'inactif')       -- ORA003
      select case when c.statut = 'A' then 'actif' else 'inactif' end

ORA004 — comparaison à ``''``
   .. code-block:: sql+jinja

      where c.nom = ''                                       -- ORA004 : IS NULL
      where c.nom <> ''                                      -- ORA004 : IS NOT NULL

   Oracle stocke ``''`` comme ``NULL`` : la condition n'est jamais vraie.

ORA005 — identifiant trop long
   .. code-block:: sql+jinja

      with clients_actifs_avec_commandes_recentes as (...)   -- ORA005 (38 > 30)

   Chaque nom est signalé une fois, à sa première ligne. Les noms générés pour
   ``ref()`` et ``source()`` sont ignorés.

Nommage
-------

NAM001 — préfixe et dossier
   ``models/staging/int_clients.sql`` est signalé en ligne 1 : le fichier est
   dans le dossier staging mais porte un préfixe intermediate. Un fichier hors
   de tout dossier de couche n'est pas contrôlé.

NAM002 — casse des colonnes
   Avec ``columns_case: lower`` et ``NAM002: warning`` :

   .. code-block:: sql+jinja

      select c.nom as NOM_CLIENT                             -- NAM002
      from {{ ref('stg_clients') }} c

   Seuls les alias du ``SELECT`` externe sont contrôlés.
