#!/usr/bin/env python3
"""Forge 错误码一致性校验（契约见 docs/ERROR-CODE-CONVENTION.md §一致性校验）。

校验三处集合必须一致：
  1. backend/src/forge/api/errors.py 的 ErrorCode 注册表（含兜底 SERVER_ERROR 类）
  2. portal-web/i18n/locales/*.json 的 errors 段
  3. admin/src/locales/langs/{zh-cn,en-us}.ts 的 errors 段

用法：python scripts/check-error-codes.py
CI/pre-commit 集成：退出码非 0 即失败。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CLIENT_EXTRA = {"NETWORK_ERROR", "UNKNOWN_ERROR"}


def backend_codes() -> set[str]:
    src = (REPO / "backend/src/forge/api/errors.py").read_text(encoding="utf-8")
    enum_block = re.search(r"class ErrorCode\(StrEnum\):(.*?)(?=\nclass )", src, re.S)
    if not enum_block:
        raise SystemExit("FATAL: cannot locate ErrorCode enum in backend errors.py")
    return {m.group(1) for m in re.finditer(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=", enum_block.group(1), re.M)}


def portal_json_codes() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for f in ["zh", "en", "ar", "de", "fr"]:
        data = json.loads((REPO / f"portal-web/i18n/locales/{f}.json").read_text(encoding="utf-8"))
        out[f] = set((data.get("errors") or {}).keys())
    return out


def admin_ts_codes() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for f in ["zh-cn", "en-us"]:
        text = (REPO / f"admin/src/locales/langs/{f}.ts").read_text(encoding="utf-8")
        m = re.search(r"errors:\s*\{(.*?)\n\s{2}\}", text, re.S)
        if not m:
            raise SystemExit(f"FATAL: cannot locate errors section in admin langs {f}.ts")
        keys = {k for k in re.findall(r"^\s{4}([A-Z][A-Z0-9_]*):", m.group(1), re.M)}
        out[f] = keys
    return out


def main() -> int:
    backend = backend_codes()
    portal = portal_json_codes()
    admin = admin_ts_codes()

    # 后端注册码必须与语言包 errors 段完全一致（语言包额外允许客户端兜底码）
    problems: list[str] = []
    expected = backend | CLIENT_EXTRA

    for lang, keys in portal.items():
        if keys != expected:
            missing = sorted(expected - keys)
            extra = sorted(keys - expected)
            if missing:
                problems.append(f"portal {lang}.json 缺少: {missing}")
            if extra:
                problems.append(f"portal {lang}.json 多余: {extra}")

    for lang, keys in admin.items():
        if keys != expected:
            missing = sorted(expected - keys)
            extra = sorted(keys - expected)
            if missing:
                problems.append(f"admin {lang}.ts 缺少: {missing}")
            if extra:
                problems.append(f"admin {lang}.ts 多余: {extra}")

    print(f"backend codes ({len(backend)}): {sorted(backend)}")
    print(f"expected language keys ({len(expected)}): {sorted(expected)}")
    for lang, keys in portal.items():
        print(f"portal {lang}: {len(keys)} keys")
    for lang, keys in admin.items():
        print(f"admin {lang}: {len(keys)} keys")

    if problems:
        print("\nMISMATCH:")
        for p in problems:
            print(" -", p)
        return 1
    print("\nOK: backend / portal-web / admin error codes are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
