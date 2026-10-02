FROM node:24-trixie-slim AS dependencies

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 build-essential libsqlite3-dev

USER node
WORKDIR /app
ENV NODE_ENV=production

COPY --chown=node:node .yarn/releases ./.yarn/releases
COPY --chown=node:node .yarnrc.yml backstage.json ./
COPY --chown=node:node yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz

RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn workspaces focus --all --production

COPY --chown=node:node examples ./examples
COPY --chown=node:node packages/backend/dist/bundle.tar.gz app-config.yaml app-config.production.yaml ./
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz

FROM node:24-trixie-slim

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-0

USER node
WORKDIR /app
ENV NODE_ENV=production

COPY --from=dependencies --chown=node:node /app ./

EXPOSE 7007
CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
