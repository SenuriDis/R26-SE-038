FROM node:22-slim AS node-runtime
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM docker:cli AS docker-cli

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /app/node_modules /app/node_modules
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/reports

EXPOSE 8004

CMD ["node", "server.js"]
