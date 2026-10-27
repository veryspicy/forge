"""Backfill pHash fingerprint for existing image resources.

用法（容器内执行，遵循 DEV-RULES §14.1）：
    podman exec forge-backend python -m scripts.backfill_resource_phash

逻辑：遍历 resource 表中 image 类型、phash IS NULL、未软删、有 object_key 的记录，
从 MinIO（本地降级）读取对象内容计算感知哈希并回填。SVG 与读取失败跳过。
"""

from __future__ import annotations

import asyncio
import logging
from typing import cast

from sqlalchemy import select

from forge.infrastructure.persistence.models import ORMResource
from forge.infrastructure.services.minio_service import MinioService
from forge.infrastructure.services.phash_service import compute_phash
from forge.main.dependencies import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("backfill_resource_phash")


async def main() -> None:
    minio = MinioService.get()
    async with async_session_factory() as db:
        rows = (
            (
                await db.execute(
                    select(ORMResource).where(
                        ORMResource.file_type == "image",
                        ORMResource.phash.is_(None),
                        ORMResource.deleted_at.is_(None),
                        ORMResource.object_key != "",
                    )
                )
            )
            .scalars()
            .all()
        )
        updated = skipped = 0
        for res in rows:
            object_key = cast(str, res.object_key)
            if object_key.lower().endswith(".svg"):
                skipped += 1
                continue
            data = minio.get_object(object_key)
            if data is None:
                logger.warning("skip %s: object not readable (%s)", res.id, object_key)
                skipped += 1
                continue
            phash = compute_phash(data)
            if phash is None:
                logger.warning("skip %s: not an image (%s)", res.id, object_key)
                skipped += 1
                continue
            res.phash = phash  # type: ignore[assignment]  # ORM Column 旧式声明，mypy 推断为 Column[str]
            updated += 1
        await db.commit()
        total = len(rows)
        logger.info("done: total=%d updated=%d skipped=%d", total, updated, skipped)


if __name__ == "__main__":
    asyncio.run(main())
