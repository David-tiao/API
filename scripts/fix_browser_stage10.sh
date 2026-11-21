#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# 备份原来的 Dockerfile
cp Dockerfile "Dockerfile.backup.$(date +%Y%m%d_%H%M%S)"

# 使用预装浏览器的官方镜像
cat > Dockerfile <<'DOCKER'
FROM node:22-bookworm-slim AS ast-deps

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY --from=ast-deps /usr/local/bin/node /usr/local/bin/node
COPY --from=ast-deps /app/node_modules /app/node_modules

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY api_extractor ./api_extractor
COPY tools ./tools
COPY README.md ./

RUN mkdir -p /out /cfg

ENTRYPOINT ["python", "-m", "api_extractor.cli"]
DOCKER

echo "Building API Extractor..."
docker build -t api-extractor:0.1.0 .

echo "Testing CLI..."
docker run --rm --pull=never \
  api-extractor:0.1.0 --help

echo "Build finished."
