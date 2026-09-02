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
# Symlink i18n/locales to match Nuxt i18n resolve path (rootDir + restructureDir + langDir)
RUN rm -rf /app/i18n && ln -s /app/app/i18n /app/i18n

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -q -O- http://localhost:3000 || exit 1

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
