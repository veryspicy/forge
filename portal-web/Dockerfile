FROM docker.io/library/node:22-alpine

WORKDIR /app

# .npmrc already has registry=https://registry.npmmirror.com, apply early so npm and pnpm both use it
COPY .npmrc ./

# Install pnpm globally
RUN npm install -g pnpm@11.21.0

# Install dependencies (ignore scripts first to avoid ERR_PNPM_IGNORED_BUILDS)
# pnpm-workspace.yaml carries overrides/allowBuilds needed by frozen install validation
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts

# Copy source (bind mount overlay for hot-reload)
COPY . .
# i18n 单一来源：portal-web/i18n/locales
# Nuxt i18n 默认 restructureDir='i18n' + langDir='locales'，解析 rootDir/i18n/locales 即命中，无需软链

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -q -O- http://localhost:3000 || exit 1

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
