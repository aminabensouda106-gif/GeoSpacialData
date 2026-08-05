# Cahier des charges — GeoSpacialData

**Projet personnel — 1ère année Cycle Ingénieur, EMSI**

> Version simplifiée, écrite avec des mots simples. Le document original et plus détaillé
> (`CAHIER~2.docx`) reste dans ce dossier comme archive, mais c'est **ce fichier-ci** qui
> sert de référence pour la suite du projet, avec [TECHNICAL.md](TECHNICAL.md),
> [ROADMAP.md](ROADMAP.md) et [PLAN.md](PLAN.md).

**Dernière mise à jour :** 2026-08-05

---

## 1. C'est quoi ce projet ?

Je veux construire un petit système qui va chercher tout seul des données géographiques
(images satellite, cartes, routes...) sur internet, qui les range proprement dans une base
de données, et qui me permet ensuite de les regarder et de les utiliser facilement.

Le but final : pouvoir suivre des choses comme la végétation ou la pluie au Maroc, à partir
de données gratuites, sans devoir tout télécharger et trier à la main à chaque fois.

## 2. Le problème que je veux résoudre

Aujourd'hui, si je veux étudier la végétation ou la pluie sur une zone du Maroc, je dois :

- Aller chercher les images satellite à la main sur Google Earth Engine.
- Aller chercher les données de carte (routes, bâtiments...) sur OpenStreetMap.
- Calculer des indices (comme le NDVI) à la main, à chaque fois.
- Tout refaire depuis le début si je change de zone ou de date.

C'est long, pas organisé, et pas réutilisable. L'idée du projet, c'est d'automatiser tout
ça : un pipeline qui va chercher les données, les nettoie, les calcule, et les range dans
une base, sans que j'aie besoin de tout refaire manuellement à chaque fois.

## 3. Mes objectifs

- Récupérer automatiquement des données depuis plusieurs sources : Google Earth Engine
  (images satellite), OpenStreetMap (cartes), OpenRouteService (routes/trajets), et du web
  scraping pour des données qui n'ont pas d'API.
- Automatiser cette collecte avec **Apache NiFi**, pour ne pas avoir à lancer des scripts à
  la main à chaque fois.
- Stocker toutes ces données dans une seule base de données géographique
  (**PostgreSQL + PostGIS**), bien organisée.
- Calculer automatiquement des indices utiles, comme le **NDVI** (indice de végétation), à
  partir des images satellite.
- Faire tourner tout ça avec **Docker / Docker Compose**, pour que le projet se lance
  facilement, d'un seul coup, sur n'importe quel ordinateur.
- Utiliser le **cloud** (Google Earth Engine) pour les gros calculs et le stockage des
  images, pour ne pas avoir besoin d'un ordinateur super puissant chez moi.

## 4. Ce qui est dans le projet (et ce qui n'y est pas)

**Ce que je fais :**
- Collecte automatique de données (GEE, OSM, ORS, web scraping).
- Nettoyage et transformation de ces données (formats différents → format commun).
- Calcul du NDVI (et éventuellement d'autres indices simples comme le NDWI).
- Stockage organisé dans PostgreSQL/PostGIS.
- Tout ça conteneurisé avec Docker, pour un déploiement simple.
- Une ou deux zones d'étude pilotes (Maroc, éventuellement Sahara occidental), pas le monde
  entier.

**Ce que je ne fais pas (pas dans ce projet, pour rester réaliste) :**
- Pas d'intelligence artificielle / machine learning avancé.
- Pas de gros système type Big Data (Spark, Hadoop...) — pas besoin pour ce volume de
  données.
- Pas d'application mobile.
- Pas de couverture mondiale en temps réel — je reste sur une/des zones pilotes.
- Pas d'API web publique complète ni d'interface graphique pour l'instant — je consulte les
  données directement dans la base ou via des scripts simples. Ça pourra être ajouté plus
  tard si j'ai le temps (voir §13).

## 5. Les données que je vais utiliser

| Source | Ce que ça me donne | Comment je la récupère |
|---|---|---|
| **Google Earth Engine (GEE)** | Images satellite (Sentinel-2), pour calculer le NDVI | Script Python (API GEE), calcul fait côté cloud Google |
| **OpenStreetMap (OSM) / Overpass Turbo** | Cartes : routes, bâtiments, occupation du sol | Requêtes envoyées à l'Overpass API |
| **OpenRouteService (ORS)** | Trajets, distances, zones accessibles | Appels à l'API ORS |
| **Web Scraping** | Données qui n'ont pas d'API (ex : météo locale) | Petits scripts Python qui lisent des pages web |

Zone d'étude : le Maroc (+ Sahara occidental si besoin), avec une sous-zone plus petite
utilisée pour les tests automatiques (pour que les calculs restent rapides).

## 6. Comment ça va marcher (le pipeline)

```
Sources (GEE, OSM, ORS, Web Scraping)
      │
      ▼
Apache NiFi  →  va chercher les données automatiquement, selon un planning
      │
      ▼
Traitement  →  nettoyage, calcul du NDVI, mise au bon format
      │
      ▼
PostgreSQL + PostGIS  →  stockage organisé (données brutes / données traitées)
      │
      ▼
Moi  →  je consulte les données (requêtes SQL, ou petit script/notebook)
```

- **Apache NiFi** joue le rôle de "chef d'orchestre" : il va chercher les données à
  intervalles réguliers (par exemple une fois par jour ou par semaine) et les fait avancer
  dans le pipeline, sans que j'aie besoin d'intervenir.
- Les **calculs lourds** (traitement des images satellite) se font directement dans le
  cloud de Google Earth Engine, pas sur mon ordinateur. Ça évite d'avoir besoin d'une
  machine très puissante.
- Une fois les données prêtes, elles sont rangées dans **PostgreSQL/PostGIS**, avec une
  séparation simple : les données brutes d'un côté, les données déjà traitées (NDVI...) de
  l'autre.

## 7. Les outils que je vais utiliser (et pourquoi)

| Outil | À quoi il sert | Pourquoi je le choisis |
|---|---|---|
| **Google Earth Engine** | Récupérer et traiter les images satellite | Gratuit pour un usage académique, calcul fait dans le cloud |
| **Apache NiFi** | Automatiser la collecte des données | Interface visuelle simple pour créer des flux, pas besoin de tout coder à la main |
| **PostgreSQL + PostGIS** | Stocker les données géographiques | Base de données gratuite, faite pour les données spatiales |
| **Docker / Docker Compose** | Faire tourner tous les services ensemble | Un seul `docker compose up` et tout démarre, sur n'importe quel ordinateur |
| **Cloud (Google)** | Stockage et calcul des images satellite | Évite d'avoir besoin d'un PC puissant, tout est fait à distance |

Tous ces outils sont **gratuits** pour un usage étudiant/académique.

## 8. Comment les données sont rangées (base de données)

Dans PostgreSQL/PostGIS, je sépare les données en deux grandes catégories, pour rester
simple :

- **Données brutes** : ce qui vient d'être récupéré, sans modification (image satellite
  brute, données OSM brutes...).
