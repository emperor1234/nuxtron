# Nuxtron frontend — Next.js 16 (webpack build). No standalone output is
# configured (next.config.ts has no `output: 'standalone'`), so the runner
# stage ships the full node_modules tree, matching what `next start` expects.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# Full lifecycle scripts run here (not --ignore-scripts): sharp and other
# native deps need their postinstall step to build a working binary, or
# next/image's optimizer silently degrades in production.
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Build-time env: only values that affect what gets baked into the client
# bundle (NEXT_PUBLIC_*) need to be present here. Everything else is
# supplied at runtime by Coolify — see .env.production.example.
ARG NEXT_PUBLIC_DEFAULT_TENANT_ID
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_CLARITY_PROJECT_ID
ARG NEXT_PUBLIC_STRICT_NO_MOCK
ENV NEXT_PUBLIC_DEFAULT_TENANT_ID=$NEXT_PUBLIC_DEFAULT_TENANT_ID \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_CLARITY_PROJECT_ID=$NEXT_PUBLIC_CLARITY_PROJECT_ID \
    NEXT_PUBLIC_STRICT_NO_MOCK=$NEXT_PUBLIC_STRICT_NO_MOCK \
    NODE_ENV=production
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
RUN addgroup -S app && adduser -S -G app app && chown -R app:app /app
USER app
EXPOSE 4173
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${PORT:-4173}/api/health" || exit 1
# PORT is honored if Coolify injects one; otherwise falls back to 4173 to
# match the port this image EXPOSEs and what Coolify's proxy should target.
CMD ["sh", "-c", "node_modules/.bin/next start -p ${PORT:-4173}"]
