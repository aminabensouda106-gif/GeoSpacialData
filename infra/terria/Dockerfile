FROM node:22 AS build
WORKDIR /app

RUN git clone --depth 1 --branch main https://github.com/TerriaJS/TerriaMap.git .

COPY infra/terria/config.json wwwroot/config.json
COPY infra/terria/regionMapping.json wwwroot/data/regionMapping.json
COPY infra/terria/serverconfig.json serverconfig.json

RUN yarn install --network-timeout 1000000 2>&1 | tail -5
RUN yarn gulp release 2>&1 | tail -10

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
