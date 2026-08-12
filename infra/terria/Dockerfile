FROM node:22 AS build
WORKDIR /app

RUN git clone --depth 1 --branch main https://github.com/TerriaJS/TerriaMap.git .

COPY infra/terria/config.json wwwroot/config.json
COPY infra/terria/regionMapping.json wwwroot/data/regionMapping.json
COPY infra/terria/serverconfig.json serverconfig.json

RUN yarn install --network-timeout 1000000 2>&1 | tail -5
RUN yarn gulp release 2>&1 | tail -10

# `gulp release` bundles Cesium's JS but never copies its static Assets
# folder (terrain-height approximation table, IAU2006 XYS data, credit
# images) into wwwroot. That's invisible in 2D Leaflet mode — Leaflet never
# requests them — but 3D Cesium mode fetches approximateTerrainHeights.json
# during camera/globe operations (e.g. "ideal zoom", adding a dataset) and
# a 404 there crashes the whole render loop ("3D map failed to render").
RUN mkdir -p wwwroot/build/TerriaJS/build/Cesium/build/Assets \
    && cp -r node_modules/terriajs-cesium/Source/Assets/. wwwroot/build/TerriaJS/build/Cesium/build/Assets/

FROM node:22-slim
WORKDIR /app
USER node

COPY --from=build --chown=node:node /app/wwwroot ./wwwroot
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/serverconfig.json ./serverconfig.json
COPY --from=build --chown=node:node /app/index.js ./index.js
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/version.js ./version.js

ENV NODE_ENV=production
EXPOSE 3001
CMD ["node", "./node_modules/terriajs-server/lib/app.js", "--config-file", "serverconfig.json"]
