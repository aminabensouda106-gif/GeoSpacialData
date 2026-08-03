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
> Légende : `[ ]` à faire · `[x]` fait · 🔄 en cours (partiel) à côté d'un titre de phase.

**Dernière mise à jour :** 2026-08-03

---

## Phase 0 — Vérification des prérequis

Objectif : s'assurer que tous les éléments nécessaires (comptes, outils, accès, config)
sont réunis avant de développer quoi que ce soit. Cette phase peut être rejouée à tout
moment (ex. changement de machine, nouvel environnement) — elle n'est pas "à usage unique".

- [ ] Compte [Google Earth Engine](https://earthengine.google.com/) approuvé pour usage
      académique
- [ ] `earthengine authenticate` exécuté avec succès en local (credentials générés)
- [ ] ID du projet Google Cloud associé à Earth Engine connu (`EE_PROJECT_ID`)
- [ ] Docker Desktop / Docker Engine installé et démarré (`docker --version`,
      `docker compose version`)
- [ ] Python 3.10+ installé, environnement virtuel créé
- [ ] `pip install -r requirements.txt` exécuté sans erreur
- [ ] `.env` créé à partir de [`.env.example`](../.env.example) avec valeurs réelles
      (`EE_PROJECT_ID`, `EE_CONFIG_DIR`, `ORS_API_KEY`, `GEE_INTERVAL_HOURS`,
      `GEE_LOOKBACK_DAYS`)
- [ ] Clé API [OpenRouteService](https://openrouteservice.org/dev/#/signup) obtenue
- [ ] Machine de développement avec ≥ 8 Go RAM (16 Go recommandé) et espace disque
      suffisant pour les rasters
- [ ] Accès internet stable (appels API GEE / Overpass / ORS)
- [ ] Dépôt Git initialisé, `.gitignore` en place (secrets `.env` non versionnés)
- [ ] QGIS installé localement (utile dès la Phase 4 pour la validation visuelle NDVI,
      indispensable en Phase 6)
- [ ] Zone(s) d'étude pilote(s) définie(s) et validée(s) — Maroc + Sahara occidental
      (`FAO/GAUL/2015/level0`), sous-zone pilote pour l'export automatisé (bbox dans
      `nifi/scripts/gee_export.py`)
- [ ] Cahier des charges relu et compris (voir [`CAHIER~2.docx`](CAHIER~2.docx) et sa
      synthèse dans [TECHNICAL.md](TECHNICAL.md))

**Scénarios de test — Phase 0 :**
1. `docker compose config` → le fichier `docker-compose.yml` est valide, pas d'erreur.
2. `python -c "import ee; ee.Initialize(project='<EE_PROJECT_ID>'); print('OK')"` → affiche
   `OK` sans lever d'exception.
3. `streamlit run app.py` → l'app démarre, la carte s'affiche, aucune erreur d'auth GEE.
4. Vérifier manuellement que `.env` n'apparaît PAS dans `git status` (bien ignoré).

---

## Phase 1 — Cadrage et conception 🔄

- [x] Rédaction du cahier des charges (contexte, problématique, objectifs, périmètre)
- [x] Étude de l'existant (GEE, portails Copernicus/USGS, OSM, ORS, solutions commerciales)
- [x] Analyse des besoins fonctionnels et non fonctionnels
- [x] Définition de l'architecture cible (voir [TECHNICAL.md §4](TECHNICAL.md#4-architecture-cible))
- [x] Choix de la stack technologique (NiFi, PostgreSQL/PostGIS, QGIS, Docker, GEE, OSM, ORS)
- [x] README initial décrivant la structure et l'avancement du projet
- [x] Documentation de référence créée (TECHNICAL.md, ROADMAP.md, PLAN.md — ce fichier)
- [ ] Validation formelle du cadrage par l'encadrant académique

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
- [x] Service `gee-exporter` (export NDVI automatisé, zone pilote)
- [x] `.env.example` documenté et versionné
- [ ] Service `postgis` ajouté au `docker-compose.yml` (image `postgis/postgis`, volume
      persistant, variables d'environnement d'identifiants)
- [ ] Réseau Docker dédié (bridge isolé) remplaçant le réseau par défaut, exposant
      uniquement les ports nécessaires (NiFi, API, web)
- [ ] Volume Docker persistant dédié aux sauvegardes PostGIS
- [ ] Squelette du service `backend` (API, ex. FastAPI minimal + Dockerfile) ajouté au
      docker-compose
- [ ] Squelette du service `frontend` (app web minimale) ajouté au docker-compose
- [ ] QGIS installé et testé en local (connexion à une base PostGIS de test)
- [ ] `docker compose up -d --build` démarre l'ensemble des services sans erreur

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
- [ ] Process Group NiFi **GEE** configuré (`ListFile`/`FetchFile` sur `nifi/data/gee/`)
- [ ] Process Group NiFi **OSM** configuré (`InvokeHTTP` → Overpass API, écriture dans
      `nifi/data/osm/`)
- [ ] Process Group NiFi **ORS** configuré (`InvokeHTTP` → OpenRouteService, écriture dans
      `nifi/data/ors/`)
- [ ] Process Group NiFi **Web Scraping** — source(s) cible(s) définie(s) + script(s)
      (`ExecuteScript`/`ExecuteStreamCommand`)
- [ ] Chaîne ETL standard par flux : validation du format reçu → extraction de métadonnées
      (date, zone, source) → routage conditionnel (`RouteOnAttribute`)
- [ ] Gestion des erreurs (relations `failure`, file d'attente dédiée, réessai/backoff,
      notification d'échec définitif) configurée sur chaque flux
- [ ] Journalisation (`LogAttribute`) aux points clés de chaque flux
- [ ] Export des flux NiFi (templates / `flow.json.gz`) versionné dans le dépôt Git

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
- [ ] Calcul NDVI intégré au pipeline automatisé (pas seulement interactif GEE)
- [ ] Calcul du NDWI (indice d'eau)
- [ ] Validation des géométries reçues (rejet/correction des géométries invalides)
- [ ] Déduplication (clés naturelles : identifiant OSM, couple date/zone pour les images
      satellites)
- [ ] Gestion des valeurs manquantes (règles définies par type de donnée : interpolation,
      exclusion, marquage explicite)
- [ ] Conversion CRS harmonisée : EPSG:4326 (échange) + EPSG:326xx UTM (calculs métriques
      locaux), via GDAL/PROJ
- [ ] Génération de couches thématiques (végétation, eau, zones urbaines) par seuillage des
      indices calculés
- [ ] Jointures spatiales OSM × NDVI pour statistiques zonales (moyenne NDVI par polygone)

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
- [ ] Schéma `raw` créé (données brutes horodatées)
- [ ] Schéma `processed` créé (NDVI, couches thématiques)
- [ ] Schéma `metadata` créé (documentation des jeux de données)
- [ ] Schéma `users` créé (gestion des accès)
- [ ] Table de métadonnées centralisée (source, licence, date de collecte, CRS, résolution,
      lien vers le fichier/objet raster)
- [ ] Nomenclature normalisée des jeux de données (`source_type_zone_date`)
- [ ] Index GiST sur les colonnes géométriques
- [ ] Mécanisme de versionnement (identifiant logique + numéro de version + date de
      génération), sans écrasement des données précédentes
- [ ] Rôles PostgreSQL créés et appliqués (lecture seule / écriture restreinte NiFi /
      administrateur — moindre privilège)
- [ ] Stratégie de sauvegarde (`pg_dump`/`pg_basebackup` planifiés, volume Docker dédié,
      rotation)
- [ ] Contraintes d'intégrité (clés primaires, `ST_IsValid` pour la validité géométrique)
- [ ] Partitionnement des tables volumineuses par zone/période (si nécessaire à ce stade)

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
- [ ] Endpoint : liste des jeux de données disponibles + métadonnées
- [ ] Endpoint : requêtage spatial (filtrage par zone, date, type d'indice)
- [ ] Endpoint : téléchargement (GeoTIFF, GeoJSON, Shapefile, Parquet)
- [ ] Authentification API (clé API ou JWT), distinguant rôles lecture seule / admin
- [ ] Documentation OpenAPI/Swagger générée et accessible
- [ ] Application web — carte interactive (Leaflet ou OpenLayers) affichant les couches
      NDVI/thématiques
- [ ] Application web — tableau de bord de statistiques synthétiques
- [ ] Intégration QGIS — connexion directe à PostGIS testée
- [ ] Intégration QGIS — projet QGIS préconfiguré versionné dans le dépôt
      (`documentation/` ou `qgis_projects/`)
- [ ] Module de reporting (génération de rapport PDF/HTML périodique)

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
- [ ] Test de bout en bout par source (GEE, OSM, ORS, web scraping) : collecte → insertion
      en base
- [ ] Validation visuelle du NDVI sur QGIS (comparaison avec l'image RGB, cohérence avec
      l'ODD 15)
- [ ] Test de déploiement complet sur une machine tierce (`docker compose up` en une seule
      commande, sans configuration manuelle additionnelle)
- [ ] Tests non fonctionnels : performance (temps de réponse API), fiabilité (simulation
      d'échec réseau), disponibilité (redémarrage automatique des conteneurs)
- [ ] Revue de sécurité (secrets non exposés dans le code/l'historique Git, HTTPS en
      production, rôles appliquant le moindre privilège)
- [ ] Vérification une par une des critères de validation du cahier des charges
      (voir [TECHNICAL.md §18](TECHNICAL.md#18-critères-de-validation-et-dacceptation))

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
- [ ] Finalisation de TECHNICAL.md, ROADMAP.md, PLAN.md (état final du projet)
- [ ] Préparation du jeu de données de démonstration (zone pilote entièrement traitée, NDVI
      + couches thématiques)
- [ ] Préparation de la présentation de soutenance
- [ ] Relecture croisée (encadrant académique / pairs)
- [ ] Répétition chronométrée de la soutenance, y compris démo en local (sans dépendre du
      réseau le jour J si possible)

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
