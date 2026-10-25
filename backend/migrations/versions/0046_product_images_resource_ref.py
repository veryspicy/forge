"""product images converge to resource_id reference

Revision ID: 0046_product_images_resource_ref
Revises: 0045_app_settings
Create Date: 2026-10-25

- 商品表 products.images 收敛为纯引用：元素仅保留 {resource_id, sort, is_main, alt, alt_translations}
- 历史图片（含纯外链 url / MinIO key）补登 resource 表并建立引用关系
- 同步 resource_ref（ref_type='product'）引用追踪，商品图编辑入口已移入资源管理页

设计原则：resource 表为全站素材真相源，url/object_key 由资源表 join 解析，商品表不再冗余快照。
"""

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0046_product_images_resource_ref"
down_revision: str | Sequence[str] | None = "0045_app_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _converge_entry(img: dict[str, Any]) -> dict[str, Any]:
    """收敛单个图片元素为纯引用（resource_id 必须已确定）。"""
    entry = {
        "resource_id": img["resource_id"],
        "sort": int(img.get("sort", 0)),
        "is_main": bool(img.get("is_main", False)),
        "alt": str(img.get("alt", "")),
    }
    alt_translations = img.get("alt_translations")
    if isinstance(alt_translations, dict) and alt_translations:
        entry["alt_translations"] = alt_translations
    return entry


def upgrade() -> None:
    bind = op.get_bind()

    # 1) 默认 site_id：取资源表出现最多的站点；空表时取 active 站点配置
    default_site = bind.execute(
        sa.text(
            "SELECT site_id FROM resource WHERE deleted_at IS NULL "
            "GROUP BY site_id ORDER BY count(*) DESC LIMIT 1"
        )
    ).scalar()
    if default_site is None:
        default_site = bind.execute(
            sa.text(
                "SELECT id FROM site_profiles WHERE is_active = TRUE ORDER BY created_at LIMIT 1"
            )
        ).scalar()
    if default_site is None:
        default_site = bind.execute(
            sa.text("SELECT id FROM site_profiles ORDER BY created_at LIMIT 1")
        ).scalar()
    if default_site is None:
        raise RuntimeError("未找到站点配置，无法为外链资源指定 site_id")

    products = bind.execute(sa.text("SELECT id, name, images FROM products")).fetchall()
    total_refs = 0
    total_created = 0

    for row in products:
        pid = row.id
        pname = str(row.name or "")
        images = row.images if isinstance(row.images, list) else []
        if not images:
            continue

        converged: list[dict[str, Any]] = []
        for img in images:
            if not isinstance(img, dict):
                continue
            resource_id = str(img.get("resource_id") or "").strip()
            url = str(img.get("url") or "").strip()
            key = str(img.get("key") or "").strip()

            if not resource_id and url:
                # 复用同 URL 活跃资源
                rid = bind.execute(
                    sa.text(
                        "SELECT id FROM resource WHERE url = :url AND deleted_at IS NULL "
                        "ORDER BY created_at LIMIT 1"
                    ),
                    {"url": url},
                ).scalar()
                if rid is None and key:
                    # 复用同 object_key 活跃资源（历史 MinIO 上传）
                    rid = bind.execute(
                        sa.text(
                            "SELECT id FROM resource WHERE object_key = :key AND deleted_at IS NULL "
                            "ORDER BY created_at LIMIT 1"
                        ),
                        {"key": key},
                    ).scalar()
                if rid is None:
                    # 登记新资源：有 key 视为 MinIO 对象，无 key 视为外链（object_key 留空）
                    name = (key.rsplit("/", 1)[-1] or url.rsplit("/", 1)[-1] or "image")
                    bind.execute(
                        sa.text(
                            "INSERT INTO resource "
                            "(site_id, bucket, object_key, url, file_type, mime, file_size, name, directory) "
                            "VALUES (:site_id, '', :object_key, :url, 'image', '', 0, :name, :directory)"
                        ),
                        {
                            "site_id": default_site,
                            "object_key": key,
                            "url": url,
                            "name": name[:255],
                            "directory": f"products/{pid}",
                        },
                    )
                    rid = bind.execute(
                        sa.text(
                            "SELECT id FROM resource WHERE url = :url AND deleted_at IS NULL "
                            "ORDER BY created_at LIMIT 1"
                        ),
                        {"url": url},
                    ).scalar()
                    total_created += 1
                resource_id = str(rid)

            if resource_id:
                img["resource_id"] = resource_id
                converged.append(_converge_entry(img))

        if not converged:
            continue

        # 2) 收敛写回商品
        bind.execute(
            sa.text("UPDATE products SET images = CAST(:images AS jsonb) WHERE id = :id"),
            {"images": json.dumps(converged, ensure_ascii=False), "id": pid},
        )

        # 3) 重建商品资源引用（去重后 upsert）
        ref_ids = {e["resource_id"] for e in converged}
        bind.execute(
            sa.text("DELETE FROM resource_ref WHERE ref_type = 'product' AND ref_id = :pid"),
            {"pid": str(pid)},
        )
        for rid in ref_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO resource_ref (resource_id, ref_type, ref_id, ref_label) "
                    "VALUES (:rid, 'product', :pid, :label)"
                ),
                {"rid": rid, "pid": str(pid), "label": pname[:255]},
            )
        total_refs += len(ref_ids)

    # 4) 兜底：清理无引用商品但仍存在的孤儿 product refs（数据一致性）
    op.execute(
        sa.text(
            "DELETE FROM resource_ref WHERE ref_type = 'product' AND ref_id NOT IN "
            "(SELECT id::text FROM products)"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    products = bind.execute(sa.text("SELECT id, images FROM products")).fetchall()
    for row in products:
        images = row.images if isinstance(row.images, list) else []
        if not images:
            continue
        restored: list[dict[str, Any]] = []
        for img in images:
            if not isinstance(img, dict):
                continue
            entry = dict(img)
            rid = str(img.get("resource_id") or "").strip()
            if rid and not str(img.get("url") or "").strip():
                # 从资源表回填快照字段（引用关系保留，不做反向收敛）
                res = bind.execute(
                    sa.text("SELECT url, object_key FROM resource WHERE id = :id AND deleted_at IS NULL"),
                    {"id": rid},
                ).fetchone()
                if res is not None:
                    entry["url"] = res.url or ""
                    entry["key"] = res.object_key or ""
            restored.append(entry)
        if restored:
            bind.execute(
                sa.text("UPDATE products SET images = CAST(:images AS jsonb) WHERE id = :id"),
                {"images": json.dumps(restored, ensure_ascii=False), "id": row.id},
            )
