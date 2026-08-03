# GeoSpacialData — Indicateurs géospatiaux (ODD) via Google Earth Engine

Projet exploitant des données satellite (Sentinel-2, GPM IMERG) pour calculer des
indicateurs liés aux Objectifs de Développement Durable (ODD) sur le Maroc et le
Sahara occidental.

## Structure du projet

```
GeoSpacialData/
├── README.md
├── requirements.txt
├── app.py                                              # App Streamlit — analyse pluviométrique (IMERG)
├── 02_Atelier_GEE_Analyseur_Pluviometrique_IMERG30min.ipynb  # Notebook exploratoire (prototype de l'app)
└── gee_scripts/
    └── vegetation_cover_ndvi.js                        # Script GEE — couverture végétale (ODD 15)
```

## Plan d'exécution — Taux de couverture végétale (ODD 15)

| # | Étape | Statut |
|---|---|---|
| 1 | Définir la zone d'étude (limites administratives) | ✅ Fait — Maroc + Sahara occidental (`FAO/GAUL/2015/level0`) |
| 2 | Acquérir l'image satellite (Sentinel-2 Level-2A, faible couverture nuageuse) | ✅ Fait — via Google Earth Engine, filtre nuages < 20 % |
| 3 | Prétraitement (découpage sur la zone, masquage des nuages, sélection des bandes RED/NIR) | ✅ Fait — `clip`, masque `QA60`, bandes B4/B8 |
| 4 | Calcul du NDVI = (NIR − RED) / (NIR + RED) | ✅ Fait |
| 5 | Application du seuil (NDVI > 0.3) → masque binaire végétation | ✅ Fait — seuil = 0.3 (test d'autres seuils comme 0.2/0.4 : pas encore fait) |
| 6 | Calcul du taux de couverture végétale (%) | ✅ Fait — résultats obtenus : nombre d'images, surface totale, surface végétalisée, taux (%) |
| 7 | Visualisation (carte du masque, histogramme NDVI, tableau récapitulatif) | ✅ Fait pour la carte et l'histogramme |
| 8 | Validation / interprétation (comparaison visuelle avec l'image RGB, lecture au regard de l'ODD 15) | ⏳ À faire |
| 9 | *(Optionnel)* Analyse temporelle multi-dates (évolution saisonnière) | ⏳ Pas encore fait |

## Indicateurs

### 1. Taux de couverture végétale (ODD 15 — Vie terrestre)

**Fichier :** [`gee_scripts/vegetation_cover_ndvi.js`](gee_scripts/vegetation_cover_ndvi.js)
**Où l'exécuter :** [Google Earth Engine Code Editor](https://code.earthengine.google.com) (JavaScript)

**Méthode :**
1. Zone d'étude = Maroc + Sahara occidental (limites `FAO/GAUL/2015/level0`, contour simplifié pour rester calculable en interactif)
2. Composite **moyen** Sentinel-2 Level-2A (`COPERNICUS/S2_SR_HARMONIZED`), filtré sur la couverture nuageuse (< 20 %) et masqué via la bande `QA60`
3. Calcul du NDVI : `(B8 − B4) / (B8 + B4)`
4. Seuillage : pixel considéré "végétation" si `NDVI > 0.3`
5. Calcul de la surface végétalisée, de la surface totale et du taux de couverture (%)
6. Histogramme de distribution des valeurs NDVI
7. Export optionnel du masque en pleine résolution (10 m) vers Google Drive

**Utilisation :**
- Ouvrir [code.earthengine.google.com](https://code.earthengine.google.com)
- Coller le contenu du script dans l'éditeur
- Cliquer sur **Run**
- Résultats : cartes (RGB, NDVI, masque végétation) dans l'onglet **Map**, statistiques dans l'onglet **Console**
- Paramètres ajustables en tête de script : `startDate` / `endDate` (période), `threshold` (seuil NDVI)

**Statut :** script fonctionnel et validé — exécution réussie sur Maroc + Sahara occidental (nombre d'images, surfaces, taux de couverture et histogramme NDVI obtenus).
**Prochaines étapes envisagées :** validation visuelle (étape 8), analyse temporelle multi-dates (étape 9), test de seuils alternatifs (0.2 / 0.4).

### 2. Analyse pluviométrique (GPM IMERG, résolution 30 min)

**Fichier :** [`app.py`](app.py)
**Où l'exécuter :** localement, via Streamlit

**Méthode :**
1. L'utilisateur dessine un polygone sur une carte interactive (Folium)
2. Récupération de la série temporelle de précipitations (`NASA/GPM_L3/IMERG_V07`) sur la zone et la période choisies
3. Calcul du cumul de pluie (mm) et de l'intensité maximale (mm/h)
4. Visualisation : histogramme par pas de 30 min + courbe de cumul
5. Export des données en CSV

**Utilisation :**
```bash
pip install -r requirements.txt
streamlit run app.py
```
⚠️ Avant le premier lancement, remplacer `EE_PROJECT_ID` dans [`app.py`](app.py) par l'ID de votre projet Google Cloud associé à Earth Engine.

**Limite :** période d'analyse plafonnée à 60 jours (`MAX_RANGE_DAYS`) pour éviter un calcul trop long côté Earth Engine.

## Ingestion automatisée (Apache NiFi) — Phase 3

**Fichiers :** [`docker-compose.yml`](docker-compose.yml), [`nifi/scripts/`](nifi/scripts/)

Orchestration des flux de collecte pour les 3 premières sources (GEE, OSM, ORS) selon
le cahier des charges §9.2. Le web scraping sera ajouté dans un second temps.

- **Google Earth Engine** : NiFi n'a pas de connecteur natif GEE → un service séparé
  (`gee-exporter`, basé sur [`nifi/scripts/gee_export.py`](nifi/scripts/gee_export.py))
  exécute périodiquement l'export NDVI (même logique que `vegetation_cover_ndvi.js`,
  restreinte à une zone pilote) et dépose le GeoTIFF dans `nifi/data/gee/`. NiFi surveille
  ensuite ce dossier (`ListFile`/`FetchFile`).
- **OpenStreetMap** et **OpenRouteService** : configurés directement dans NiFi via des
  processeurs `InvokeHTTP` (pas de script nécessaire), qui écrivent leurs résultats dans
  `nifi/data/osm/` et `nifi/data/ors/`.

**Démarrage :**
```bash
cp .env.example .env   # puis renseigner EE_PROJECT_ID, EE_CONFIG_DIR, ORS_API_KEY
docker compose up -d --build
```
Interface NiFi : http://localhost:8080/nifi

## Prérequis

- Compte [Google Earth Engine](https://earthengine.google.com/) activé
- Pour la partie Python : `pip install -r requirements.txt`
  - `earthengine-api`, `streamlit`, `streamlit-folium`, `folium`, `pandas`, `plotly`
- Authentification Earth Engine (première utilisation) :
  ```bash
  earthengine authenticate
  ```

## Sources de données

| Donnée | Source | Résolution |
|---|---|---|
| Imagerie optique | Sentinel-2 Level-2A (Copernicus) | 10 m |
| Précipitations | GPM IMERG V07 (NASA) | ~11 km, pas de 30 min |
| Limites administratives | FAO GAUL 2015 | — |

## Explication du script ligne par ligne — `vegetation_cover_ndvi.js`

### Bloc 1 — Zone d'étude (lignes 10-21)

```javascript
var countries = ee.FeatureCollection("FAO/GAUL/2015/level0");
var morocco = countries.filter(ee.Filter.eq('ADM0_NAME', 'Morocco'));
var westernSahara = countries.filter(ee.Filter.eq('ADM0_NAME', 'Western Sahara'));
var roi = morocco.merge(westernSahara).geometry().simplify({maxError: 1000});
Map.centerObject(roi, 5);
Map.addLayer(roi, {}, 'ROI', false);
```
- `ee.FeatureCollection(...)` charge la couche vectorielle des frontières mondiales des pays (une collection de polygones, un par pays)
- `.filter(ee.Filter.eq('ADM0_NAME', 'Morocco'))` garde uniquement l'entité dont l'attribut `ADM0_NAME` vaut `"Morocco"` — même chose pour le Sahara occidental
- `.merge(...)` fusionne les deux collections filtrées en une seule (Maroc + Sahara occidental)
- `.geometry()` extrait la géométrie (le ou les polygones) de la collection fusionnée
- `.simplify({maxError: 1000})` réduit le nombre de sommets du contour avec une tolérance de 1000 m — nécessaire car le contour original est trop détaillé pour être découpé (`clip`) en interactif sans dépasser la mémoire
- `Map.centerObject(roi, 5)` centre la carte sur la zone d'étude, niveau de zoom 5
- `Map.addLayer(roi, {}, 'ROI', false)` ajoute la géométrie comme couche sur la carte (nommée "ROI"), `false` = cachée par défaut

### Bloc 2 — Image Sentinel-2 (lignes 26-57)

```javascript
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterDate(startDate, endDate)
  .filterBounds(roi)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(maskS2clouds);
var image = s2.mean();
var clipped = image.clip(roi);
```
- `ee.ImageCollection(...)` charge la collection d'images satellite Sentinel-2 Level-2A (des centaines d'images dans le monde, à toutes les dates)
- `.filterDate(startDate, endDate)` garde seulement les images prises dans l'intervalle de dates choisi
- `.filterBounds(roi)` garde seulement les images qui recouvrent (au moins en partie) la zone d'étude
- `.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))` garde seulement les images dont l'attribut "pourcentage de nuages" est inférieur à 20 %
- `.map(maskS2clouds)` applique la fonction `maskS2clouds` à **chaque image** de la collection (équivalent d'une boucle, mais exécutée côté serveur GEE) — à l'intérieur : `.select('QA60')` extrait la bande qualité, `.bitwiseAnd()` / `.eq()` / `.and()` décodent bit par bit les indicateurs nuage/cirrus de cette bande, `.updateMask()` rend transparents (NoData) les pixels nuageux, `.divide(10000)` convertit les valeurs brutes en réflectance (0 à 1)
- `.mean()` est un **réducteur temporel** : combine toutes les images restantes de la collection en une seule image composite, pixel par pixel, en prenant la moyenne des valeurs valides à chaque endroit
- `.clip(roi)` découpe l'image composite pour ne garder que les pixels à l'intérieur du contour Maroc + Sahara occidental (élimine la mer et les pays voisins)

### Bloc 3 — Calcul du NDVI (ligne 62)

```javascript
var ndvi = clipped.normalizedDifference(['B8', 'B4']).rename('NDVI');
```
- `.normalizedDifference(['B8', 'B4'])` calcule automatiquement `(B8 − B4) / (B8 + B4)` pixel par pixel sur toute l'image — B8 = proche infrarouge (NIR), B4 = rouge (RED). C'est la formule du NDVI
- `.rename('NDVI')` donne un nom explicite à la bande résultante

### Bloc 4 — Seuillage (lignes 69-70)

```javascript
var vegMask = ndvi.gt(threshold).selfMask();
```
- `.gt(threshold)` compare chaque pixel à la valeur du seuil (0.3) : renvoie 1 si NDVI > 0.3, sinon 0 — crée une image binaire
- `.selfMask()` transforme les pixels à 0 en pixels transparents/NoData, ne gardant visibles/comptables que les pixels "végétation"

### Bloc 5 — Surfaces et taux de couverture (lignes 80-99)

```javascript
var pixelArea = ee.Image.pixelArea();
var vegArea = pixelArea.updateMask(vegMask).reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: roi,
  scale: 500,
  maxPixels: 1e13,
  bestEffort: true,
  tileScale: 8
}).get('area');
var totalArea = roi.area({maxError: 1000});
```
- `ee.Image.pixelArea()` génère une image où la valeur de chaque pixel est sa propre surface réelle en m² (varie légèrement selon la latitude)
- `.updateMask(vegMask)` ne garde la surface que des pixels "végétation" (les autres deviennent NoData)
- `.reduceRegion({...})` agrège (ici : additionne) les valeurs de tous les pixels sur la géométrie donnée — c'est la fonction centrale pour transformer une image raster en un chiffre unique
  - `reducer: ee.Reducer.sum()` : type d'agrégation = somme
  - `geometry: roi` : région sur laquelle agréger
  - `scale: 500` : résolution (en m) à laquelle le calcul est fait
  - `maxPixels`, `bestEffort`, `tileScale` : paramètres pour rester dans les limites de calcul interactif de GEE sur une zone aussi grande
- `.get('area')` récupère la valeur numérique du résultat (un dictionnaire est renvoyé par `reduceRegion`, on en extrait la clé `'area'`)
- `roi.area({maxError: 1000})` calcule directement la surface totale de la géométrie (pas besoin de raster ici, calcul géométrique direct)

### Bloc 6 — Histogramme (lignes 104-109)

```javascript
ui.Chart.image.histogram({image: ndvi, region: roi, scale: 500, maxPixels: 1e9})
```
- `ui.Chart.image.histogram({...})` génère un histogramme de la distribution des valeurs de pixels d'une image sur une région donnée — utile pour voir la répartition des valeurs NDVI (combien de pixels sont proches de 0, proches de 1, etc.)

### Bloc 7 — Export (lignes 114-120)

```javascript
Export.image.toDrive({image: vegMask.toByte(), description: '...', region: roi, scale: 10, maxPixels: 1e13});
```
- `.toByte()` convertit l'image en un type de donnée plus léger (entier 8-bit) avant export
- `Export.image.toDrive({...})` crée une **tâche asynchrone** (visible dans l'onglet Tasks) qui exporte l'image raster complète vers Google Drive, à la résolution native (10 m) — contrairement au reste du script, cet export tourne sur l'infrastructure batch de GEE et tolère des calculs plus lourds que l'interactif

## Tableau récapitulatif — fonctions et syntaxes géospatiales

| Fonction / syntaxe | Catégorie | Rôle géospatial |
|---|---|---|
| `ee.FeatureCollection(id)` | Vecteur | Charge une collection de géométries (points/lignes/polygones) depuis le catalogue GEE |
| `ee.Filter.eq(prop, val)` / `ee.Filter.lt(prop, val)` | Filtre | Filtre des éléments (images ou entités vectorielles) selon un attribut |
| `.filter(filtre)` | Vecteur / Image | Applique un filtre à une collection |
| `.merge(collection)` | Vecteur | Fusionne deux `FeatureCollection` en une seule |
| `.geometry()` | Vecteur | Extrait la géométrie pure (polygones) d'une `FeatureCollection` |
| `.simplify({maxError})` | Vecteur | Simplifie un contour (réduit le nombre de sommets) avec une tolérance donnée |
| `.area({maxError})` | Vecteur | Calcule la surface d'une géométrie |
| `Map.centerObject(obj, zoom)` | Affichage | Centre la carte interactive sur un objet géographique |
| `Map.addLayer(obj, visParams, nom, visible)` | Affichage | Ajoute une couche (raster ou vecteur) à la carte |
| `ee.ImageCollection(id)` | Raster | Charge une collection d'images satellite (série temporelle) |
| `.filterDate(début, fin)` | Raster | Filtre une collection d'images par intervalle de dates |
| `.filterBounds(geometry)` | Raster | Filtre une collection aux images qui intersectent une zone géographique |
| `.select(bande)` | Raster | Sélectionne une ou plusieurs bandes spectrales d'une image |
| `.bitwiseAnd()` / `.eq()` / `.and()` | Raster | Opérations bit à bit / logiques, utilisées ici pour décoder un masque qualité (QA) |
| `.updateMask(mask)` | Raster | Masque une image (pixels invalides → transparents/NoData) |
| `.divide(n)` | Raster | Opération arithmétique appliquée pixel par pixel |
| `.map(fonction)` | Raster | Applique une fonction à chaque image d'une collection (boucle côté serveur) |
| `.mean()` / `.median()` | Raster | Réducteur temporel : fusionne une collection d'images en une seule image composite |
| `.clip(geometry)` | Raster | Découpe une image selon les limites d'une géométrie |
| `.normalizedDifference([b1, b2])` | Raster | Calcule un indice de différence normalisée, ex. NDVI = (b1−b2)/(b1+b2) |
| `.rename(nom)` | Raster | Renomme une bande d'image |
| `.gt(valeur)` | Raster | Comparaison pixel par pixel (>), produit une image booléenne |
| `.selfMask()` | Raster | Masque une image sur ses propres pixels à zéro/faux |
| `ee.Image.pixelArea()` | Raster | Image où chaque pixel contient sa propre surface réelle en m² |
| `.reduceRegion({...})` | Raster → Nombre | Agrège les pixels d'une image sur une région (somme, moyenne, etc.) — convertit un raster en statistique |
| `ee.Reducer.sum()` | Réducteur | Type d'agrégation utilisé par `reduceRegion` |
| `ee.Number(x)` | Utilitaire | Enveloppe une valeur serveur GEE en objet numérique manipulable (`.divide()`, `.multiply()`, ...) |
| `ui.Chart.image.histogram({...})` | Visualisation | Histogramme de distribution des valeurs de pixels sur une région |
| `Export.image.toDrive({...})` | Export | Crée une tâche batch qui exporte une image raster vers Google Drive |

## Contexte

Projet réalisé dans le cadre d'un travail encadré, visant à construire progressivement
un ensemble d'indicateurs géospatiaux liés aux ODD (actuellement : ODD 15 — couverture
végétale ; ODD 13 / gestion des risques — pluviométrie).
