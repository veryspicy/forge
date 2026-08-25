#!/bin/sh
# Admin 启动入口：
# 1. 将当前构建的 assets 归档到持久化卷（与最新归档内容一致则跳过，避免重启膨胀）
# 2. 仅保留最近 MAX_VERSIONS 个历史版本
# 3. 将历史 chunk 合并回 html/assets（Vite content-hash 命名，新旧文件可共存），
#    使仍持有旧 index.html 的浏览器能加载到旧 chunk，从根源消除 ChunkLoadError 白屏/卡死
set -e

HISTORY_DIR=/var/lib/admin-assets-history
ASSETS_DIR=/usr/share/nginx/html/assets
MAX_VERSIONS=5

mkdir -p "$HISTORY_DIR"

# 最新归档目录
LATEST=$(ls -1d "$HISTORY_DIR"/*/ 2>/dev/null | sort -r | head -n1)

NEED_ARCHIVE=1
if [ -n "$LATEST" ] && [ -d "$LATEST" ]; then
  if diff -rq "$ASSETS_DIR" "$LATEST" >/dev/null 2>&1; then
    NEED_ARCHIVE=0
  fi
fi

if [ "$NEED_ARCHIVE" -eq 1 ]; then
  TS=$(date +%Y%m%d%H%M%S)
  while [ -d "$HISTORY_DIR/$TS" ]; do
    TS="${TS}x"
  done
  cp -r "$ASSETS_DIR" "$HISTORY_DIR/$TS"
fi

# 保留最近 MAX_VERSIONS 版
COUNT=0
for d in $(ls -1d "$HISTORY_DIR"/*/ 2>/dev/null | sort -r); do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -gt "$MAX_VERSIONS" ]; then
    rm -rf "$d"
  fi
done

# 合并历史 assets 回 html（cp -rn：不覆盖同名文件）
for d in $(ls -1d "$HISTORY_DIR"/*/ 2>/dev/null); do
  cp -rn "$d"* "$ASSETS_DIR/" 2>/dev/null || true
done

exec nginx -g 'daemon off;'