- **Données traitées** : le résultat après calcul (NDVI, cartes simplifiées...).

Chaque donnée est accompagnée d'un minimum d'informations : d'où elle vient, pour quelle
zone, à quelle date. Comme ça, je sais toujours retrouver l'origine d'une donnée.

## 9. Comment je vais tester que ça marche

- Vérifier que chaque source (GEE, OSM, ORS, scraping) arrive bien à récupérer des données
  automatiquement, sans erreur.
- Vérifier que le NDVI calculé est correct, en le comparant visuellement à l'image satellite
  (zones vertes = NDVI élevé).
- Vérifier que les données sont bien rangées dans PostgreSQL/PostGIS (pas de doublons, pas
  de données corrompues).
- Vérifier que tout le projet démarre bien avec une seule commande Docker, même sur un autre
  ordinateur.

Le détail des tests, étape par étape, est dans [PLAN.md](PLAN.md).

## 10. Ce que je vais rendre à la fin

- Le code du projet (scripts NiFi/Python, configuration Docker), sur Git.
- Les fichiers Docker Compose pour lancer tout le projet facilement.
- Cette documentation (cahier des charges, doc technique, plan).
- Un exemple de résultat concret : une zone du Maroc entièrement traitée, avec son NDVI
  calculé et stocké en base.

## 11. Mon planning (simple)

Le planning détaillé, phase par phase, avec les cases à cocher, est dans
[PLAN.md](PLAN.md) et [ROADMAP.md](ROADMAP.md). En résumé :

1. Vérifier que j'ai tout ce qu'il faut pour commencer (comptes, outils installés).
2. Mettre en place l'environnement (Docker, NiFi, PostgreSQL/PostGIS).
3. Automatiser la collecte des données (un flux NiFi par source).
4. Traiter les données (nettoyage, calcul du NDVI).
5. Bien organiser tout ça dans la base de données.
6. Tester que tout fonctionne de bout en bout.
7. Rédiger le rapport final.

## 12. Les difficultés possibles

| Problème possible | Ce que je ferai si ça arrive |
|---|---|
| Google Earth Engine indisponible ou quota dépassé | Réessayer plus tard, ou télécharger les images directement depuis un autre site (Copernicus) |
| Overpass API ou ORS instable | Réessayer automatiquement, garder en cache ce qui a déjà été récupéré |
| Trop de données pour ma machine | Travailler sur une zone d'étude plus petite (zone pilote) |
| Un site à scraper change ou bloque | Adapter le script, ou choisir une source plus stable |
| Manque de temps | Prioriser : d'abord GEE + NDVI (le cœur du projet), le reste ensuite si le temps le permet |

## 13. Ce que je pourrais ajouter plus tard (pas obligatoire)

Si j'ai le temps en plus du cœur du projet :
- Une petite API pour consulter les données plus facilement depuis l'extérieur.
- Une interface QGIS ou une carte web simple pour visualiser les résultats.
- D'autres indices que le NDVI (comme le NDWI pour l'eau).

Ces points ne sont **pas obligatoires** pour que le projet soit considéré comme réussi —
ce sont des bonus si j'avance plus vite que prévu.
