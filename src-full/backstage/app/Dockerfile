FROM node:24-trixie-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 build-essential libsqlite3-dev && apt-get clean
WORKDIR /app
RUN chown node:node /app
USER node
COPY --chown=node:node . .
RUN --mount=type=secret,id=build-ca,mode=0444 \
    if [ -f /run/secrets/build-ca ]; then \
      export NODE_EXTRA_CA_CERTS=/run/secrets/build-ca; \
    fi; \
    yarn install --immutable && yarn tsc && yarn build:backend && \
    yarn workspaces focus --all --production
RUN tar xzf packages/backend/dist/bundle.tar.gz

FROM node:24-trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 && apt-get clean
WORKDIR /app
USER node
ENV NODE_ENV=production
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/packages/backend ./packages/backend
COPY --from=build --chown=node:node /app/packages/app ./packages/app
COPY --from=build --chown=node:node /app/app-config.yaml ./app-config.yaml
EXPOSE 7007
CMD ["node", "packages/backend", "--config", "/app/platform/app-config.yaml"]
