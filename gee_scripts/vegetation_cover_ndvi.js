// ============================================================
// Taux de couverture végétale — ODD 15 (Vie terrestre)
// Méthode : seuillage NDVI sur composite Sentinel-2 Level-2A
// Zone d'étude : Maroc + Sahara occidental (FAO GAUL 2015 level0)
// ============================================================

// ------------------------------------------------------------
// 1. ZONE D'ÉTUDE
// ------------------------------------------------------------
var countries = ee.FeatureCollection("FAO/GAUL/2015/level0");

var morocco = countries.filter(ee.Filter.eq('ADM0_NAME', 'Morocco'));
var westernSahara = countries.filter(ee.Filter.eq('ADM0_NAME', 'Western Sahara'));

// simplify() : réduit le nombre de points du contour (tolérance 1 km,
// invisible à l'échelle du pays) — indispensable pour que le clip reste
// calculable en interactif, sinon "Tile error: memory capacity exceeded"
var roi = morocco.merge(westernSahara).geometry().simplify({maxError: 1000});

Map.centerObject(roi, 5);
Map.addLayer(roi, {}, 'ROI', false);

// ------------------------------------------------------------
// 2. IMAGE SENTINEL-2 (Level-2A, corrigée atmosphériquement)
// ------------------------------------------------------------
var startDate = '2026-04-01';
var endDate   = '2026-04-30'; // 1 mois : moins d'images à traiter = moins de mémoire

function maskS2clouds(img) {
  var qa = img.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    .and(qa.bitwiseAnd(cirrusBitMask).eq(0));
  return img.updateMask(mask).divide(10000);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterDate(startDate, endDate)
  .filterBounds(roi)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .map(maskS2clouds);

print('Nombre d\'images disponibles :', s2.size());

// mean() plutôt que median() : la médiane doit garder toutes les valeurs
// de chaque pixel en mémoire pour les trier, ce qui dépasse la limite
// mémoire à l'échelle nationale. La moyenne se calcule au fil de l'eau
// (somme/compte), beaucoup plus légère, et donne un résultat très proche
// pour un indicateur agrégé comme le taux de couverture.
var image = s2.mean();

// Découpage précis sur le contour terrestre (Maroc + Sahara occidental,
// sans la mer) — grâce au simplify() ci-dessus, ce clip reste calculable
// en interactif.
var clipped = image.clip(roi);
Map.addLayer(clipped, {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3}, 'RGB (clipped)');

// ------------------------------------------------------------
// 3. CALCUL DU NDVI
// ------------------------------------------------------------
var ndvi = clipped.normalizedDifference(['B8', 'B4']).rename('NDVI');

Map.addLayer(ndvi, {min: -1, max: 1, palette: ['blue', 'white', 'green']}, 'NDVI');

// ------------------------------------------------------------
// 4. SEUILLAGE
// ------------------------------------------------------------
var threshold = 0.3;
var vegMask = ndvi.gt(threshold).selfMask();
Map.addLayer(vegMask, {palette: ['darkgreen']}, 'Masque végétation (NDVI > 0.3)');

// ------------------------------------------------------------
// 5. CALCUL DES SURFACES ET DU TAUX DE COUVERTURE
//    (scale=500m : à l'échelle nationale, 100m fait dépasser le temps/
//    mémoire de calcul interactif car il faut évaluer le composite
//    médian Sentinel-2 sur des centaines d'images pour tout le pays.
//    500m reste largement suffisant pour un pourcentage national.)
// ------------------------------------------------------------
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

var vegAreaKm2 = ee.Number(vegArea).divide(1e6);
var totalAreaKm2 = ee.Number(totalArea).divide(1e6);
var coveragePct = ee.Number(vegArea).divide(totalArea).multiply(100);

print('Surface totale (km²) :', totalAreaKm2);
print('Surface végétalisée (km²) :', vegAreaKm2);
print('Taux de couverture végétale (%) :', coveragePct);

// ------------------------------------------------------------
// 6. HISTOGRAMME DE DISTRIBUTION NDVI
// ------------------------------------------------------------
print(ui.Chart.image.histogram({
  image: ndvi,
  region: roi,
  scale: 500,
  maxPixels: 1e9
}).setOptions({title: 'Distribution des valeurs NDVI (Maroc + Sahara occidental)'}));

// ------------------------------------------------------------
// 7. (Optionnel) Export du masque en pleine résolution 10m vers Drive
// ------------------------------------------------------------
Export.image.toDrive({
  image: vegMask.toByte(),
  description: 'vegetation_mask_MA_EH_10m',
  region: roi,
  scale: 10,
  maxPixels: 1e13
});
