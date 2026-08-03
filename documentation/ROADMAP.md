# Roadmap — GeoSpacialData

> Vue d'ensemble des phases du projet, adaptée du planning prévisionnel du
> [cahier des charges](CAHIER~2.docx) (§19, 20 semaines académiques) et mise à jour selon
> l'avancement réel.
>
> - Pour le **détail étape par étape**, les scénarios de test et l'historique des mises à
>   jour de documentation : voir [PLAN.md](PLAN.md) (document vivant, mis à jour en continu).
> - Pour le **contexte technique complet** (architecture, schéma BD, sécurité...) : voir
>   [TECHNICAL.md](TECHNICAL.md).

**Légende de statut :** ⬜ à faire · 🔄 en cours · ✅ terminée

**Dernière mise à jour :** 2026-08-03

---

- [ ] **Phase 0 — Vérification des prérequis** ⬜
  Vérifier que tous les éléments nécessaires (comptes, outils, accès, configuration) sont
  en place avant de lancer le développement.
  → Détail : [PLAN.md — Phase 0](PLAN.md#phase-0--vérification-des-prérequis)

- [ ] **Phase 1 — Cadrage et conception** 🔄
  Analyse des besoins, étude de l'existant, conception de l'architecture, rédaction du
  cahier des charges.
  → Détail : [PLAN.md — Phase 1](PLAN.md#phase-1--cadrage-et-conception)

- [ ] **Phase 2 — Mise en place de l'environnement** 🔄
  Installation et configuration Docker, NiFi, PostgreSQL/PostGIS, QGIS.
  → Détail : [PLAN.md — Phase 2](PLAN.md#phase-2--mise-en-place-de-lenvironnement)

- [ ] **Phase 3 — Développement des flux d'ingestion (NiFi)** 🔄
  Processeurs NiFi pour Google Earth Engine, OpenStreetMap, OpenRouteService et web
  scraping.
  → Détail : [PLAN.md — Phase 3](PLAN.md#phase-3--développement-des-flux-dingestion-nifi)

- [ ] **Phase 4 — Traitement et transformation** ⬜
  Nettoyage, conversion CRS, calcul NDVI/NDWI, couches thématiques.
  → Détail : [PLAN.md — Phase 4](PLAN.md#phase-4--traitement-et-transformation)

- [ ] **Phase 5 — Centralisation et modélisation des données (PostGIS)** ⬜
  Schéma PostGIS, indexation, versionnement, métadonnées. *(en parallèle possible de la
  Phase 4)*
  → Détail : [PLAN.md — Phase 5](PLAN.md#phase-5--centralisation-et-modélisation-des-données-postgis)

- [ ] **Phase 6 — Développement de l'exposition des données** ⬜
  API REST, intégration QGIS, application web de visualisation.
  → Détail : [PLAN.md — Phase 6](PLAN.md#phase-6--exposition-des-données)

- [ ] **Phase 7 — Tests et validation** ⬜
  Tests fonctionnels, tests de bout en bout, validation des indicateurs NDVI.
  → Détail : [PLAN.md — Phase 7](PLAN.md#phase-7--tests-et-validation)

- [ ] **Phase 8 — Rédaction et soutenance** ⬜
  Finalisation du rapport, préparation de la présentation, soutenance.
  → Détail : [PLAN.md — Phase 8](PLAN.md#phase-8--rédaction-et-soutenance)

---

## Où en est le projet aujourd'hui ?

- ✅ Cahier des charges rédigé, README initial, structure de dépôt en place.
- ✅ Script GEE de calcul NDVI / taux de couverture végétale (ODD 15) fonctionnel et validé.
- ✅ Export NDVI automatisé (zone pilote) via `gee_export.py`, prêt à être surveillé par NiFi.
- ✅ `docker-compose.yml` de base (services `nifi` + `gee-exporter`).
- ✅ App Streamlit complémentaire (analyse pluviométrie IMERG) fonctionnelle.
- 🔄 Flux NiFi (canvas) pas encore construits dans l'UI ; ingestion OSM/ORS pas commencée.
- ⬜ PostgreSQL/PostGIS, API REST, application web cible, intégration QGIS, web scraping,
  tests : tout reste à faire.

Voir la table de statut par composant dans [TECHNICAL.md §4.1](TECHNICAL.md#41-statut-dimplémentation-par-composant)
pour le détail complet.

## Convention de travail

À la fin de chaque étape/phase terminée, un point est fait avec des **scénarios de test /
validation manuelle** à exécuter avant de passer à la suite (voir la section correspondante
dans [PLAN.md](PLAN.md)). Rien n'est considéré "acquis" tant que ce contrôle n'a pas été
validé.
