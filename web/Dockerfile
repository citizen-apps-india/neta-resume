# syntax=docker/dockerfile:1

###############################################################################
# Builder: install deps and produce the Next.js standalone build
###############################################################################
FROM node:22-slim AS builder

WORKDIR /app

# Server-side base URL for the FastAPI read layer, baked at build time and
# also available at runtime (see runner stage).
ARG NETA_API_BASE=http://localhost:8000
ENV NETA_API_BASE=$NETA_API_BASE

# Install dependencies from the lockfile for reproducible builds.
COPY package.json package-lock.json ./
RUN npm ci

# Build the standalone output (requires output: "standalone" in next.config).
COPY . .
RUN npm run build

###############################################################################
# Runner: minimal image serving the standalone server
###############################################################################
FROM node:22-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

ARG NETA_API_BASE=http://localhost:8000
ENV NETA_API_BASE=$NETA_API_BASE

# Standalone bundle (server.js + minimal node_modules) and static assets.
# (No ./public dir in this project; add a COPY for it if one is introduced.)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
