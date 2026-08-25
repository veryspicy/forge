# syntax=docker/dockerfile:1

# Stage 1: Build from source
FROM node:20-alpine AS builder

RUN npm install -g pnpm --registry=https://registry.npmmirror.com

WORKDIR /app

# Install deps first (cache layer)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
COPY packages ./packages
RUN --mount=type=cache,target=/root/.local/share/pnpm/store,sharing=locked \
    --mount=type=cache,target=/root/.npm,sharing=locked \
    pnpm install --frozen-lockfile

# Copy source and build
COPY . .
RUN pnpm build

# Stage 2: Serve with nginx
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/entrypoint.sh /usr/local/bin/admin-entrypoint.sh

RUN chmod +x /usr/local/bin/admin-entrypoint.sh

EXPOSE 80

CMD ["/usr/local/bin/admin-entrypoint.sh"]
