# Plan d'exécution — GeoSpacialData

> **Document vivant.** Contrairement à [ROADMAP.md](ROADMAP.md) (vue d'ensemble) et
> [TECHNICAL.md](TECHNICAL.md) (référence technique statique), ce fichier est **mis à jour en
> continu** au fil de l'avancement réel du projet : cases cochées, sous-étapes ajoutées si
> découvertes en cours de route, statuts révisés. Rien n'est retiré du fichier une fois fait —
> l'historique des cases cochées sert de trace d'avancement.
>
> **Convention de validation :** à la fin de chaque étape ou phase, un point est fait avec
> l'utilisateur : liste de ce qui a été fait, **scénarios de test / validation manuelle** à
> exécuter, et attente d'un feu vert avant de passer à la suite. Aucune phase n'est considérée
> "terminée" sans ce contrôle.
>
> **Convention de détail :** chaque grande étape (`- [ ]`) est décomposée en sous-étapes
> d'exécution concrètes (`  - [ ]`, indentées). Une grande étape n'est cochée que lorsque
> **toutes** ses sous-étapes le sont. Les sous-étapes peuvent être complétées/affinées en
> cours de route si l'exécution réelle révèle des actions supplémentaires.
>
> Légende : `[ ]` à faire · `[x]` fait · 🔄 en cours (partiel) à côté d'un titre de phase.

**Dernière mise à jour :** 2026-08-05

---

## Phase 0 — Vérification des prérequis

Objectif : s'assurer que tous les éléments nécessaires (comptes, outils, accès, config)
sont réunis avant de développer quoi que ce soit. Cette phase peut être rejouée à tout
moment (ex. changement de machine, nouvel environnement) — elle n'est pas "à usage unique".

- [ ] Compte [Google Earth Engine](https://earthengine.google.com/) approuvé pour usage
      académique
  - [ ] Créer/utiliser un compte Google dédié au projet
  - [ ] Soumettre la demande d'accès Earth Engine (formulaire "non-commercial/academic")
  - [ ] Attendre l'email de confirmation d'approbation Google
  - [ ] Vérifier l'accès en se connectant à https://code.earthengine.google.com/
- [ ] `earthengine authenticate` exécuté avec succès en local (credentials générés)
  - [ ] Installer le package `earthengine-api` (`pip install earthengine-api`)
  - [ ] Exécuter `earthengine authenticate` dans le terminal
  - [ ] Suivre le lien OAuth et s'authentifier avec le compte GEE approuvé
  - [ ] Coller le code d'autorisation renvoyé dans le terminal
  - [ ] Vérifier la présence du fichier credentials généré localement
- [ ] ID du projet Google Cloud associé à Earth Engine connu (`EE_PROJECT_ID`)
  - [ ] Créer un projet Google Cloud dédié (ou identifier un projet existant)
  - [ ] Activer l'API Earth Engine pour ce projet dans la console GCP
  - [ ] Relever l'identifiant du projet et le conserver pour le `.env`
- [ ] Docker Desktop / Docker Engine installé et démarré (`docker --version`,
      `docker compose version`)
  - [ ] Télécharger et installer Docker Desktop (Win/Mac) ou Docker Engine (Linux)
  - [ ] Démarrer le service/l'application Docker
  - [ ] Vérifier `docker --version` et `docker compose version` dans un terminal
- [ ] Python 3.10+ installé, environnement virtuel créé
  - [ ] Vérifier la version installée (`python --version`)
  - [ ] Créer l'environnement virtuel (`python -m venv venv`)
  - [ ] Activer l'environnement virtuel
- [ ] `pip install -r requirements.txt` exécuté sans erreur
  - [ ] Activer l'environnement virtuel
  - [ ] Exécuter `pip install -r requirements.txt`
  - [ ] Résoudre les éventuelles erreurs de compilation de dépendances géospatiales (GDAL, etc.)
- [ ] `.env` créé à partir de [`.env.example`](../.env.example) avec valeurs réelles
      (`EE_PROJECT_ID`, `EE_CONFIG_DIR`, `ORS_API_KEY`, `GEE_INTERVAL_HOURS`,
      `GEE_LOOKBACK_DAYS`)
  - [ ] Copier `.env.example` vers `.env`
  - [ ] Renseigner `EE_PROJECT_ID` et `EE_CONFIG_DIR`
  - [ ] Renseigner `ORS_API_KEY`
  - [ ] Renseigner `GEE_INTERVAL_HOURS` et `GEE_LOOKBACK_DAYS`
  - [ ] Vérifier que `.env` figure bien dans `.gitignore`
- [ ] Clé API [OpenRouteService](https://openrouteservice.org/dev/#/signup) obtenue
  - [ ] Créer un compte sur openrouteservice.org
  - [ ] Générer une clé API (plan gratuit suffisant pour le pilote)
  - [ ] Reporter la clé dans `.env` (`ORS_API_KEY`)
- [ ] Machine de développement avec ≥ 8 Go RAM (16 Go recommandé) et espace disque
      suffisant pour les rasters
  - [ ] Vérifier la RAM disponible sur la machine cible
  - [ ] Vérifier l'espace disque libre disponible pour le stockage des rasters/exports
- [ ] Accès internet stable (appels API GEE / Overpass / ORS)
  - [ ] Tester la connectivité vers earthengine.googleapis.com
  - [ ] Tester la connectivité vers overpass-api.de
  - [ ] Tester la connectivité vers api.openrouteservice.org
- [ ] Dépôt Git initialisé, `.gitignore` en place (secrets `.env` non versionnés)
  - [ ] `git init` si le dépôt n'existe pas encore
  - [ ] Vérifier/compléter `.gitignore` (`.env`, `venv/`, données brutes volumineuses)
  - [ ] Confirmer avec `git status` qu'aucun secret n'est suivi
- [ ] QGIS installé localement (utile dès la Phase 4 pour la validation visuelle NDVI,
      indispensable en Phase 6)
  - [ ] Télécharger et installer QGIS (version LTR recommandée)
  - [ ] Vérifier le lancement correct de l'application
- [ ] Zone(s) d'étude pilote(s) définie(s) et validée(s) — Maroc + Sahara occidental
      (`FAO/GAUL/2015/level0`), sous-zone pilote pour l'export automatisé (bbox dans
      `nifi/scripts/gee_export.py`)
  - [ ] Confirmer le périmètre global (Maroc + Sahara occidental, couche `FAO/GAUL/2015/level0`)
  - [ ] Définir la bbox précise de la sous-zone pilote (export automatisé)
  - [ ] Reporter cette bbox dans `nifi/scripts/gee_export.py`
  - [ ] Faire valider la zone pilote par l'encadrant si nécessaire
- [ ] Cahier des charges relu et compris (voir [`CAHIER~2.docx`](CAHIER~2.docx) et sa
      synthèse dans [TECHNICAL.md](TECHNICAL.md))
  - [ ] Lire l'intégralité de `CAHIER~2.docx`
  - [ ] Comparer avec la synthèse dans TECHNICAL.md (cohérence)
  - [ ] Lister les points ambigus ou ouverts à clarifier avec l'encadrant

**Scénarios de test — Phase 0 :**
1. `docker compose config` → le fichier `docker-compose.yml` est valide, pas d'erreur.
2. `python -c "import ee; ee.Initialize(project='<EE_PROJECT_ID>'); print('OK')"` → affiche
   `OK` sans lever d'exception.
3. `streamlit run app.py` → l'app démarre, la carte s'affiche, aucune erreur d'auth GEE.
4. Vérifier manuellement que `.env` n'apparaît PAS dans `git status` (bien ignoré).

---

## Phase 1 — Cadrage et conception 🔄

- [x] Rédaction du cahier des charges (contexte, problématique, objectifs, périmètre)
  - [x] Formuler le contexte et la problématique
  - [x] Définir les objectifs du projet
  - [x] Délimiter le périmètre fonctionnel et géographique
- [x] Étude de l'existant (GEE, portails Copernicus/USGS, OSM, ORS, solutions commerciales)
  - [x] Recenser les plateformes de données satellites existantes (GEE, Copernicus, USGS)
  - [x] Recenser les sources de données vectorielles/routières (OSM, ORS)
  - [x] Analyser des solutions commerciales comparables
- [x] Analyse des besoins fonctionnels et non fonctionnels
  - [x] Lister les besoins fonctionnels (ingestion, traitement, exposition)
  - [x] Lister les besoins non fonctionnels (performance, sécurité, disponibilité)
- [x] Définition de l'architecture cible (voir [TECHNICAL.md §4](TECHNICAL.md#4-architecture-cible))
  - [x] Schématiser les composants (NiFi, PostGIS, API, front, QGIS)
  - [x] Documenter les flux de données entre composants
- [x] Choix de la stack technologique (NiFi, PostgreSQL/PostGIS, QGIS, Docker, GEE, OSM, ORS)
  - [x] Justifier chaque choix technique dans TECHNICAL.md
- [x] README initial décrivant la structure et l'avancement du projet
  - [x] Décrire la structure du dépôt
  - [x] Décrire l'état d'avancement au moment de la rédaction
- [x] Documentation de référence créée (TECHNICAL.md, ROADMAP.md, PLAN.md — ce fichier)
  - [x] Créer TECHNICAL.md
  - [x] Créer ROADMAP.md
  - [x] Créer PLAN.md
- [ ] Validation formelle du cadrage par l'encadrant académique
  - [ ] Préparer un support de présentation du cadrage
  - [ ] Planifier le point avec l'encadrant
  - [ ] Obtenir un go/no-go explicite avant la Phase 2
  - [ ] Consigner les remarques/ajustements demandés

**Scénarios de test / validation — Phase 1 :**
1. Relecture croisée du cahier des charges + de [TECHNICAL.md](TECHNICAL.md) : cohérence
   entre le besoin exprimé et l'architecture décrite.
2. Point avec l'encadrant académique : présentation du cadrage, obtention d'un go/no-go
   avant de démarrer la Phase 2.

**Mise à jour documentation :** README.md ✅ · TECHNICAL.md ✅ · ROADMAP.md ✅ · PLAN.md ✅
(ce fichier vient d'être créé — rien à mettre à jour pour l'instant).

---

## Phase 2 — Mise en place de l'environnement 🔄

- [x] `docker-compose.yml` de base avec service `nifi`
  - [x] Définir l'image et les ports du service `nifi`
  - [x] Configurer les volumes de persistance NiFi
- [x] Service `gee-exporter` (export NDVI automatisé, zone pilote)
  - [x] Écrire le Dockerfile du service
  - [x] Configurer les variables d'environnement (`EE_PROJECT_ID`, planning d'export)
- [x] `.env.example` documenté et versionné
  - [x] Lister toutes les variables requises avec commentaires
- [ ] Service `postgis` ajouté au `docker-compose.yml` (image `postgis/postgis`, volume
      persistant, variables d'environnement d'identifiants)
  - [ ] Ajouter le service `postgis` avec l'image `postgis/postgis` dans `docker-compose.yml`
  - [ ] Déclarer un volume Docker persistant pour les données PostGIS
  - [ ] Définir les variables d'environnement d'identifiants (utilisateur, mot de passe, base)
  - [ ] Exposer le port PostgreSQL uniquement sur le réseau interne (sauf besoin de debug local)
- [ ] Réseau Docker dédié (bridge isolé) remplaçant le réseau par défaut, exposant
      uniquement les ports nécessaires (NiFi, API, web)
  - [ ] Déclarer un réseau `bridge` custom dans `docker-compose.yml`
  - [ ] Rattacher tous les services à ce réseau
  - [ ] Vérifier qu'aucun port superflu n'est exposé côté hôte
- [ ] Volume Docker persistant dédié aux sauvegardes PostGIS
  - [ ] Déclarer le volume dans `docker-compose.yml`
  - [ ] Documenter son emplacement et sa politique de rétention
- [ ] Squelette du service `backend` (API, ex. FastAPI minimal + Dockerfile) ajouté au
      docker-compose
  - [ ] Créer l'arborescence minimale du service (FastAPI + `requirements.txt`)
  - [ ] Écrire le Dockerfile du backend
  - [ ] Ajouter le service au `docker-compose.yml` avec ses dépendances (`depends_on: postgis`)
  - [ ] Exposer un endpoint `GET /health` de base
- [ ] Squelette du service `frontend` (app web minimale) ajouté au docker-compose
  - [ ] Créer l'arborescence minimale de l'app front
  - [ ] Écrire le Dockerfile du frontend
  - [ ] Ajouter le service au `docker-compose.yml`
- [ ] QGIS installé et testé en local (connexion à une base PostGIS de test)
  - [ ] Créer une base PostGIS de test (locale ou via le conteneur)
  - [ ] Configurer la connexion PostGIS dans QGIS
  - [ ] Vérifier l'affichage d'une table de test
- [ ] `docker compose up -d --build` démarre l'ensemble des services sans erreur
  - [ ] Lancer `docker compose up -d --build`
  - [ ] Vérifier `docker compose ps` (tous les services `running`/`healthy`)
  - [ ] Consulter les logs de chaque service pour écarter les erreurs de démarrage

**Scénarios de test — Phase 2 :**
1. `docker compose up -d --build` → tous les conteneurs démarrent (`docker compose ps`,
   statut `running`/`healthy`).
2. NiFi accessible sur `http://localhost:8080/nifi`.
3. Connexion à PostGIS depuis un client (`psql` ou pgAdmin) avec les identifiants du `.env`.
4. Health-check du service `backend` (ex. `GET /health`) répond `200 OK`.
5. Redémarrage d'un conteneur (`docker restart <container>`) → le service revient
   automatiquement (politique `restart: unless-stopped`/`on-failure`).

**Mise à jour documentation :** TECHNICAL.md §4.1 (statuts des composants) · README.md
(instructions de démarrage complètes) · ROADMAP.md (statut Phase 2).

---

## Phase 3 — Développement des flux d'ingestion (NiFi) 🔄

- [x] Script d'export NDVI pilote (`gee_export.py`) fonctionnel en local / conteneurisé
  - [x] Écrire la logique de calcul NDVI et d'export GEE
  - [x] Tester l'exécution en local
  - [x] Tester l'exécution dans le conteneur `gee-exporter`
- [ ] Process Group NiFi **GEE** configuré (`ListFile`/`FetchFile` sur `nifi/data/gee/`)
  - [ ] Créer le Process Group dédié dans l'UI NiFi
  - [ ] Configurer le processeur `ListFile` sur `nifi/data/gee/`
  - [ ] Configurer le processeur `FetchFile` en aval
  - [ ] Relier la sortie au reste de la chaîne (métadonnées/routage)
- [ ] Process Group NiFi **OSM** configuré (`InvokeHTTP` → Overpass API, écriture dans
      `nifi/data/osm/`)
  - [ ] Créer le Process Group dédié
  - [ ] Configurer `InvokeHTTP` avec la requête Overpass QL cible
  - [ ] Configurer l'écriture du résultat dans `nifi/data/osm/`
  - [ ] Paramétrer la fréquence de déclenchement (planificateur NiFi)
- [ ] Process Group NiFi **ORS** configuré (`InvokeHTTP` → OpenRouteService, écriture dans
      `nifi/data/ors/`)
  - [ ] Créer le Process Group dédié
  - [ ] Configurer `InvokeHTTP` avec l'endpoint ORS et la clé API (`ORS_API_KEY`)
  - [ ] Configurer l'écriture du résultat dans `nifi/data/ors/`
- [ ] Process Group NiFi **Web Scraping** — source(s) cible(s) définie(s) + script(s)
      (`ExecuteScript`/`ExecuteStreamCommand`)
  - [ ] Identifier et valider la/les source(s) à scraper
  - [ ] Écrire le script de scraping (Python) et le tester en autonome
  - [ ] Intégrer le script via `ExecuteScript`/`ExecuteStreamCommand` dans NiFi
- [ ] Chaîne ETL standard par flux : validation du format reçu → extraction de métadonnées
      (date, zone, source) → routage conditionnel (`RouteOnAttribute`)
  - [ ] Ajouter un processeur de validation de format par flux
  - [ ] Ajouter l'extraction des attributs de métadonnées (date, zone, source)
  - [ ] Configurer `RouteOnAttribute` pour le routage conditionnel
- [ ] Gestion des erreurs (relations `failure`, file d'attente dédiée, réessai/backoff,
      notification d'échec définitif) configurée sur chaque flux
  - [ ] Router chaque relation `failure` vers une file d'attente dédiée
  - [ ] Configurer une politique de réessai avec backoff
  - [ ] Configurer une notification (log/alerte) en cas d'échec définitif
- [ ] Journalisation (`LogAttribute`) aux points clés de chaque flux
  - [ ] Ajouter un `LogAttribute` en entrée de chaque Process Group
  - [ ] Ajouter un `LogAttribute` en sortie/erreur de chaque Process Group
- [ ] Export des flux NiFi (templates / `flow.json.gz`) versionné dans le dépôt Git
  - [ ] Exporter chaque Process Group (template ou `flow.json.gz`)
  - [ ] Committer les exports dans le dépôt (dossier dédié, ex. `nifi/flows/`)

**Scénarios de test — Phase 3 :**
1. Déclenchement manuel de chaque Process Group dans l'UI NiFi → un fichier apparaît dans
   le bon dossier `nifi/data/<source>/` avec les métadonnées attendues.
2. Consultation de l'onglet **Data Provenance** pour vérifier la traçabilité de bout en bout
   d'un flow file.
3. Simulation d'un échec (couper la connexion réseau, ou pointer vers une URL invalide) →
   vérifier le comportement de réessai puis la notification d'échec définitif.
4. Vérifier qu'un fichier corrompu/mal formé est bien routé vers la file d'erreurs et non
   inséré plus loin dans la chaîne.

**Mise à jour documentation :** TECHNICAL.md §7 (statuts par source) · README.md (section
ingestion automatisée) · ROADMAP.md (statut Phase 3).

---

## Phase 4 — Traitement et transformation

- [x] Calcul du NDVI (seuil 0.3) — script GEE interactif
      ([`vegetation_cover_ndvi.js`](../gee_scripts/vegetation_cover_ndvi.js))
  - [x] Implémenter la formule NDVI dans le script GEE
  - [x] Appliquer le seuil 0.3 pour la classification végétation/non-végétation
  - [x] Valider visuellement le résultat sur la zone pilote
- [ ] Calcul NDVI intégré au pipeline automatisé (pas seulement interactif GEE)
  - [ ] Porter la logique du script interactif dans `gee_export.py` (ou module dédié)
  - [ ] Paramétrer le seuil et la zone via configuration/`.env`
  - [ ] Intégrer l'appel dans le flux NiFi **GEE**
- [ ] Calcul du NDWI (indice d'eau)
  - [ ] Implémenter la formule NDWI
  - [ ] Définir le seuil de classification de l'eau
  - [ ] Intégrer au pipeline automatisé (même approche que NDVI)
- [ ] Validation des géométries reçues (rejet/correction des géométries invalides)
  - [ ] Ajouter un contrôle `ST_IsValid`/équivalent en entrée
  - [ ] Définir la règle : correction automatique (`ST_MakeValid`) vs rejet
  - [ ] Journaliser les géométries rejetées
- [ ] Déduplication (clés naturelles : identifiant OSM, couple date/zone pour les images
      satellites)
  - [ ] Définir la clé naturelle par type de source (OSM id, date+zone satellite)
  - [ ] Implémenter la logique de détection de doublon
  - [ ] Définir la règle de résolution (conserver le plus récent, etc.)
- [ ] Gestion des valeurs manquantes (règles définies par type de donnée : interpolation,
      exclusion, marquage explicite)
  - [ ] Lister les types de valeurs manquantes possibles par source
  - [ ] Définir la règle par type (interpolation / exclusion / marquage)
  - [ ] Implémenter la règle dans le pipeline de transformation
- [ ] Conversion CRS harmonisée : EPSG:4326 (échange) + EPSG:326xx UTM (calculs métriques
      locaux), via GDAL/PROJ
  - [ ] Identifier la zone UTM correspondant à la zone d'étude (EPSG:326xx)
  - [ ] Implémenter la conversion via GDAL/PROJ dans le pipeline
  - [ ] Vérifier la cohérence des reprojections sur un jeu de test
- [ ] Génération de couches thématiques (végétation, eau, zones urbaines) par seuillage des
      indices calculés
  - [ ] Définir les seuils de classification par thème
  - [ ] Générer la couche vecteur/raster par thème
  - [ ] Stocker le résultat au format cible (GeoTIFF/GeoJSON)
- [ ] Jointures spatiales OSM × NDVI pour statistiques zonales (moyenne NDVI par polygone)
  - [ ] Implémenter la jointure spatiale (zonal statistics)
  - [ ] Calculer la moyenne NDVI par polygone OSM
  - [ ] Valider le résultat sur un échantillon de polygones connus

**Scénarios de test — Phase 4 :**
1. Comparaison d'un jeu de données avant/après transformation : CRS correct, pas de
   doublons, valeurs manquantes traitées selon la règle définie.
2. Validation visuelle du NDVI sur QGIS pour la zone pilote (superposition avec l'image RGB).
3. Injection volontaire d'une géométrie invalide en entrée → vérifier qu'elle est rejetée ou
   corrigée selon la règle définie, sans casser le reste du pipeline.
4. Vérification numérique : le taux de couverture végétale recalculé correspond à celui
   obtenu par le script interactif (marge d'erreur acceptable liée à la résolution/`scale`).

**Mise à jour documentation :** TECHNICAL.md §8 (formules et règles définitives) ·
README.md (méthode).

---

## Phase 5 — Centralisation et modélisation des données (PostGIS)

- [ ] Service PostgreSQL/PostGIS opérationnel (dépend de la Phase 2)
  - [ ] Vérifier que le service `postgis` démarre correctement (`docker compose ps`)
  - [ ] Vérifier l'extension PostGIS active (`SELECT PostGIS_Version();`)
- [ ] Schéma `raw` créé (données brutes horodatées)
  - [ ] Écrire le script SQL de création du schéma `raw`
  - [ ] Créer les tables de données brutes par source, avec horodatage
- [ ] Schéma `processed` créé (NDVI, couches thématiques)
  - [ ] Écrire le script SQL de création du schéma `processed`
  - [ ] Créer les tables NDVI/NDWI/couches thématiques
- [ ] Schéma `metadata` créé (documentation des jeux de données)
  - [ ] Écrire le script SQL de création du schéma `metadata`
  - [ ] Définir la structure de la table de métadonnées
- [ ] Schéma `users` créé (gestion des accès)
  - [ ] Écrire le script SQL de création du schéma `users`
  - [ ] Définir la structure des tables utilisateurs/rôles
- [ ] Table de métadonnées centralisée (source, licence, date de collecte, CRS, résolution,
      lien vers le fichier/objet raster)
  - [ ] Définir les colonnes (source, licence, date de collecte, CRS, résolution, lien fichier)
  - [ ] Implémenter l'insertion automatique de métadonnées depuis le pipeline NiFi
- [ ] Nomenclature normalisée des jeux de données (`source_type_zone_date`)
  - [ ] Documenter la convention de nommage
  - [ ] Appliquer la convention dans les scripts d'insertion/export
- [ ] Index GiST sur les colonnes géométriques
  - [ ] Identifier les colonnes géométriques nécessitant un index
  - [ ] Créer les index GiST correspondants
- [ ] Mécanisme de versionnement (identifiant logique + numéro de version + date de
      génération), sans écrasement des données précédentes
  - [ ] Ajouter les colonnes `id_logique`, `version`, `date_generation` aux tables concernées
  - [ ] Implémenter la logique d'incrémentation de version à l'insertion
- [ ] Rôles PostgreSQL créés et appliqués (lecture seule / écriture restreinte NiFi /
      administrateur — moindre privilège)
  - [ ] Créer le rôle lecture seule
  - [ ] Créer le rôle écriture restreinte (utilisé par NiFi)
  - [ ] Créer le rôle administrateur
  - [ ] Appliquer les `GRANT`/`REVOKE` correspondants sur chaque schéma
- [ ] Stratégie de sauvegarde (`pg_dump`/`pg_basebackup` planifiés, volume Docker dédié,
      rotation)
  - [ ] Définir la fréquence de sauvegarde
  - [ ] Écrire le script de sauvegarde (`pg_dump`/`pg_basebackup`)
  - [ ] Planifier son exécution (cron/service dédié)
  - [ ] Définir et implémenter la politique de rotation des sauvegardes
- [ ] Contraintes d'intégrité (clés primaires, `ST_IsValid` pour la validité géométrique)
  - [ ] Définir les clés primaires sur chaque table
  - [ ] Ajouter des contraintes `CHECK (ST_IsValid(geom))` sur les colonnes géométriques
- [ ] Partitionnement des tables volumineuses par zone/période (si nécessaire à ce stade)
  - [ ] Évaluer le volume de données réel et le besoin de partitionnement
  - [ ] Implémenter le partitionnement si le besoin est confirmé

**Scénarios de test — Phase 5 :**
1. Insertion d'un jeu de données de test dans chaque schéma (`raw`, `processed`,
   `metadata`) → cohérence vérifiée via requêtes SQL.
2. Exécution d'une requête spatiale (`ST_Intersects`, `ST_Within`) → résultat correct,
   `EXPLAIN ANALYZE` confirme l'utilisation de l'index GiST.
3. Test de versionnement : insertion d'une nouvelle génération de NDVI pour une même
   zone/date → l'ancienne version reste consultable.
4. Test des rôles : connexion avec le rôle "lecture seule" → une tentative d'écriture doit
   échouer.
5. `pg_dump` puis restauration sur une base vierge → les données sont identiques.

**Mise à jour documentation :** TECHNICAL.md §9 (schéma définitif, éventuel diagramme ER) ·
ROADMAP.md (statut Phase 5).

---

## Phase 6 — Exposition des données

- [ ] Squelette de l'API REST démarré (conteneurisé, ex. FastAPI)
  - [ ] Vérifier le démarrage du service `backend` créé en Phase 2
  - [ ] Connecter l'API à PostGIS (chaîne de connexion via `.env`)
- [ ] Endpoint : liste des jeux de données disponibles + métadonnées
  - [ ] Implémenter la requête SQL sur le schéma `metadata`
  - [ ] Exposer l'endpoint (`GET /datasets`) avec pagination si nécessaire
- [ ] Endpoint : requêtage spatial (filtrage par zone, date, type d'indice)
  - [ ] Définir les paramètres de filtrage (bbox/zone, date, type d'indice)
  - [ ] Implémenter la requête spatiale correspondante (`ST_Intersects`, etc.)
  - [ ] Exposer l'endpoint et documenter les paramètres
- [ ] Endpoint : téléchargement (GeoTIFF, GeoJSON, Shapefile, Parquet)
  - [ ] Implémenter l'export au format GeoTIFF
  - [ ] Implémenter l'export au format GeoJSON
  - [ ] Implémenter l'export au format Shapefile
  - [ ] Implémenter l'export au format Parquet
- [ ] Authentification API (clé API ou JWT), distinguant rôles lecture seule / admin
  - [ ] Choisir le mécanisme (clé API ou JWT)
  - [ ] Implémenter la vérification d'authentification sur les endpoints
  - [ ] Implémenter la distinction de rôles (lecture seule / admin)
- [ ] Documentation OpenAPI/Swagger générée et accessible
  - [ ] Vérifier/compléter les schémas OpenAPI générés par FastAPI
  - [ ] Rendre la documentation accessible (`/docs`)
- [ ] Application web — carte interactive (Leaflet ou OpenLayers) affichant les couches
      NDVI/thématiques
  - [ ] Choisir la librairie (Leaflet ou OpenLayers)
  - [ ] Intégrer le fond de carte de base
  - [ ] Ajouter la couche NDVI/thématique consommée depuis l'API
  - [ ] Ajouter une légende de couleurs
- [ ] Application web — tableau de bord de statistiques synthétiques
  - [ ] Définir les indicateurs à afficher (ex. % couverture végétale par zone)
  - [ ] Implémenter les composants de visualisation (graphiques/KPI)
  - [ ] Connecter le tableau de bord à l'API
- [ ] Intégration QGIS — connexion directe à PostGIS testée
  - [ ] Configurer la connexion PostGIS dans QGIS avec les identifiants du rôle adapté
  - [ ] Charger une couche `processed` et vérifier son affichage
- [ ] Intégration QGIS — projet QGIS préconfiguré versionné dans le dépôt
      (`documentation/` ou `qgis_projects/`)
  - [ ] Construire un projet QGIS avec les couches et styles pré-configurés
  - [ ] Exporter/committer le fichier projet dans le dépôt
- [ ] Module de reporting (génération de rapport PDF/HTML périodique)
  - [ ] Définir le contenu type du rapport (statistiques, cartes, période)
  - [ ] Implémenter la génération (ex. templating + export PDF/HTML)
  - [ ] Planifier la génération périodique si requis

**Scénarios de test — Phase 6 :**
1. Appel de chaque endpoint via `curl`/Postman, avec et sans clé API valide → codes de
   retour attendus (200 / 401 / 403).
2. Ouverture de la documentation Swagger et test interactif d'au moins un endpoint par
   catégorie (consultation, requêtage spatial, téléchargement).
3. Ouverture de l'application web, affichage de la carte NDVI sur la zone pilote,
   vérification visuelle de la légende/couleurs.
4. Ouverture du projet QGIS préconfiguré → les couches PostGIS se chargent correctement.
5. Génération d'un rapport de test → contenu cohérent avec les données en base.

**Mise à jour documentation :** TECHNICAL.md §10 · README.md (instructions d'utilisation
API / web / QGIS) · documentation OpenAPI publiée.

---

## Phase 7 — Tests et validation

- [ ] Tests unitaires du backend (API, fonctions de transformation)
  - [ ] Mettre en place le framework de test (ex. `pytest`)
  - [ ] Écrire les tests des fonctions de transformation (NDVI, NDWI, CRS, dédup.)
  - [ ] Écrire les tests des endpoints API principaux
- [ ] Test de bout en bout par source (GEE, OSM, ORS, web scraping) : collecte → insertion
      en base
  - [ ] Dérouler le scénario complet pour la source GEE
  - [ ] Dérouler le scénario complet pour la source OSM
  - [ ] Dérouler le scénario complet pour la source ORS
  - [ ] Dérouler le scénario complet pour le web scraping
- [ ] Validation visuelle du NDVI sur QGIS (comparaison avec l'image RGB, cohérence avec
      l'ODD 15)
  - [ ] Superposer la couche NDVI et l'image RGB sur QGIS
  - [ ] Vérifier la cohérence visuelle (zones végétalisées plausibles)
  - [ ] Relier l'analyse à l'indicateur ODD 15 visé
- [ ] Test de déploiement complet sur une machine tierce (`docker compose up` en une seule
      commande, sans configuration manuelle additionnelle)
  - [ ] Cloner le dépôt sur une machine "propre" (ou VM)
  - [ ] Renseigner uniquement le `.env`
  - [ ] Exécuter `docker compose up` et vérifier le démarrage complet sans intervention manuelle
- [ ] Tests non fonctionnels : performance (temps de réponse API), fiabilité (simulation
      d'échec réseau), disponibilité (redémarrage automatique des conteneurs)
  - [ ] Mesurer le temps de réponse des endpoints critiques
  - [ ] Simuler une coupure réseau et observer le comportement du pipeline
  - [ ] Tester le redémarrage automatique des conteneurs après arrêt forcé
- [ ] Revue de sécurité (secrets non exposés dans le code/l'historique Git, HTTPS en
      production, rôles appliquant le moindre privilège)
  - [ ] Vérifier l'absence de secrets dans le code et l'historique Git (`git log -p`/`git grep`)
  - [ ] Vérifier la configuration HTTPS prévue pour la production
  - [ ] Vérifier l'application du principe de moindre privilège sur les rôles PostgreSQL/API
- [ ] Vérification une par une des critères de validation du cahier des charges
      (voir [TECHNICAL.md §18](TECHNICAL.md#18-critères-de-validation-et-dacceptation))
  - [ ] Reprendre chaque critère du §18 et vérifier son statut
  - [ ] Consigner les critères non satisfaits et le plan d'action associé

**Scénarios de test — Phase 7 :**
1. Exécution de la suite de tests automatisés (backend) → tous verts.
2. Déroulé manuel de chaque scénario de test des phases précédentes, résultats consignés.
3. Déploiement complet réalisé par une tierce personne sur une machine "propre" (ou une VM),
   à partir du seul dépôt Git + `.env` rempli.
4. Revue de sécurité : `git log -p` / `git grep` pour confirmer l'absence de secrets commités.

**Mise à jour documentation :** TECHNICAL.md (statuts finaux de tous les composants) ·
rédaction éventuelle d'un `documentation/TEST_REPORT.md` récapitulatif.

---

## Phase 8 — Rédaction et soutenance

- [ ] Rédaction du rapport de PFA (contexte, conception, réalisation, résultats, bilan,
      perspectives)
  - [ ] Rédiger la partie contexte et problématique
  - [ ] Rédiger la partie conception/architecture
  - [ ] Rédiger la partie réalisation (choix techniques, difficultés rencontrées)
  - [ ] Rédiger la partie résultats
  - [ ] Rédiger le bilan et les perspectives
- [ ] Finalisation de TECHNICAL.md, ROADMAP.md, PLAN.md (état final du projet)
  - [ ] Mettre à jour TECHNICAL.md avec l'état final de chaque composant
  - [ ] Mettre à jour ROADMAP.md avec le statut final de chaque phase
  - [ ] Mettre à jour PLAN.md (ce fichier) — toutes les cases cochées ou justifiées
- [ ] Préparation du jeu de données de démonstration (zone pilote entièrement traitée, NDVI
      + couches thématiques)
  - [ ] Exécuter le pipeline complet sur la zone pilote
  - [ ] Vérifier la présence de toutes les couches attendues en base
- [ ] Préparation de la présentation de soutenance
  - [ ] Construire le support de présentation (slides)
  - [ ] Préparer le script de démonstration live
- [ ] Relecture croisée (encadrant académique / pairs)
  - [ ] Faire relire le rapport par l'encadrant
  - [ ] Faire relire le rapport par un ou plusieurs pairs
  - [ ] Intégrer les retours de relecture
- [ ] Répétition chronométrée de la soutenance, y compris démo en local (sans dépendre du
      réseau le jour J si possible)
  - [ ] Répéter la présentation avec chronométrage
  - [ ] Répéter la démo en local, données pré-chargées
  - [ ] Ajuster le contenu si dépassement du temps imparti

**Scénarios de test — Phase 8 :**
1. Relecture complète du rapport (cohérence avec le code et la documentation technique).
2. Répétition de la soutenance avec démo live sur l'environnement Docker local.
3. Vérification que la démo fonctionne même en cas de coupure réseau (données pré-chargées
   en base, pas de dépendance critique à un appel API live pendant la présentation).

**Mise à jour documentation :** tous les documents (`README.md`, `TECHNICAL.md`,
`ROADMAP.md`, `PLAN.md`) figés dans leur état final, cohérents avec le rapport de PFA.

---

## Historique des révisions de ce plan

| Date | Modification |
|---|---|
| 2026-08-03 | Création initiale du plan (Phase 0 à 8), basé sur le cahier des charges et l'état réel du dépôt à cette date |
| 2026-08-05 | Ajout de sous-étapes d'exécution détaillées pour chaque grande étape de chaque phase (Phase 0 à 8), afin que chaque action concrète à réaliser soit explicitement listée |
