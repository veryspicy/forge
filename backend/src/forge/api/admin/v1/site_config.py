"""站点配置 API - 品牌、主题、导航等全量配置的读写。"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()

# 配置存储路径（与 uploads/diy 同级，本地文件存储）
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "uploads" / "site-config"
_CONFIG_FILE = _CONFIG_DIR / "site_config.json"

# 默认配置（与前端 DEFAULT_SITE_CONFIG 对齐）
DEFAULT_CONFIG: Dict[str, Any] = {
    "brand": {"name": "Forge", "tagline": "", "logo": {"type": "text", "data": ""}},
    "theme": {
        "primaryColor": "#18a058", "primaryLight": "#36ad6a", "primaryDark": "#0c7a43",
        "secondaryColor": "#f0a020", "accentColor": "#2080f0",
        "fontHeading": "Inter", "fontBody": "Inter",
    },
    "nav": [
        {"label": "首页", "url": "/"},
        {"label": "商品", "url": "/products"},
        {"label": "我的宠物", "url": "/pets"},
        {"label": "订单", "url": "/orders"},
        {"label": "AI客服", "url": "/chat"},
    ],
    "categories": [
        {"slug": "cat-food", "nameKey": "footer.petFood", "icon": "mdi:food"},
        {"slug": "toys", "nameKey": "footer.toys", "icon": "mdi:teddy-bear"},
        {"slug": "health-wellness", "nameKey": "footer.healthWellness", "icon": "mdi:heart-pulse"},
    ],
    "footer": {"copyright": "© 2026 Forge. 版权所有。", "newsletter": True},
    "seo": {"homeTitle": "Forge - 专业宠物用品商店", "metaDescription": "", "metaKeywords": ""},
    "i18n": {"defaultLocale": "en", "locales": ["en"]},
    "featureFlags": {"liveChat": True, "reviews": True, "wishlist": False},
    "currencies": ["USD"],
}


class SiteConfigPayload(BaseModel):
    config: Dict[str, Any]


def _load_from_file() -> Dict[str, Any]:
    """从 JSON 文件读取配置，不存在则返回默认值。"""
    if not _CONFIG_FILE.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 合并默认值（确保新增字段有默认）
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        _deep_merge(merged, data)
        return merged
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(DEFAULT_CONFIG))


def _save_to_file(config: Dict[str, Any]) -> None:
    """保存配置到 JSON 文件。"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(base: dict, override: dict) -> None:
    """深度合并：override 覆盖 base 的同名键，dict 类型递归合并。"""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


@router.get("/config")
async def get_site_config():
    """获取站点全量配置。"""
    config = _load_from_file()
    return {"data": config}


@router.put("/config")
async def save_site_config(payload: SiteConfigPayload):
    """保存站点全量配置（覆盖写入）。"""
    config = _load_from_file()
    _deep_merge(config, payload.config)
    _save_to_file(config)
    return {"data": config}
